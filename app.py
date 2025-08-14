from flask import Flask, request, Response
from ussd_flow import handle_ussd
from database import init_db
from config import Config
import threading

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
init_db(app)

# Session storage (in-memory for simplicity - use Redis in production)
session_store = {}
session_lock = threading.Lock()

@app.route('/ussd', methods=['POST'])
def ussd_handler():
    # Extract parameters
    session_id = request.form.get('sessionId')
    service_code = request.form.get('serviceCode')
    phone_number = request.form.get('phoneNumber')
    text = request.form.get('text', '')
    
    with session_lock:
        response = handle_ussd(
            session_store=session_store,
            session_id=session_id,
            phone_number=phone_number,
            user_input=text
        )
    
    return Response(response, content_type='text/plain; charset=utf-8')

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
    
    app.run(host='0.0.0.0', port=5000, debug=True)