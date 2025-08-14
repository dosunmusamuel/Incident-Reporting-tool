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
    
    def is_expired(self):
        return datetime.utcnow() > self.last_active + timedelta(minutes=5)
    
    def update_activity(self):
        self.last_active = datetime.utcnow()
    
    def generate_reference(self):
        """Generate unique reference number"""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"INC-{date_str}-{rand_str}"

def handle_ussd(session_store, session_id, phone_number, user_input):
    # Get or create session
    session = session_store.get(session_id)
    if not session or session.is_expired():
        session = USSDSession(session_id, phone_number)
        session_store[session_id] = session
    
    session.update_activity()
    input_parts = user_input.split('*') if user_input else []
    
    # State machine
    if session.state == "INITIAL":
        response = ("CON Welcome to Incident Reporting:\n"
                   "1. Report New Incident\n"
                   "2. View Previous Reports\n"
                   "3. Help\n"
                   "0. Exit")
        session.state = "MAIN_MENU"
        return response
    
    elif session.state == "MAIN_MENU":
        if user_input == '1':
            session.state = "CATEGORY_SELECT"
            return ("CON Select Incident Category:\n" +
                    "\n".join([f"{k}. {v}" for k, v in INCIDENT_CATEGORIES.items()]))
        
        elif user_input == '2':
            session.state = "VIEW_REPORTS"
            return get_recent_reports(phone_number)
        
        elif user_input == '3':
            session.state = "INITIAL"
            return ("END Contact support:\n"
                    "Email: support@incident.org\n"
                    "Phone: +1234567890")
        
        elif user_input == '0':
            session.state = "EXIT"
            return "END Thank you. Stay safe."
        
        else:
            return "END Invalid option. Please dial again."
    
    elif session.state == "CATEGORY_SELECT":
        if user_input in INCIDENT_CATEGORIES:
            session.incident_data['category'] = INCIDENT_CATEGORIES[user_input]
            session.state = "LOCATION_INPUT"
            return "CON Enter location (e.g., Building A, Room 101):"
        else:
            return "END Invalid category. Please start again."
    
    elif session.state == "LOCATION_INPUT":
        session.incident_data['location'] = user_input
        session.state = "SEVERITY_SELECT"
        return ("CON Select Severity Level:\n" +
                "\n".join([f"{k}. {v}" for k, v in SEVERITY_LEVELS.items()]))
    
    elif session.state == "SEVERITY_SELECT":
        if user_input in SEVERITY_LEVELS:
            session.incident_data['severity'] = SEVERITY_LEVELS[user_input]
            session.state = "DESCRIPTION_INPUT"
            return "CON Briefly describe the incident:"
        else:
            return "END Invalid severity level. Please start again."
    
    elif session.state == "DESCRIPTION_INPUT":
        session.incident_data['description'] = user_input
        session.state = "CONFIRMATION"
        
        summary = (f"Category: {session.incident_data['category']}\n"
                   f"Location: {session.incident_data['location']}\n"
                   f"Severity: {session.incident_data['severity']}\n"
                   f"Description: {session.incident_data['description']}")
        
        return f"CON Confirm submission:\n{summary}\n1. Submit\n2. Cancel"
    
    elif session.state == "CONFIRMATION":
        if user_input == '1':
            # Save to database
            ref = save_incident(session)
            session.state = "COMPLETE"
            return f"END Incident reported successfully!\nReference: {ref}"
        else:
            session.state = "INITIAL"
            return "END Incident reporting cancelled."
    
    elif session.state == "VIEW_REPORTS":
        if user_input == '0':
            session.state = "INITIAL"
            return "CON Welcome to Incident Reporting:\n1. Report New Incident\n2. View Previous Reports\n3. Help\n0. Exit"
        else:
            # Handle report detail view
            return view_report_details(phone_number, user_input)
    
    return "END Session error. Please dial again."

def get_recent_reports(phone_number):
    """Get user's recent incident reports"""
    user = User.query.filter_by(phone_number=phone_number).first()
    if not user:
        return "END No previous reports found."
    
    incidents = Incident.query.filter_by(user_id=user.id).order_by(Incident.created_at.desc()).limit(5).all()
    
    if not incidents:
        return "END No previous reports found."
    
    response = "CON Recent Reports:\n"
    for i, incident in enumerate(incidents, 1):
        response += f"{i}. {incident.category} ({incident.created_at.strftime('%d/%m')})\n"
    
    response += "\nSelect a report for details\n0. Back"
    return response

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
        return f"END {incidents[index].summary()}"
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
        category=session.incident_data['category'],
        location=session.incident_data['location'],
        severity=session.incident_data['severity'],
        description=session.incident_data['description'],
        user_id=user.id
    )
    
    db.session.add(incident)
    db.session.commit()
    return reference