from app import app
from models.database import db, User, Incident

with app.app_context():
    # 1️⃣ Create a new user first
    user = User(
        phone_number="07089533287",
    )
    db.session.add(user)
    db.session.commit()  # commit so user gets an ID

    # 2️⃣ Create incidents linked to the new user
    incidents = [
        Incident(reference="INC001", category="Forgery (Digital)", location="Lagos", severity="High", description="Fake documents uploaded", user_id=user.id),
        Incident(reference="INC002", category="Fraud (Digital)", location="Abuja", severity="Medium", description="Unauthorized transaction", user_id=user.id),
        Incident(reference="INC003", category="Phishing", location="Port Harcourt", severity="High", description="Email phishing attempt", user_id=user.id),
        Incident(reference="INC004", category="Malware / Virus", location="Kano", severity="Low", description="Suspicious software detected", user_id=user.id),
    ]

    db.session.add_all(incidents)
    db.session.commit()

    print("✅ User and incidents added successfully!")
