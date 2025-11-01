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
from .utils import authenticate_admin
import uuid


class DashboardResource(Resource):
    def get(self):
        admin, error = authenticate_admin()
        if error:
            return error

        now = datetime.utcnow()

        # Total reports
        total_reports = db.session.query(Incident).count()

        # Last 30 days
        thirty_days_ago = now - timedelta(days=30)
        this_month_count = (
            db.session.query(Incident)
            .filter(Incident.created_at >= thirty_days_ago)
            .count()
        )

        # Today (UTC)
        start_of_today = datetime(now.year, now.month, now.day)
        today_incidents = (
            Incident.query
            .filter(Incident.created_at >= start_of_today)
            .order_by(Incident.created_at.desc())
            .all()
        )

        # Last 8 incidents
        last_reports = (
            Incident.query
            .order_by(Incident.created_at.desc())
            .limit(8)
            .all()
        )

        report_history = [
            {
                "id": inc.id,
                "category": inc.category,
                "severity": inc.severity,
                "location": inc.location,
                "description": inc.description or ""
            }
            for inc in last_reports
        ]

        return {
            "success": True,
            "admin": {
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "email": admin.email
            },
            "stats": {
                "total_reports_count": total_reports,
                "this_month_count": this_month_count,
                "today_count": len(today_incidents)
            },
            "report_history": report_history
        }, 200



class ReportsResource(Resource):
    def get(self):
        admin, error = authenticate_admin()
        if error:
            return error

        parser = reqparse.RequestParser()
        parser.add_argument("category", type=str, location="args")
        parser.add_argument("severity", type=str, location="args")
        args = parser.parse_args()

        query = Incident.query
        if args["category"]:
            query = query.filter(Incident.category == args["category"])
        if args["severity"]:
            query = query.filter(Incident.severity == args["severity"])

        reports = query.order_by(Incident.created_at.desc()).all()

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
    def get(self):
        admin, error = authenticate_admin()
        if error:
            return error

        parser = reqparse.RequestParser()
        parser.add_argument("q", type=str, required=True, location="args")
        args = parser.parse_args()
        query_term = args["q"].strip()

        if not query_term:
            return {"success": False, "msg": "Search query cannot be empty"}, 400

        incidents = Incident.query.filter(
            or_(
                Incident.description.ilike(f"%{query_term}%"),
                Incident.category.ilike(f"%{query_term}%"),
                Incident.location.ilike(f"%{query_term}%"),
                Incident.severity.ilike(f"%{query_term}%"),
                Incident.reference.ilike(f"%{query_term}%")
            )
        ).order_by(Incident.created_at.desc()).all()

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
    def get(self):
        admin, error = authenticate_admin()
        if error:
            return error

        incidents = Incident.query.order_by(Incident.created_at.desc()).all()

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(["ID", "Reference", "Category", "Severity", "Location", "Description", "Created At", "User ID"])
        for inc in incidents:
            writer.writerow([
                inc.id,
                inc.reference or "",
                inc.category,
                inc.severity,
                inc.location,
                inc.description or "",
                inc.created_at.isoformat(),
                inc.user_id
            ])

        output.seek(0)
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=incident_reports.csv"}
        )