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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def heartbeat_worker(app):
    """Enhanced worker function to perform periodic connection tests with smart recovery"""
    consecutive_failures = 0
    while True:
        try:
            with app.app_context():
                from database import db_manager, connection_state, CONNECTION_MONITOR
                
                current_state = "unhealthy" if not db_manager.connection_state['healthy'] else "healthy"
                logger.info(f"Heartbeat check starting. Current state: {current_state}")
                
                if not db_manager.connection_state['healthy']:
                    # Aggressive recovery mode with exponential backoff
                    if consecutive_failures > CONNECTION_MONITOR['CRITICAL_FAILURE_THRESHOLD']:
                        logger.warning("Critical failure threshold reached - implementing circuit breaker")
                        time.sleep(min(CONNECTION_MONITOR['BASE_DELAY'] * (2 ** consecutive_failures), 
                                    CONNECTION_MONITOR['MAX_DELAY']))
                    
                    if db_manager.attempt_recovery(db):
                        logger.info("Recovery successful - resuming normal operation")
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        logger.error(
                            "Recovery failed - system in degraded state\n"
                            f"Last error: {db_manager.connection_state['last_error']}\n"
                            f"Total attempts: {db_manager.connection_state['total_reconnect_attempts']}\n"
                            f"Consecutive failures: {consecutive_failures}"
                        )
                else:
                    # Enhanced proactive health check with detailed monitoring
                    try:
                        if db_manager.test_connection(db):
                            logger.debug(
                                "Heartbeat: Database connection is alive\n"
                                f"Current pool size: {db_manager.connection_state['pool_size_current']}\n"
                                f"Connection latency: {db_manager.connection_state['connection_latency']:.3f}s\n"
                                f"Cache hit ratio: {db_manager.connection_state.get('transaction_stats', {}).get('cache_hit_ratio', 0):.2%}"
                            )
                            consecutive_failures = 0
                        else:
                            logger.warning("Heartbeat: Database connection test failed - initiating recovery")
                            db_manager.attempt_recovery(db)
                            consecutive_failures += 1
                    except Exception as e:
                        logger.error(f"Health check failed: {str(e)}")
                        consecutive_failures += 1
                        db_manager.connection_state['healthy'] = False
                
                # Dynamic health check interval based on system health
                if consecutive_failures > 0:
                    # More frequent checks when there are issues, with exponential backoff for severe cases
                    check_interval = max(
                        CONNECTION_MONITOR['HEALTH_CHECK_INTERVAL'] // (2 ** min(consecutive_failures, 3)),
                        CONNECTION_MONITOR['BASE_DELAY']
                    )
                else:
                    check_interval = CONNECTION_MONITOR['HEALTH_CHECK_INTERVAL']
                
        except Exception as e:
            logger.error(
                f"Heartbeat: Critical error during connection check: {e}\n"
                "Initiating emergency recovery procedure"
            )
            connection_state['healthy'] = False
            connection_state['last_error'] = str(e)
            attempt_recovery()
            check_interval = CONNECTION_MONITOR['BASE_DELAY']
        
        # Wait for next heartbeat interval
        time.sleep(check_interval)

def create_app(config=None):
    """Application factory function"""
    # Initialize Flask app
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
    
    # Add configuration for heartbeat
    app.config['_is_heartbeat_initialized'] = False
    app.config['heartbeat_thread'] = None
    
    # Add video player route
    @app.route('/video/demo_video')
    def video_player():
        return render_template('video_player.html')
    # Database configuration moved to extensions.py
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
    app.config["UPLOAD_FOLDER"] = "uploads"

    # Initialize extensions with enhanced monitoring
    init_extensions(app)

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Register template context processor
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    def init_heartbeat(app):
        """Initialize the database heartbeat mechanism"""
        if not app.config['_is_heartbeat_initialized']:
            app.config['heartbeat_thread'] = threading.Thread(target=lambda: heartbeat_worker(app), daemon=True)
            app.config['heartbeat_thread'].start()
            app.config['_is_heartbeat_initialized'] = True
            logger.info("Database heartbeat mechanism started")

    @app.before_request
    def before_request():
        """Initialize heartbeat before the first request if not in debug mode"""
        if not app.debug and not app.config['_is_heartbeat_initialized']:
            init_heartbeat(app)

    # Register blueprints
    from auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from abbot import bp as abbot_bp
    app.register_blueprint(abbot_bp)
    
    from chat import chat_bp
    app.register_blueprint(chat_bp)
    from profile import profile_bp
    app.register_blueprint(profile_bp)
    app.register_blueprint(fema_bp)

    # Initialize database tables
    with app.app_context():
        db.create_all()
        
        # Start heartbeat mechanism immediately if in production
        if not app.debug and not app.config['_is_heartbeat_initialized']:
            init_heartbeat(app)

    # Register custom filters
    app.jinja_env.filters['from_json'] = from_json

    return app

# Create application instance
app = create_app()

# Remove duplicate route as it's already defined in create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
