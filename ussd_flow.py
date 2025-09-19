# ussd_flow.py
from datetime import datetime, timedelta
from database import db, User, Incident
import random
import string

# Incident categories
INCIDENT_CATEGORIES = {
    '1': "Theft/Burglary",
    '2': "Fire Hazard",
    '3': "Accident",
    '4': "Harassment",
    '5': "Infrastructure Damage",
    '6': "Public Health Concern"
}

# Severity levels
SEVERITY_LEVELS = {
    '1': "Low",
    '2': "Medium",
    '3': "High",
    '4': "Emergency"
}

class USSDSession:
    def __init__(self, session_id, phone_number):
        self.session_id = session_id
        self.phone_number = phone_number
        self.state = "INITIAL"
        self.incident_data = {}
        self.created_at = datetime.utcnow()
        self.last_active = datetime.utcnow()
    
    def is_expired(self, ttl_minutes: int = 5):
        return datetime.utcnow() > self.last_active + timedelta(minutes=ttl_minutes)
    
    def update_activity(self):
        self.last_active = datetime.utcnow()
    
    def generate_reference(self):
        """Generate unique reference number"""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"INC-{date_str}-{rand_str}"

# module-level replay cache (in-memory)
session_responses = {}   # key: session_id -> last response string

def _looks_like_initial_dial(text: str):
    """
    Return True if text looks like an initial USSD dial (e.g. '*123#' or empty).
    Otherwise False (likely a user selection like '1', '2', '1234', etc.).
    """
    if not text:
        return True
    t = str(text).strip()
    # if it contains '*' or '#' treat as a dial string
    if '*' in t or '#' in t:
        return True
    return False

def _normalize_input(s):
    if s is None:
        return ''
    s = str(s)
    s = s.replace('\uFF03', '#').replace('\uFF0A', '*').replace('＃', '#').replace('＊', '*')
    return s.strip()

def handle_ussd(session_store, session_id, phone_number, user_input, new_session=False, replay_cache=None, session_ttl_minutes: int = 5):
    """
    session_store: dict-like mapping session_id -> USSDSession
    session_id, phone_number: strings
    user_input: normalized text from provider (may be '' for initial dial)
    new_session: boolean flag from provider payload
    replay_cache: optional dict-like for replay (not strictly required here)
    session_ttl_minutes: expiry
    Returns: response string (starting with 'CON ' or 'END ')
    """
    if replay_cache is None:
        replay_cache = session_responses

    # Normalize input to be safe
    user_input = _normalize_input(user_input)

    # If provider says newSession and we have a cached reply and this is an initial dial, replay handled in app.py fast-path
    # (we keep replay cache write here for completeness)
    # Get existing session
    session = session_store.get(session_id)

    # Create session if missing or expired
    created_new_session = False
    if (not session) or session.is_expired(ttl_minutes=session_ttl_minutes):
        session = USSDSession(session_id, phone_number)
        session_store[session_id] = session
        created_new_session = True

        # IMPORTANT: if the incoming payload includes a real selection (e.g., '1','2', etc.)
        # and it does *not* look like an initial dial (like '*123#'), set the session.state to MAIN_MENU
        # so the incoming selection will be processed rather than being discarded.
        if user_input and (not _looks_like_initial_dial(user_input)):
            session.state = "MAIN_MENU"

    else:
        # if session exists, do nothing special — we will process normally
        pass

    # Update activity timestamp
    session.update_activity()

    # State machine
    response = None

    if session.state == "INITIAL":
        response = ("CON Welcome to Incident Reporting:\n"
                   "1. Report New Incident\n"
                   "2. View Previous Reports\n"
                   "3. Help\n"
                   "0. Exit")
        session.state = "MAIN_MENU"

    elif session.state == "MAIN_MENU":
        if user_input == '1':
            session.state = "CATEGORY_SELECT"
            response = ("CON Select Incident Category:\n" +
                        "\n".join([f"{k}. {v}" for k, v in INCIDENT_CATEGORIES.items()]))
        elif user_input == '2':
            session.state = "VIEW_REPORTS"
            response = get_recent_reports(phone_number)
        elif user_input == '3':
            session.state = "INITIAL"
            response = ("END Contact support:\n"
                        "Email: support@incident.org\n"
                        "Phone: +1234567890")
        elif user_input == '0':
            session.state = "EXIT"
            response = "END Thank you. Stay safe."
        else:
            # If there's no input (user just dialed) show menu. If input is invalid selection, show invalid.
            if not user_input:
                response = ("CON Welcome to Incident Reporting:\n"
                            "1. Report New Incident\n"
                            "2. View Previous Reports\n"
                            "3. Help\n"
                            "0. Exit")
                session.state = "MAIN_MENU"
            else:
                response = "END Invalid option. Please dial again."

    elif session.state == "CATEGORY_SELECT":
        if user_input in INCIDENT_CATEGORIES:
            session.incident_data['category'] = INCIDENT_CATEGORIES[user_input]
            session.state = "LOCATION_INPUT"
            response = "CON Enter location (e.g., Building A, Room 101):"
        else:
            response = "END Invalid category. Please start again."

    elif session.state == "LOCATION_INPUT":
        if user_input:
            session.incident_data['location'] = user_input
            session.state = "SEVERITY_SELECT"
            response = ("CON Select Severity Level:\n" +
                        "\n".join([f"{k}. {v}" for k, v in SEVERITY_LEVELS.items()]))
        else:
            response = "CON Enter location (e.g., Building A, Room 101):"

    elif session.state == "SEVERITY_SELECT":
        if user_input in SEVERITY_LEVELS:
            session.incident_data['severity'] = SEVERITY_LEVELS[user_input]
            session.state = "DESCRIPTION_INPUT"
            response = "CON Briefly describe the incident:"
        else:
            response = "END Invalid severity level. Please start again."

    elif session.state == "DESCRIPTION_INPUT":
        if user_input:
            session.incident_data['description'] = user_input
            session.state = "CONFIRMATION"
            summary = (f"Category: {session.incident_data.get('category','-')}\n"
                       f"Location: {session.incident_data.get('location','-')}\n"
                       f"Severity: {session.incident_data.get('severity','-')}\n"
                       f"Description: {session.incident_data.get('description','-')}")
            response = f"CON Confirm submission:\n{summary}\n1. Submit\n2. Cancel"
        else:
            response = "CON Briefly describe the incident:"

    elif session.state == "CONFIRMATION":
        if user_input == '1':
            ref = save_incident(session)
            session.state = "COMPLETE"
            response = f"END Incident reported successfully!\nReference: {ref}"
        else:
            session.state = "INITIAL"
            response = "END Incident reporting cancelled."

    elif session.state == "VIEW_REPORTS":
        if user_input == '0':
            session.state = "INITIAL"
            response = ("CON Welcome to Incident Reporting:\n"
                        "1. Report New Incident\n"
                        "2. View Previous Reports\n"
                        "3. Help\n0. Exit")
        else:
            response = view_report_details(phone_number, user_input)

    else:
        response = "END Session error. Please dial again."

    # Save last response into replay cache for potential quick replay
    try:
        replay_cache[session_id] = response
    except Exception:
        # ignore if replay_cache is not writable
        pass

    return response


