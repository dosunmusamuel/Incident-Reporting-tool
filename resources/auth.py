# resources/auth.py
from flask_restful import Resource
from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt,
    get_jwt_identity
)
from sqlalchemy.exc import IntegrityError
from models.database import db, Admin, TokenBlocklist
from .utils import authenticate_admin

class RegisterResource(Resource):
    def post(self):
        data = request.get_json() or {}
        phone = data.get("phone_number")
        email = data.get("email")
        password = data.get("password")
        first_name = data.get("first_name")
        last_name = data.get("last_name")

        if not password or not email:
            return {"success": False, "msg": "email and password required"}, 400

        # optional: normalize phone format here

        if Admin.query.filter_by(phone_number=phone).first():
            return {"success": False, "msg": "admin already exists"}, 400

        admin = Admin(email=email, phone_number=phone, first_name=first_name, last_name=last_name)
        admin.set_password(password)

        db.session.add(admin)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {"success": False, "msg": "email already registered"}, 400

        return {"success": True, "msg": "admin created"}, 201


class LoginResource(Resource):
    def post(self):
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return {"success": False, "msg": "email and password required"}, 400

        admin = Admin.query.filter_by(email=email).first()
        if not admin or not admin.check_password(password):
            return {"success": False, "msg": "bad credentials"}, 401

        identity = {"admin_id": admin.id, "email": admin.email}
        # auth.py - LoginResource
        access = create_access_token(identity=str(admin.id))
        refresh = create_refresh_token(identity=str(admin.id))

        return {
            "success":True,
            "access_token": access,
            "refresh_token": refresh,
            "msg":"Login Successful"
        },200


class RefreshResource(Resource):
    @jwt_required(refresh=True)
    def post(self):
        identity = get_jwt_identity()
        access = create_access_token(identity=identity)
        return {"access_token": access}, 200


class LogoutAccessResource(Resource):
    @jwt_required()
    def post(self):
        admin, error = authenticate_admin()
        if error:
            return error
        jti = get_jwt()["jti"]
        db.session.add(TokenBlocklist(jti=jti, token_type="access"))
        db.session.commit()
        return {"success":True, "msg": "access token revoked"}, 200


class LogoutRefreshResource(Resource):
    @jwt_required(refresh=True)
    def post(self):
        jti = get_jwt()["jti"]
        db.session.add(TokenBlocklist(jti=jti, token_type="refresh"))
        db.session.commit()
        return {"msg": "refresh token revoked"}, 200
