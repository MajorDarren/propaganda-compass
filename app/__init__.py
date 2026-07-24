from flask import Flask
from config import Config
from app.database import init_db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db(app.config['DATABASE_PATH'])

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app