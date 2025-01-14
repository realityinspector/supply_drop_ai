import os
from flask import Flask, render_template, session
from extensions import db
from rejection import rejection_bp
from resource_finder import resource_finder_bp
from sqlalchemy import text

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'uploads'
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(rejection_bp, url_prefix='/rejection')
    app.register_blueprint(resource_finder_bp, url_prefix='/resources')
    
    # Create database tables
    with app.app_context():
        # Drop all tables with CASCADE
        db.session.execute(text('DROP SCHEMA public CASCADE'))
        db.session.execute(text('CREATE SCHEMA public'))
        db.session.commit()
        
        # Create all tables fresh
        db.create_all()
    
    @app.route('/')
    def index():
        """Show the main dashboard"""
        return render_template('dashboard.html')
    
    @app.before_request
    def before_request():
        """Ensure session ID exists"""
        if 'session_id' not in session:
            session.permanent = True
            session['session_id'] = os.urandom(16).hex()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
