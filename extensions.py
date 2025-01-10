import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from flask import jsonify, request, redirect, url_for

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = "auth.login"

# Configure login manager to handle AJAX requests
@login_manager.unauthorized_handler
def unauthorized():
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(error='Authentication required'), 401
    return redirect(url_for('auth.login'))

def init_extensions(app):
    """Initialize Flask extensions"""
    # Configure SQLAlchemy
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,  # Recycle connections every 5 minutes
        "pool_pre_ping": True,  # Enable connection testing before use
        "pool_size": 10,  # Maximum number of persistent connections
        "max_overflow": 20,  # Maximum number of connections that can be created beyond pool_size
        "pool_timeout": 30,  # Timeout for getting a connection from the pool
    }
    
    # Initialize SQLAlchemy
    db.init_app(app)
    
    # Initialize Flask-Migrate
    migrate.init_app(app, db)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    
    # Initialize CSRF protection
    csrf.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return db.session.get(User, int(user_id))
