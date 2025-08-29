from flask import Flask, request, jsonify
from ussd_flow import handle_ussd
from database import init_db
from config import Config
import threading
import time

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
init_db(app)

# Session storage (in-memory for simplicity — use Redis in production)
session_store = {}
session_lock = threading.Lock()


@app.route('/ussd', methods=['POST'])
def ussd_handler():
    session_id = request.form.get('sessionId')
    service_code = request.form.get('serviceCode')
    phone_number = request.form.get('phoneNumber')
    text = request.form.get('text', '')

    print("Incoming USSD request:", request.form)

    # Validate required params
    if not session_id or not service_code or not phone_number:
        return jsonify({
            "sessionId": session_id,
            "userId": "incident-service",
            "msisdn": phone_number,
            "message": "Missing required parameters.",
            "continueSession": False
        }), 200

    try:
        with session_lock:
            response_text = handle_ussd(
                session_store=session_store,
                session_id=session_id,
                phone_number=phone_number,
                user_input=text
            )

        # Decide continueSession based on response prefix
        continue_session = response_text.startswith("CON")
        message = response_text[4:] if response_text.startswith(("CON", "END")) else response_text

        return jsonify({
            "sessionId": session_id,
            "userId": "incident-service",   # identifier for your app
            "msisdn": phone_number,
            "message": message,
            "continueSession": continue_session
        }), 200

    except Exception as e:
        print("Error:", str(e))
        return jsonify({
            "sessionId": session_id,
            "userId": "incident-service",
            "msisdn": phone_number,
            "message": "Internal server error. Please try again later.",
            "continueSession": False
        }), 200


def cleanup_sessions():
    """Periodically clean up expired sessions"""
    with session_lock:
        expired_keys = [k for k, s in session_store.items() if s.is_expired()]
        for key in expired_keys:
            del session_store[key]


def session_cleanup_loop():
    """Background thread that cleans sessions every 60s"""
    while True:
        time.sleep(60)
        cleanup_sessions()


if __name__ == '__main__':
    # Start cleanup in background
    threading.Thread(target=session_cleanup_loop, daemon=True).start()

    app.run(host='0.0.0.0', port=8000, debug=True)
