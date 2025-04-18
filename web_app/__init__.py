"""
Web interface for the Bybit Trading Bot.
This module initializes the Flask application and registers all blueprints.
"""

import os
from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager

# Initialize Socket.IO
socketio = SocketIO()

# Initialize login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')

    # Load default configuration
    app.config.from_object('config')

    # Ensure SECRET_KEY is set
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'dev-key-for-testing'

    # Override with instance config
    if config:
        app.config.update(config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize extensions
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # Register blueprints
    from web_app.auth import auth_bp
    from web_app.main import main_bp
    from web_app.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # Add template context processor for datetime
    from datetime import datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    return app
