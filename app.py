# app.py (top section) - paste/replace up to before session_store definition
from flask import Flask, request, jsonify
from flask_restful import Api
from ussd.ussd_handler import ussd_bp,start_cleanup
from models.database import init_db  # init_db will call db.init_app and optionally create_all/migrations
from config import Config
import threading, time

# auth / jwt imports
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    get_jwt, get_jwt_identity, jwt_required
)

app = Flask(__name__)
app.config.from_object(Config)

# Ensure Config has JWT_SECRET_KEY set
# Initialize DB BEFORE registering resources that may query DB
init_db(app)          # <-- make sure this runs (or db.init_app + migrate.init_app elsewhere)

# JWT setup
jwt = JWTManager()
jwt.init_app(app)

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload.get("jti")
    if not jti:
        return True
    # TokenBlocklist imported inside database.py; safe to query inside request context
    from models.database import TokenBlocklist
    return TokenBlocklist.query.filter_by(jti=jti).first() is not None

@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return jsonify({"msg": "Token has been revoked"}), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"msg": "Token expired"}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error_string):
    return jsonify({"msg": "Invalid token", "error": error_string}), 422

@jwt.unauthorized_loader
def missing_token_callback(error_string):
    return jsonify({"msg": "Missing Authorization Header", "error": error_string}), 401
# --- end JWT setup ---


# register url routes 
from routes import register_routes
register_routes(app)


# register ussd route
app.register_blueprint(ussd_bp)

# start the ussd cleanup loop (runs in background)
start_cleanup()


# from flask_migrate import Migrate
# from database import db

# migrate = Migrate(app, db)
