# app/resources/dashboard.py
from flask_restful import Resource,reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import current_app
from models.database import db, Admin, Incident
from datetime import datetime, timedelta
from sqlalchemy import or_
import csv
from io import StringIO
from flask import Response


import uuid


class DashboardResource(Resource):
    @jwt_required()
    def get(self):
        # Identity is stored as {"admin_id": <id>} in the example auth code above
        
        identity = get_jwt_identity()

        # check if identity exists first
        if not identity:
            return {"success": False, "msg": "invalid token identity"}, 401

        # convert to UUID
        try:
            admin_id = uuid.UUID(identity)
        except ValueError:
            return {"success": False, "msg": "invalid token identity"}, 401

        # now query the admin
        admin = Admin.query.get(admin_id)
        if not admin:
            return {"success": False, "msg": "admin not found"}, 404

                
        now = datetime.utcnow()

        # total number of incident reports
        total_reports = db.session.query(Incident).count()
        
        # reports in the last 30 days (count)
        thirty_days_ago = now - timedelta(days=30)
        this_month_count = (
            db.session.query(Incident)
            .filter(Incident.created_at >= thirty_days_ago)
            .count()
        )

        # reports for "today" (UTC): from 00:00:00 UTC to now
        start_of_today = datetime(year=now.year, month=now.month, day=now.day)
        today_count = (
            Incident.query
            .filter(Incident.created_at >= start_of_today)
            .order_by(Incident.created_at.desc())
            .all()
        )

        # last 8 incidents (most recent first)
        last_reports_query = (
            Incident.query
            .order_by(Incident.created_at.desc())
            .limit(8)
            .all()
        )

        report_history = []
        for inc in last_reports_query:
            report_history.append({
                "id": inc.id,
                "category": inc.category,
                "severity": inc.severity,
                "location": inc.location,
                "description": inc.description or ""
            })

        return {
            "success": True,
            "admin": {
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "email": admin.email
            },
            "stats": {
                "total_reports_count": total_reports,
                "this_month_count":this_month_count,
                "today_count":today_count
            },
            "report_history": report_history
        }, 200



class ReportsResource(Resource):
    @jwt_required()
    def get(self):
        # --- Parse query parameters ---
        parser = reqparse.RequestParser()
        parser.add_argument("category", type=str, required=False, help="Filter by category", location="args")
        parser.add_argument("severity", type=str, required=False, help="Filter by severity", location="args")
        args = parser.parse_args()

        category_filter = args.get("category")
        severity_filter = args.get("severity")
        # --- Get admin identity from JWT ---
        
        identity = get_jwt_identity()

        # check if identity exists first
        if not identity:
            return {"success": False, "msg": "invalid token identity"}, 401

        # convert to UUID
        try:
            admin_id = uuid.UUID(identity)
        except ValueError:
            return {"success": False, "msg": "invalid token identity"}, 401

        # now query the admin
        admin = Admin.query.get(admin_id)
        if not admin:
            return {"success": False, "msg": "admin not found"}, 404

        # --- Build the base query ---
        query = Incident.query

        if category_filter:
            query = query.filter(Incident.category == category_filter)
        if severity_filter:
            query = query.filter(Incident.severity == severity_filter)

        # --- Order by most recent ---
        query = query.order_by(Incident.created_at.desc())

        # --- Execute query ---
        reports = query.all()

        # --- Build response ---
        report_history = [
            {
                "id": inc.id,
                "category": inc.category,
                "severity": inc.severity,
                "location": inc.location,
                "description": inc.description or "",
            }
            for inc in reports
        ]

        return {
            "success": True,
            "count": len(report_history),
            "report_history": report_history
        }, 200



# app/resources/search.py
class IncidentSearchResource(Resource):
    @jwt_required()
    def get(self):
        # --- Parse search query ---
        parser = reqparse.RequestParser()
        parser.add_argument("q", type=str, required=True, help="Search query is required", location="args")
        args = parser.parse_args()
        query_term = args.get("q").strip()

        if not query_term:
            return {"success": False, "msg": "Search query cannot be empty"}, 400

        # --- Get admin identity from JWT ---
        identity = get_jwt_identity()

        # check if identity exists first
        if not identity:
            return {"success": False, "msg": "invalid token identity"}, 401

        # convert to UUID
        try:
            admin_id = uuid.UUID(identity)
        except ValueError:
            return {"success": False, "msg": "invalid token identity"}, 401

        # now query the admin
        admin = Admin.query.get(admin_id)
        if not admin:
            return {"success": False, "msg": "admin not found"}, 404

        # --- Build search query ---
        incidents = Incident.query.filter(
            or_(
                Incident.description.ilike(f"%{query_term}%"),
                Incident.category.ilike(f"%{query_term}%"),
                Incident.location.ilike(f"%{query_term}%"),
                Incident.severity.ilike(f"%{query_term}%"),
                Incident.reference.ilike(f"%{query_term}%")
            )
        ).order_by(Incident.created_at.desc()).all()

        # --- Build response ---
        results = [
            {
                "id": inc.id,
                "category": inc.category,
                "severity": inc.severity,
                "location": inc.location,
                "description": inc.description or "",
            }
            for inc in incidents
        ]

        return {
            "success": True,
            "count": len(results),
            "results": results
        }, 200


# app/resources/export.py
class ExportReportsCSVResource(Resource):
    @jwt_required()
    def get(self):
        # --- Authenticate admin ---
        identity = get_jwt_identity()

        # check if identity exists first
        if not identity:
            return {"success": False, "msg": "invalid token identity"}, 401

        # convert to UUID
        try:
            admin_id = uuid.UUID(identity)
        except ValueError:
            return {"success": False, "msg": "invalid token identity"}, 401

        # now query the admin
        admin = Admin.query.get(admin_id)
        if not admin:
            return {"success": False, "msg": "admin not found"}, 404

        # --- Fetch all incidents ---
        incidents = Incident.query.order_by(Incident.created_at.desc()).all()

        # --- Create CSV in memory ---
        output = StringIO()
        writer = csv.writer(output)

        # Write header row
        writer.writerow(["ID", "Reference", "Category", "Severity", "Location", "Description", "Created At", "User ID"])

        # Write incident rows
        for inc in incidents:
            writer.writerow([
                inc.id,
                inc.reference,
                inc.category,
                inc.severity,
                inc.location,
                inc.description or "",
                inc.created_at.isoformat(),
                inc.user_id
            ])

        # Prepare response
        output.seek(0)
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=incident_reports.csv"}
        )
