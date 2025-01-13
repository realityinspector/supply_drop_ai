import os
from datetime import datetime
import logging
import time
from flask import Flask, render_template
import threading
from extensions import init_extensions, db
from database import test_connection, attempt_recovery, connection_state, CONNECTION_MONITOR
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from filters import from_json
from fema import fema_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config=None):
    """Application factory function"""
    # Initialize Flask app
    app = Flask(__name__)

    # Ensure we have a secret key
    if not os.environ.get("FLASK_SECRET_KEY"):
        logger.warning("No FLASK_SECRET_KEY found in environment, using default key")
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_only_for_prototype")

    # Configure logging
    app.logger.setLevel(logging.INFO)

    # Database configuration moved to extensions.py
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
    app.config["UPLOAD_FOLDER"] = "uploads"

    # Initialize extensions with enhanced monitoring
    try:
        init_extensions(app)
        logger.info("Extensions initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize extensions: {str(e)}")
        raise

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Register template context processor
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    # Register blueprints
    try:
        from auth import auth_bp
        app.register_blueprint(auth_bp)

        from abbot import bp as abbot_bp
        app.register_blueprint(abbot_bp)

        from chat import chat_bp
        app.register_blueprint(chat_bp)

        from profile import profile_bp
        app.register_blueprint(profile_bp)

        app.register_blueprint(fema_bp)

        logger.info("All blueprints registered successfully")
    except Exception as e:
        logger.error(f"Failed to register blueprints: {str(e)}")
        raise

    # Initialize database tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise

    # Register custom filters
    app.jinja_env.filters['from_json'] = from_json

    return app

# Create application instance
app = create_app()

if __name__ == '__main__':
    try:
        logger.info("Starting Flask application")
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        logger.error(f"Failed to start Flask application: {str(e)}")
        raise