def get_recent_reports(phone_number):
    """Get user's recent incident reports"""
    user = User.query.filter_by(phone_number=phone_number).first()
    if not user:
        return "END No previous reports found."
    
    incidents = Incident.query.filter_by(user_id=user.id).order_by(Incident.created_at.desc()).limit(5).all()
    
    if not incidents:
        return "END No previous reports found."
    
    response_lines = ["CON Recent Reports:"]
    for i, incident in enumerate(incidents, 1):
        response_lines.append(f"{i}. {incident.category} ({incident.created_at.strftime('%d/%m')})")
    
    response_lines.append("")  # blank line
    response_lines.append("Select a report for details")
    response_lines.append("0. Back")
    return "\n".join(response_lines)


def view_report_details(phone_number, selection):
    """Show details of a specific report"""
    try:
        index = int(selection) - 1
        if index < 0:
            return "END Invalid selection."
    except ValueError:
        return "END Invalid input."
    
    user = User.query.filter_by(phone_number=phone_number).first()
    if not user:
        return "END User not found."
    
    incidents = Incident.query.filter_by(user_id=user.id).order_by(Incident.created_at.desc()).limit(5).all()
    
    if 0 <= index < len(incidents):
        detail = incidents[index].summary()
        if len(detail) > 200:
            detail = detail[:197] + "..."
        return f"END {detail}"
    return "END Report not found."


def save_incident(session):
    """Save incident to database"""
    user = User.query.filter_by(phone_number=session.phone_number).first()
    if not user:
        user = User(phone_number=session.phone_number)
        db.session.add(user)
        db.session.commit()
    
    reference = session.generate_reference()
    incident = Incident(
        reference=reference,
        category=session.incident_data.get('category', ''),
        location=session.incident_data.get('location', ''),
        severity=session.incident_data.get('severity', ''),
        description=session.incident_data.get('description', ''),
        user_id=user.id
    )
    
    db.session.add(incident)
    db.session.commit()
    return reference
