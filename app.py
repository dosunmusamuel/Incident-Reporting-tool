# app.py
from flask import Flask, jsonify
from flask_restful import Api
from ussd.ussd_handler import ussd_bp, start_cleanup
from models.database import init_db
from config import Config

# JWT
from flask_jwt_extended import JWTManager

app = Flask(__name__)
app.config.from_object(Config)

app.config['JWT_ERROR_MESSAGE_KEY'] = 'msg'
app.config['JWT_TOKEN_LOCATION'] = ['headers']

init_db(app)

# === JWT ===
jwt = JWTManager(app) 


# General HTTP errors
from werkzeug.exceptions import HTTPException
@app.errorhandler(HTTPException)
def handle_http_exception(e):
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