import os
from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager

# Initialize SocketIO with async_mode='eventlet' for better compatibility with Python 3.11
socketio = SocketIO(async_mode='eventlet')
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
def create_app(config=None):
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    app.config.from_object('config')
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'dev-key-for-testing'
    if config:
        app.config.update(config)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)
    from web_app.auth import auth_bp
    from web_app.main import main_bp
    from web_app.api import api_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    from datetime import datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
    return app
