# app.py
from flask import Flask, request, jsonify
from ussd_flow import handle_ussd
from database import init_db
from config import Config
import threading
import time

app = Flask(__name__)
app.config.from_object(Config)

# Initialize DB
init_db(app)

# In-memory stores (process-level)
session_store = {}     # session_id -> USSDSession (from ussd_flow)
replay_cache = {}      # session_id -> (response_payload_dict, timestamp)
session_lock = threading.Lock()

# Tunable TTLs
SESSION_TTL_MINUTES = 5         # session expiry window
REPLAY_CACHE_TTL_SECONDS = 60   # how long to keep last response for replay

def _extract_and_normalize(req):
    """
    Parse incoming request (JSON or form) and return canonical dict:
      { merged, session_id, service_code, phone_number, text, new_session }
    """
    json_data = req.get_json(silent=True)
    form_data = req.form.to_dict() if req.form else {}
    merged = {}
    if form_data:
        merged.update(form_data)
    if json_data and isinstance(json_data, dict):
        merged.update(json_data)

    # case-insensitive lookup helper
    lower_map = {k.lower(): v for k, v in merged.items()}

    def pick(*names):
        for n in names:
            if n in merged:
                return merged[n]
            v = lower_map.get(n.lower())
            if v is not None:
                return v
        return None

    session_id = pick('sessionId', 'session_id', 'sessionID', 'sessionid', 'session')
    service_code = pick('serviceCode', 'service_code', 'servicecode', 'service', 'ussd', 'userData', 'user_data', 'userdata')
    phone_number = pick('phoneNumber', 'phone_number', 'msisdn', 'msisdnNumber', 'phone')
    # gateways sometimes use 'text', 'message', 'userData', 'input', 'userInput' etc.
    text = pick('text', 'message', 'input', 'ussd_string', 'userData', 'userdata', 'userInput') or ''
    new_session_raw = pick('newSession', 'new_session', 'newsession', 'isNew')

    # convert new_session to bool defensively
    new_session = False
    if isinstance(new_session_raw, bool):
        new_session = new_session_raw
    elif new_session_raw is not None:
        try:
            s = str(new_session_raw).strip().lower()
            new_session = s in ('true', '1', 'yes')
        except Exception:
            new_session = False

    # normalize fullwidth USSD characters and whitespace
    def normalize_ussd(s):
        if s is None:
            return ''
        s = str(s)
        s = s.replace('\uFF03', '#').replace('\uFF0A', '*').replace('＃', '#').replace('＊', '*')
        return s.strip()

    service_code = normalize_ussd(service_code) if service_code else None
    text = normalize_ussd(text)

    # If service_code missing but text looks like initial dial e.g. "*123#", use it.
    if not service_code and text and text.startswith('*') and '#' in text:
        service_code = text
        if new_session:
            text = ''

    return {
        'merged': merged,
        'session_id': session_id,
        'service_code': service_code,
        'phone_number': phone_number,
        'text': text,
        'new_session': new_session
    }

def _is_initial_dial(text, service_code):
    """True if text is an initial dial (empty or equals service_code or contains * or #)."""
    if not text:
        return True
    if not service_code:
        # If service_code unknown, consider dial if it contains '*' or '#'
        return ('*' in text) or ('#' in text)
    t = text.strip()
    sc = service_code.strip()
    if t == sc:
        return True
    if sc.endswith('#') and t == sc.rstrip('#'):
        return True
    if ('*' in t) or ('#' in t):
        return True
    return False

