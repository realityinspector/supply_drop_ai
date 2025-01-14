
from flask import Flask
from flask_migrate import Migrate
from extensions import db
from chat import chat_bp
from resource_finder import resource_finder_bp
import logging

def create_app():
    app = Flask(__name__)
    
    # Configure the app
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/postgres'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev'  # Change this in production
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Register blueprints
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(resource_finder_bp, url_prefix='/resources')
    
    return app
