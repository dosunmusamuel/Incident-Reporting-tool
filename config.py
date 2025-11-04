# config.py
from decouple import config

def _get_db_uri():
    uri = config('DATABASE_URL')
    if uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)
    if 'sslmode' not in uri:
        uri += ('&' if '?' in uri else '?') + 'sslmode=require'
    return uri

class Config:
    JWT_SECRET_KEY = config('JWT_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = _get_db_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    USSD_SHORTCODE = config('USSD_SHORTCODE')
    MAX_SESSION_MINUTES = config('MAX_SESSION_MINUTES', default=5, cast=int)