def _make_response_payload(session_id, merged, response_text):
    """
    Build JSON payload expected by gateway from response_text string (CON/END)
    response_text may be str starting with 'CON ' or 'END ' or raw message.
    """
    # extract userID if present in merged
    try:
        user_id = merged.get('userID') or merged.get('userId') or merged.get('user_id')
    except Exception:
        user_id = None
    if not user_id:
        user_id = session_id

    msisdn = merged.get('msisdn') or merged.get('msisdnNumber') or merged.get('phoneNumber') or merged.get('phone') or merged.get('msisdn') or merged.get('msisdn')

    # determine continueSession and message
    continue_session = False
    message = ""
    raw_response = response_text

    if isinstance(response_text, str):
        if response_text.startswith('CON '):
            continue_session = True
            message = response_text[4:]
        elif response_text.startswith('END '):
            continue_session = False
            message = response_text[4:]
        else:
            # default treat as END
            continue_session = False
            message = response_text
    else:
        message = str(response_text)
        continue_session = False

    payload = {
        "sessionID": session_id,
        "userID": user_id,
        "msisdn": msisdn,
        "message": message,
        "continueSession": continue_session,
        "raw_response": raw_response
    }
    return payload

@app.route('/ussd', methods=['POST'])
def ussd_handler():
    parsed = _extract_and_normalize(request)
    merged = parsed['merged']
    session_id = parsed['session_id']
    service_code = parsed['service_code']
    phone_number = parsed['phone_number']
    text = parsed['text']
    new_session = parsed['new_session']

    # Debug log
    print("Incoming USSD request headers:", dict(request.headers))
    print("Merged payload:", merged)
    print("Parsed:", {"session_id": session_id, "service_code": service_code, "phone_number": phone_number, "text": text, "new_session": new_session})

    # Validate
    if not session_id or not phone_number:
        return jsonify({
            "error": "Missing required parameters",
            "expected": ["sessionId | sessionID | session_id", "phoneNumber | msisdn"],
            "received": merged
        }), 200

    # Fast-path: only replay cached JSON if provider indicates new session AND text looks like initial dial
    with session_lock:
        cache_entry = replay_cache.get(session_id)
        if new_session and cache_entry and _is_initial_dial(text, service_code):
            payload, ts = cache_entry
            if (time.time() - ts) <= REPLAY_CACHE_TTL_SECONDS:
                print(f"[USSD] Replaying cached JSON payload for session {session_id} (initial dial detected)")
                return jsonify(payload), 200
            else:
                del replay_cache[session_id]

    # Call business logic
    try:
        with session_lock:
            response_text = handle_ussd(
                session_store=session_store,
                session_id=session_id,
                phone_number=phone_number,
                user_input=text,
                new_session=new_session,
                replay_cache={k: v[0] for k, v in replay_cache.items()},
                session_ttl_minutes=SESSION_TTL_MINUTES
            )
            # Build JSON payload for gateway
            payload = _make_response_payload(session_id, merged, response_text)
            # Save payload in replay cache with timestamp
            replay_cache[session_id] = (payload, time.time())
    except Exception as e:
        print("Error in handle_ussd:", str(e))
        fallback = {
            "sessionID": session_id,
            "userID": merged.get('userID') or session_id,
            "msisdn": phone_number,
            "message": "Internal server error",
            "continueSession": False,
            "raw_response": "END Internal server error."
        }
        return jsonify(fallback), 200

    # Return the JSON payload the gateway expects
    return jsonify(payload), 200

def cleanup_sessions_and_replay():
    """Periodically remove expired sessions and stale replay entries."""
    try:
        with session_lock:
            now = time.time()
            # remove expired sessions
            expired_keys = [sid for sid, s in session_store.items() if s.is_expired()]
            for sid in expired_keys:
                del session_store[sid]
                if sid in replay_cache:
                    del replay_cache[sid]

            # remove stale replay cache entries older than REPLAY_CACHE_TTL_SECONDS
            stale = [sid for sid, (_, ts) in replay_cache.items() if (now - ts) > REPLAY_CACHE_TTL_SECONDS]
            for sid in stale:
                del replay_cache[sid]
    except Exception as e:
        print("Error during cleanup:", str(e))
    finally:
        threading.Timer(30, cleanup_sessions_and_replay).start()

if __name__ == '__main__':
    threading.Timer(1, cleanup_sessions_and_replay).start()
    app.run(host='0.0.0.0', port=8000, debug=True)
