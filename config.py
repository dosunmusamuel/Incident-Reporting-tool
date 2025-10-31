class Config:
    # Jwt Secret Key For Development
    JWT_SECRET_KEY = "364577233bca3aa8e03dc710fdb320887e838534c76628a3ffdce9b7b1ea3e92"

    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///incidents.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # USSD Configuration
    USSD_SHORTCODE = "*123#"
    MAX_SESSION_MINUTES = 5  # Session timeout

    