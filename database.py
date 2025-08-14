
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    incidents = db.relationship('Incident', backref='user', lazy=True)

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def summary(self):
        return (f"Ref: {self.reference}\n"
                f"Category: {self.category}\n"
                f"Location: {self.location}\n"
                f"Severity: {self.severity}\n"
                f"Date: {self.created_at.strftime('%Y-%m-%d %H:%M')}")

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()