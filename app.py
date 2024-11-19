import os
from datetime import datetime
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,  # Recycle connections every 5 minutes
    "pool_pre_ping": True,  # Enable connection testing before use
    "pool_size": 10,  # Maximum number of persistent connections
    "max_overflow": 20,  # Maximum number of connections that can be created beyond pool_size
    "pool_timeout": 30,  # Timeout for getting a connection from the pool
}
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
app.config["UPLOAD_FOLDER"] = "uploads"

# Database connection event handlers
@event.listens_for(Engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.info("Database connection established")

@event.listens_for(Engine, "engine_connect")
def engine_connect(connection):
    logger.info("Engine connection established")

@event.listens_for(Engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("Database connection checked out from pool")

@event.listens_for(Engine, "checkin")
def checkin(dbapi_connection, connection_record):
    logger.debug("Database connection returned to pool")

@event.listens_for(Engine, "invalidate")
def invalidate(dbapi_connection, connection_record, exception):
    logger.warning(f"Database connection invalidated due to error: {exception}")

def heartbeat_worker():
    """Worker function to perform periodic connection tests"""
    while True:
        try:
            with app.app_context():
                # Execute a simple query to test the connection
                # Using pool_pre_ping=True means we don't need to explicitly test
                # but we'll do a lightweight check anyway for monitoring
                with db.engine.connect() as connection:
                    result = connection.execute(text("SELECT 1")).scalar()
                    if result == 1:
                        logger.debug("Heartbeat: Database connection is alive")
        except Exception as e:
            logger.error(f"Heartbeat: Database connection error: {e}")
            # The pool_pre_ping will handle reconnection on next attempt
        time.sleep(60)  # Wait for 60 seconds before next heartbeat

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "auth.login"

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Add template context processor for datetime
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# Initialize heartbeat thread
heartbeat_thread = None
_is_heartbeat_initialized = False

def init_heartbeat():
    """Initialize the database heartbeat mechanism"""
    global heartbeat_thread, _is_heartbeat_initialized
    if not _is_heartbeat_initialized:
        heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
        heartbeat_thread.start()
        _is_heartbeat_initialized = True
        logger.info("Database heartbeat mechanism started")

@app.before_request
def before_request():
    """Initialize heartbeat before the first request if not in debug mode"""
    if not app.debug and not _is_heartbeat_initialized:
        init_heartbeat()

with app.app_context():
    import models
    from auth import auth_bp
    from chat import chat_bp
    from profile import profile_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(profile_bp)
    
    # Initialize database tables
    db.create_all()
    
    # Start heartbeat mechanism immediately if in production
    if not app.debug:
        init_heartbeat()
