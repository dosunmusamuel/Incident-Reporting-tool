# app.py
from flask import Flask, request, jsonify
from flask_restful import Api
from ussd.ussd_handler import ussd_bp, start_cleanup
from models.database import init_db
from config import Config
import threading, time

# JWT imports
import jwt as pyjwt
from jwt import exceptions as pyjwt_exceptions
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    get_jwt, get_jwt_identity, jwt_required,
    JWTExtendedException, NoAuthorizationError, InvalidHeaderError
)

app = Flask(__name__)
app.config.from_object(Config)

# === CONFIG ===
app.config['JWT_ERROR_MESSAGE_KEY'] = 'msg'
app.config['JWT_TOKEN_LOCATION'] = ['headers']

# === INIT DB ===
init_db(app)

# === JWT ===
jwt = JWTManager()
jwt.init_app(app)

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload.get("jti")
    if not jti:
        return True
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

# === ERROR HANDLERS (use @app, not @current_app) ===
@app.errorhandler(pyjwt_exceptions.ExpiredSignatureError)
def handle_pyjwt_expired(err):
    app.logger.debug("PyJWT ExpiredSignatureError: %s", err)
    return jsonify({"msg": "Token expired"}), 401

@app.errorhandler(pyjwt_exceptions.InvalidTokenError)
def handle_pyjwt_invalid(err):
    app.logger.debug("PyJWT InvalidTokenError: %s", err)
    return jsonify({"msg": "Invalid token", "error": str(err)}), 422

@app.errorhandler(JWTExtendedException)
def handle_jwt_extended(err):
    app.logger.debug("JWTExtendedException: %s", err)
    return jsonify({"msg": str(err)}), 401

@app.errorhandler(NoAuthorizationError)
def handle_no_authorization(err):
    app.logger.debug("NoAuthorizationError: %s", err)
    return jsonify({"msg": "Missing Authorization Header"}), 401

@app.errorhandler(InvalidHeaderError)
def handle_invalid_header(err):
    app.logger.debug("InvalidHeaderError: %s", err)
    return jsonify({"msg": "Invalid Authorization Header"}), 401

from werkzeug.exceptions import HTTPException

@app.errorhandler(HTTPException)
def handle_http_exception(e):
    app.logger.debug("HTTPException: %s", e)
    return jsonify({"msg": e.description}), e.code

@app.errorhandler(Exception)
def handle_unexpected_exception(e):
    app.logger.exception("Unhandled exception")
    return jsonify({"msg": "Internal server error"}), 500

# === ROUTES ===
from routes import register_routes
register_routes(app)
app.register_blueprint(ussd_bp)

# === BACKGROUND ===
start_cleanup()