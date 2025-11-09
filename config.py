# config.py
from decouple import config
from datetime import timedelta


def _get_db_uri():
    uri = config('DATABASE_URL')
    if uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)
    if 'sslmode' not in uri:
        uri += ('&' if '?' in uri else '?') + 'sslmode=require'
    return uri

class Config:
    JWT_SECRET_KEY = config('JWT_SECRET_KEY')

    # Make access tokens expire in 14 days (2 weeks)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=14)
    # Keep refresh tokens slightly longer (optional) — e.g., 30 days
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    SQLALCHEMY_DATABASE_URI = _get_db_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    USSD_SHORTCODE = config('USSD_SHORTCODE')
    MAX_SESSION_MINUTES = config('MAX_SESSION_MINUTES', default=5, cast=int)

    # Connection pool health
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 5,
        'max_overflow': 10
    }