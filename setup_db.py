from app import app
from models.database import db

with app.app_context():
    db.create_all()

