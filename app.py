from flask import Flask, request, jsonify
from ussd_flow import handle_ussd
from database import init_db
from config import Config
import threading

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
init_db(app)

# Session storage (in-memory for simplicity — use Redis in production)
session_store = {}
session_lock = threading.Lock()


def _get_param_from_payload(payload, *names):
    """Helper: try several possible key names, case-insensitive."""
    if not payload:
        return None
    # Normalize keys to lower-case for lookup
    lower_map = {k.lower(): v for k, v in payload.items()}
    for n in names:
        if n is None:
            continue
        val = lower_map.get(n.lower())
        if val is not None:
            return val
    return None

@app.route('/ussd', methods=['POST'])
def ussd_handler():
    # Try JSON first, then form, then values
    json_data = request.get_json(silent=True)
    form_data = request.form.to_dict() if request.form else {}
    # merge: prefer JSON values over form values
    merged = {}
    if form_data:
        merged.update(form_data)
    if json_data and isinstance(json_data, dict):
        merged.update(json_data)

    # Accept a wide variety of parameter names (sessionId, session_id, sessionid, etc.)
    session_id = _get_param_from_payload(merged, 'sessionId', 'session_id', 'sessionid', 'SessionId')
    service_code = _get_param_from_payload(merged, 'serviceCode', 'service_code', 'servicecode')
    phone_number = _get_param_from_payload(merged, 'phoneNumber', 'phone_number', 'msisdn', 'phone')
    text = _get_param_from_payload(merged, 'text', 'message', 'ussd_string') or ''

    # Debug logs (keep these while testing with the simulator)
    print("Incoming USSD request headers:", dict(request.headers))
    print("Merged payload:", merged)

    # Validate required parameters
    if not session_id or not service_code or not phone_number:
        print("Missing parameters:", {
            "sessionId": session_id,
            "serviceCode": service_code,
            "phoneNumber": phone_number
        })
        # Return a helpful message for debugging; Arkesel expects 200 OK with JSON body
        return jsonify({"error": "Missing required parameters", "received": merged}), 200

    # Handle USSD session (your existing handler)
    try:
        with session_lock:
            response_text = handle_ussd(
                session_store=session_store,
                session_id=session_id,
                phone_number=phone_number,
                user_input=text
            )
    except Exception as e:
        print("Error in handle_ussd:", str(e))
        return jsonify({"response": "END Internal server error. Please try again later."}), 200

    # Determine continueSession/message from a CON / END prefix if present
    # Keep backward compatibility: if caller expects the raw response string, include it too.
    continue_session = False
    message = response_text

    # If your handle_ussd returns "CON " or "END " prefixed strings (common)
    if isinstance(response_text, str):
        if response_text.startswith('CON '):
            continue_session = True
            message = response_text[4:]
        elif response_text.startswith('END '):
            continue_session = False
            message = response_text[4:]
        else:
            # no explicit prefix: treat as END (session terminated) by default
            continue_session = False
            message = response_text

    # Return Arkesel-friendly JSON plus a 'response' fallback
    return jsonify({
        "message": message,
    }), 200

def cleanup_sessions():
    """Periodically clean up expired sessions"""
    with session_lock:
        expired_keys = [k for k, s in session_store.items() if s.is_expired()]
        for key in expired_keys:
            del session_store[key]

if __name__ == '__main__':
    # Start session cleanup thread
    from threading import Timer
    def schedule_cleanup():
        cleanup_sessions()
        Timer(60, schedule_cleanup).start()  # Run every minute

    Timer(60, schedule_cleanup).start()

    app.run(host='0.0.0.0', port=8000, debug=True)
