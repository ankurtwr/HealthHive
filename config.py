
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-fallback-key')


    WTF_CSRF_ENABLED = True

 
    SESSION_COOKIE_HTTPONLY = True   #
    SESSION_COOKIE_SAMESITE = 'Lax' 

    
    DB_HOST     = os.environ.get('DB_HOST',     'localhost')
    DB_USER     = os.environ.get('DB_USER',     'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'root')
    DB_NAME     = os.environ.get('DB_NAME',     'medcompare')