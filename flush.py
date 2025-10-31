# flush.py
from app import app  # import the Flask app instance
from models.database import db

with app.app_context():
    db.drop_all()
    print("Dropped all tables")
    db.create_all()
    print("Created tables from models")
