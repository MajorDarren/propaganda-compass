import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-flask-secret-key')
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'news.db')
    WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'my-super-secret-passcode')