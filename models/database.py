import uuid
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()

# User model for USSD
class User(db.Model):
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    incidents = db.relationship('Incident', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.phone_number}>"

# Admin model 
class Admin(db.Model):
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = db.Column(db.String(255), default='')
    last_name = db.Column(db.String(255), default='')
    email = db.Column(db.String(255), unique=True, nullable=False)  
    phone_number = db.Column(db.String(20), default='')
    password_hash = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Admin {self.phone_number}>"


# Incident model
class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)
    
    def summary(self):
        return (
            f"Ref: {self.reference}\n"
            f"Category: {self.category}\n"
            f"Location: {self.location}\n"
            f"Severity: {self.severity}\n"
            f"Date: {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        )


# JWT Model
class TokenBlocklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    token_type = db.Column(db.String(10), nullable=False)  # access / refresh
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Database initiator
def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
