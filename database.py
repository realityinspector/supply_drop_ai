import os
import logging
import time
from sqlalchemy import text, event
from sqlalchemy.engine import Engine
from extensions import db
from database_manager import DatabaseManager

# Configure logging with reduced verbosity
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Configure specific loggers
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('database_manager').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Initialize database manager singleton
db_manager = DatabaseManager()

# Export connection state and settings from manager for compatibility
connection_state = db_manager.connection_state
CONNECTION_MONITOR = db_manager.CONNECTION_MONITOR

def test_connection():
    """Test database connection using DatabaseManager"""
    return db_manager.test_connection(db)

def attempt_recovery():
    """Attempt database recovery using DatabaseManager"""
    return db_manager.attempt_recovery(db)

def get_connection_stats():
    """Get detailed connection pool statistics"""
    return db_manager.get_connection_stats(db)

# Set up event listeners through DatabaseManager
db_manager._setup_event_listeners()
