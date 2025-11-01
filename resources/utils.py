# app/utils/auth.py
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask import current_app
from models.database import Admin
import uuid

def authenticate_admin():
    """
    Returns (admin, error_response) tuple.
    If admin exists → (admin, None)
    If error → (None, (json_response, status_code))
    """
    try:
        verify_jwt_in_request()
        identity = get_jwt_identity()

        if not identity:
            return None, ({"success": False, "msg": "Invalid token identity"}, 401)

        try:
            admin_id = uuid.UUID(identity)
        except ValueError:
            return None, ({"success": False, "msg": "Invalid token identity"}, 401)

        admin = Admin.query.get(admin_id)
        if not admin:
            return None, ({"success": False, "msg": "Admin not found"}, 404)

        return admin, None

    except Exception as e:
        current_app.logger.debug(f"JWT Auth failed: {e}")
        msg = "Unauthorized"
        if "expired" in str(e).lower():
            msg = "Token expired"
        elif "missing" in str(e).lower():
            msg = "Missing Authorization header"
        elif "signature" in str(e).lower():
            msg = "Invalid token signature"
        return None, ({"success": False, "msg": msg}, 401)