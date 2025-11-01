from flask_restful import Api
from resources.auth import RegisterResource, LoginResource, LogoutAccessResource, LogoutRefreshResource, RefreshResource
from resources.dashboard import DashboardResource,IncidentSearchResource,ReportsResource,ExportReportsCSVResource
#from resources.incidents import IncidentListResource, IncidentResource, IncidentSummaryResource, IncidentStatsResource

def register_routes(app):
    api = Api(app)
    api.add_resource(RegisterResource, "/api/auth/register")
    api.add_resource(LoginResource, "/api/auth/login")
    api.add_resource(LogoutAccessResource, "/api/auth/logout/")
    api.add_resource(LogoutRefreshResource, "/api/auth/logout/refresh")
    api.add_resource(RefreshResource, "/api/auth/refresh")

    


    api.add_resource(DashboardResource, "/api/dashboard")
    api.add_resource(ReportsResource, "/api/reports")
    api.add_resource(IncidentSearchResource, "/api/search")
    api.add_resource(ExportReportsCSVResource, "/api/export")
