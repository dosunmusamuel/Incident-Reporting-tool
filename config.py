# config.py
from decouple import config, Csv

class Config:
    # JWT
    JWT_SECRET_KEY = config('JWT_SECRET_KEY')

    # PostgreSQL – build the URI from env vars
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{config('POSTGRES_USER')}:{config('POSTGRES_PASSWORD')}@"
        f"{config('POSTGRES_HOST')}:{config('POSTGRES_PORT')}/{config('POSTGRES_DB')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # USSD
    USSD_SHORTCODE = config('USSD_SHORTCODE')
    MAX_SESSION_MINUTES = config('MAX_SESSION_MINUTES', default=5, cast=int)