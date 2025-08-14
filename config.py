class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///incidents.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # USSD Configuration
    USSD_SHORTCODE = "*123#"
    MAX_SESSION_MINUTES = 5  # Session timeout