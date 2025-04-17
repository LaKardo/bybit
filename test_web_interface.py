"""
Test script for the web interface.
This script creates a simplified version of the trading bot to test the web interface.
"""

import os
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_socketio import SocketIO
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired

# Configuration
WEB_HOST = "0.0.0.0"
WEB_PORT = 5000
WEB_DEBUG = True
WEB_SECRET_KEY = "test-secret-key"
WEB_USERNAME = "admin"
WEB_PASSWORD = "admin"

# Global variables
socketio = None

class LoginForm(FlaskForm):
    """Login form for web interface."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class User(UserMixin):
    """User class for authentication."""
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def check_password(self, password):
        """Check if password is correct."""
        return self.password == password

class MockBot:
    """Mock trading bot for testing."""
    def __init__(self):
        self.running = False
        self.symbol = "BTCUSDT"
        self.timeframe = "1h"
        self.dry_run = True
        
    def run(self):
        """Run the bot."""
        self.running = True
        print("Bot started")
        
        # Emit status update
        emit_status_update({
            'running': self.running,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'dry_run': self.dry_run,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # Emit log message
        emit_log("Bot started", "info")
        
        # Simulate bot activity
        for i in range(10):
            if not self.running:
                break
            
            emit_log(f"Bot activity {i+1}", "info")
            time.sleep(2)
        
        if self.running:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the bot."""
        self.running = False
        print("Bot stopped")
        
        # Emit status update
        emit_status_update({
            'running': self.running,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'dry_run': self.dry_run,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # Emit log message
        emit_log("Bot stopped", "info")

class WebInterface:
    """Web interface for the trading bot."""
    def __init__(self, bot):
        global socketio
        
        self.bot = bot
        
        # Initialize Flask app
        self.app = Flask(__name__, 
                         template_folder='templates',
                         static_folder='static')
        self.app.config['SECRET_KEY'] = WEB_SECRET_KEY
        
        # Initialize SocketIO
        socketio = SocketIO(self.app)
        
        # Initialize login manager
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = 'login'
        
        # Create user
        self.users = {
            WEB_USERNAME: User(1, WEB_USERNAME, WEB_PASSWORD)
        }
        
        # Register routes
        self._register_routes()
        
        # Register SocketIO events
        self._register_socketio_events()
        
        print("Web interface initialized")
    
    def _register_routes(self):
        """Register Flask routes."""
        @self.app.route('/')
        @login_required
        def index():
            """Render dashboard page."""
            return render_template('index.html', 
                                  bot=self.bot, 
                                  config={"WEB_USERNAME": WEB_USERNAME})
        
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            """Handle login."""
            if current_user.is_authenticated:
                return redirect(url_for('index'))
            
            form = LoginForm()
            if form.validate_on_submit():
                user = self.users.get(form.username.data)
                if user is None or not user.check_password(form.password.data):
                    flash('Invalid username or password')
                    return redirect(url_for('login'))
                
                login_user(user, remember=form.remember_me.data)
                return redirect(url_for('index'))
            
            return render_template('login.html', form=form)
        
        @self.app.route('/logout')
        def logout():
            """Handle logout."""
            logout_user()
            return redirect(url_for('login'))
        
        @self.app.route('/settings')
        @login_required
        def settings():
            """Render settings page."""
            return render_template('settings.html', 
                                  bot=self.bot, 
                                  config={"WEB_USERNAME": WEB_USERNAME})
        
        @self.app.route('/trades')
        @login_required
        def trades():
            """Render trades page."""
            return render_template('trades.html', 
                                  bot=self.bot, 
                                  config={"WEB_USERNAME": WEB_USERNAME})
        
        @self.app.route('/api/status')
        @login_required
        def api_status():
            """API endpoint for bot status."""
            return jsonify({
                'status': 'OK',
                'running': self.bot.running,
                'symbol': self.bot.symbol,
                'timeframe': self.bot.timeframe,
                'dry_run': self.bot.dry_run,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        @self.app.route('/api/start', methods=['POST'])
        @login_required
        def api_start():
            """API endpoint to start the bot."""
            if not self.bot.running:
                # Start the bot in a new thread
                threading.Thread(target=self.bot.run).start()
                
                return jsonify({
                    'status': 'OK',
                    'message': 'Bot started'
                })
            else:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot already running'
                })
        
        @self.app.route('/api/stop', methods=['POST'])
        @login_required
        def api_stop():
            """API endpoint to stop the bot."""
            if self.bot.running:
                self.bot.shutdown()
                
                return jsonify({
                    'status': 'OK',
                    'message': 'Bot stopped'
                })
            else:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not running'
                })
        
        @self.app.route('/api/balance')
        @login_required
        def api_balance():
            """API endpoint for account balance."""
            # Mock balance data
            balance = {
                'available_balance': 10000.00,
                'equity': 10500.00,
                'used_margin': 500.00,
                'unrealized_pnl': 500.00
            }
            
            return jsonify({
                'status': 'OK',
                'balance': balance
            })
        
        @self.app.route('/api/positions')
        @login_required
        def api_positions():
            """API endpoint for open positions."""
            # Mock positions data
            if self.bot.running:
                positions = [
                    {
                        'symbol': 'BTCUSDT',
                        'side': 'BUY',
                        'size': 0.1,
                        'entry_price': 65000.00,
                        'mark_price': 65500.00,
                        'unrealized_pnl': 500.00
                    }
                ]
            else:
                positions = []
            
            return jsonify({
                'status': 'OK',
                'positions': positions
            })
        
        @self.app.route('/api/close_position', methods=['POST'])
        @login_required
        def api_close_position():
            """API endpoint to close a position."""
            return jsonify({
                'status': 'OK',
                'message': 'Position closed'
            })
        
        @self.app.route('/api/update_settings', methods=['POST'])
        @login_required
        def api_update_settings():
            """API endpoint to update settings."""
            # Get settings from request
            data = request.json
            
            # Update settings
            if 'symbol' in data:
                self.bot.symbol = data['symbol']
            
            if 'timeframe' in data:
                self.bot.timeframe = data['timeframe']
            
            if 'dry_run' in data:
                self.bot.dry_run = data['dry_run']
            
            return jsonify({
                'status': 'OK',
                'message': 'Settings updated'
            })
        
        @self.login_manager.user_loader
        def load_user(user_id):
            """Load user by ID."""
            for user in self.users.values():
                if user.id == int(user_id):
                    return user
            return None
    
    def _register_socketio_events(self):
        """Register SocketIO events."""
        @socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            print("Client connected to SocketIO")
        
        @socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            print("Client disconnected from SocketIO")
    
    def run(self):
        """Run the web interface."""
        print(f"Starting Web Interface on {WEB_HOST}:{WEB_PORT}")
        socketio.run(self.app, host=WEB_HOST, port=WEB_PORT, debug=WEB_DEBUG, allow_unsafe_werkzeug=True)

def emit_log(message, level="info"):
    """Emit log message to connected clients."""
    if socketio:
        socketio.emit('log', {
            'message': message,
            'level': level,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

def emit_trade(trade_data):
    """Emit trade data to connected clients."""
    if socketio:
        socketio.emit('trade', trade_data)

def emit_status_update(status_data):
    """Emit status update to connected clients."""
    if socketio:
        socketio.emit('status_update', status_data)

if __name__ == "__main__":
    # Create mock bot
    bot = MockBot()
    
    # Create web interface
    web_interface = WebInterface(bot)
    
    # Run web interface
    web_interface.run()
