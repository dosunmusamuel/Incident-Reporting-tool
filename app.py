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

@app.route('/ussd', methods=['POST'])
def ussd_handler():
    # Extract parameters from form data
    session_id = request.form.get('sessionId')
    service_code = request.form.get('serviceCode')
    phone_number = request.form.get('phoneNumber')
    text = request.form.get('text', '')

    # Log incoming request for debugging(tobismaa)
    print("Incoming USSD request:")
    print("Headers:", request.headers)
    print("Form Data:", request.form)

    # Validate required parameters(tobismaa)
    if not session_id or not service_code or not phone_number:
        print("Missing parameters:", {
            "sessionId": session_id,
            "serviceCode": service_code,
            "phoneNumber": phone_number
        })
        return jsonify({"response": "END Missing required parameters."}), 200

    # Handle USSD session(updated_tobismaa)
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

    # Return response in JSON format as expected by Arkesel(tobismaa)
    return jsonify({"response": response_text}), 200

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
