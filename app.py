import os
from datetime import datetime
import logging
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
import threading
import time
import random

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

# Connection state tracking
connection_state = {
    'healthy': True,
    'last_successful_connection': time.time(),
    'consecutive_failures': 0,
    'retry_count': 0
}

def reset_connection_state():
    """Reset the connection state tracking"""
    connection_state['healthy'] = True
    connection_state['consecutive_failures'] = 0
    connection_state['retry_count'] = 0
    connection_state['last_successful_connection'] = time.time()

def get_retry_delay():
    """Calculate retry delay with exponential backoff"""
    base_delay = 1
    max_delay = 60
    jitter = random.uniform(0, 0.1 * base_delay)
    delay = min(base_delay * (2 ** connection_state['retry_count']) + jitter, max_delay)
    return delay

# Database connection event handlers
@event.listens_for(Engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.info("Database connection established")
    reset_connection_state()

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
    connection_state['healthy'] = False
    connection_state['consecutive_failures'] += 1

def test_connection():
    """Test database connection with retry logic"""
    try:
        with db.engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
            if result == 1:
                reset_connection_state()
                return True
    except Exception as e:
        connection_state['healthy'] = False
        connection_state['consecutive_failures'] += 1
        connection_state['retry_count'] += 1
        logger.error(f"Database connection test failed: {e}")
        return False

def attempt_recovery():
    """Attempt to recover database connection"""
    while not connection_state['healthy']:
        delay = get_retry_delay()
        logger.info(f"Attempting connection recovery in {delay:.2f} seconds...")
        time.sleep(delay)
        
        if test_connection():
            logger.info("Database connection recovered successfully")
            return True
        
        # If we've had too many consecutive failures, log a critical error
        if connection_state['consecutive_failures'] >= 5:
            logger.critical("Multiple consecutive connection failures detected")
    
    return False

def heartbeat_worker():
    """Worker function to perform periodic connection tests with automatic recovery"""
    while True:
        try:
            if not connection_state['healthy']:
                attempt_recovery()
            else:
                with app.app_context():
                    if test_connection():
                        logger.debug("Heartbeat: Database connection is alive")
                    else:
                        logger.warning("Heartbeat: Database connection test failed")
                        attempt_recovery()
        except Exception as e:
            logger.error(f"Heartbeat: Error during connection check: {e}")
            connection_state['healthy'] = False
            attempt_recovery()
        
        # Wait for next heartbeat interval
        time.sleep(60)

# Add video player route
@app.route('/video/demo_video')
def video_player():
    return render_template('video_player.html')

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
