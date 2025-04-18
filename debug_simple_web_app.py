"""
Debug version of the simple web interface for the Bybit Trading Bot.
This script runs the web interface with detailed error logging.
"""

import os
import sys
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('web_app_debug.log')
    ]
)

# Create Flask application
app = Flask(__name__, 
            template_folder='templates', 
            static_folder='static')

# Configuration
app.config.update(
    SECRET_KEY='debug-secret-key',
    WTF_CSRF_ENABLED=True,
    DEBUG=True,
    WEB_PORT=5000,
    WEB_USERNAME='admin',
    WEB_PASSWORD='admin',
    DARK_MODE=False,
    SYMBOL='BTCUSDT',
    TIMEFRAME='15',
    LEVERAGE=10,
    DRY_RUN=True,
    RISK_PER_TRADE=0.015,
    RISK_REWARD_RATIO=2.0,
    SL_ATR_MULTIPLIER=1.5,
    FAST_EMA=12,
    SLOW_EMA=26,
    RSI_PERIOD=14,
    RSI_OVERBOUGHT=70,
    RSI_OVERSOLD=30,
    MULTI_TIMEFRAME_ENABLED=True,
    CONFIRMATION_TIMEFRAMES=['60', '240'],
    MTF_ALIGNMENT_REQUIRED=2
)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for authentication
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def check_password(self, password):
        return self.password == password

# Login form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    try:
        if int(user_id) == 1:
            return User(1, app.config['WEB_USERNAME'], app.config['WEB_PASSWORD'])
    except Exception as e:
        logging.error(f"Error loading user: {e}")
    return None

# Routes
@app.route('/')
@login_required
def index():
    """Render dashboard page."""
    try:
        return render_template('simple_index.html', config=app.config)
    except Exception as e:
        logging.error(f"Error rendering index page: {e}")
        return f"Error rendering index page: {e}", 500

@app.route('/settings')
@login_required
def settings():
    """Render settings page."""
    try:
        return render_template('settings.html', config=app.config)
    except Exception as e:
        logging.error(f"Error rendering settings page: {e}")
        return f"Error rendering settings page: {e}", 500

@app.route('/charts')
@login_required
def charts():
    """Render charts page."""
    try:
        return render_template('charts.html', config=app.config)
    except Exception as e:
        logging.error(f"Error rendering charts page: {e}")
        return f"Error rendering charts page: {e}", 500

@app.route('/trades')
@login_required
def trades():
    """Render trades page."""
    try:
        return render_template('trades.html', config=app.config)
    except Exception as e:
        logging.error(f"Error rendering trades page: {e}")
        return f"Error rendering trades page: {e}", 500

@app.route('/logs')
@login_required
def logs():
    """Render logs page."""
    try:
        return render_template('logs.html', config=app.config)
    except Exception as e:
        logging.error(f"Error rendering logs page: {e}")
        return f"Error rendering logs page: {e}", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login."""
    try:
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        form = LoginForm()
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = request.form.get('remember') == 'on'
            
            logging.debug(f"Login attempt: username={username}, remember={remember}")
            
            if username == app.config['WEB_USERNAME'] and password == app.config['WEB_PASSWORD']:
                user = User(1, app.config['WEB_USERNAME'], app.config['WEB_PASSWORD'])
                login_user(user, remember=remember)
                
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('index')
                
                logging.debug(f"Login successful, redirecting to {next_page}")
                return redirect(next_page)
            
            logging.warning(f"Invalid login attempt for username: {username}")
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        
        return render_template('debug_login.html', form=form)
    except Exception as e:
        logging.error(f"Error in login route: {e}")
        return f"Error in login route: {e}", 500

@app.route('/logout')
def logout():
    """Handle logout."""
    try:
        logout_user()
        flash('You have been logged out', 'info')
        return redirect(url_for('login'))
    except Exception as e:
        logging.error(f"Error in logout route: {e}")
        return f"Error in logout route: {e}", 500

# API endpoints
@app.route('/api/status', methods=['GET'])
@login_required
def get_status():
    """Get bot status."""
    try:
        return jsonify({
            'status': 'OK',
            'running': True,
            'mode': 'Demo',
            'uptime': '0:00:00',
            'last_update': '2023-01-01T00:00:00'
        })
    except Exception as e:
        logging.error(f"Error in get_status route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/balance', methods=['GET'])
@login_required
def get_balance():
    """Get account balance."""
    try:
        return jsonify({
            'total_equity': 10000.0,
            'available_balance': 8500.0,
            'position_margin': 1500.0,
            'unrealized_pnl': 250.0
        })
    except Exception as e:
        logging.error(f"Error in get_balance route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/positions', methods=['GET'])
@login_required
def get_positions():
    """Get open positions."""
    try:
        return jsonify([
            {
                'symbol': 'BTCUSDT',
                'side': 'Buy',
                'size': 0.1,
                'entry_price': 50000.0,
                'mark_price': 51000.0,
                'unrealized_pnl': 100.0,
                'leverage': 10,
                'liquidation_price': 45000.0,
                'timestamp': '2023-01-01T00:00:00'
            }
        ])
    except Exception as e:
        logging.error(f"Error in get_positions route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade_history', methods=['GET'])
@login_required
def get_trade_history():
    """Get trade history."""
    try:
        return jsonify([
            {
                'symbol': 'BTCUSDT',
                'side': 'Buy',
                'size': 0.1,
                'price': 50000.0,
                'pnl': 0.0,
                'fee': 5.0,
                'timestamp': '2023-01-01T00:00:00'
            },
            {
                'symbol': 'BTCUSDT',
                'side': 'Sell',
                'size': 0.1,
                'price': 51000.0,
                'pnl': 100.0,
                'fee': 5.1,
                'timestamp': '2023-01-01T01:00:00'
            }
        ])
    except Exception as e:
        logging.error(f"Error in get_trade_history route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market_data', methods=['GET'])
@login_required
def get_market_data():
    """Get market data."""
    try:
        import random
        
        # Generate random market data
        timestamps = [1672531200000 + i * 900000 for i in range(100)]  # Starting from 2023-01-01, 15-minute intervals
        open_prices = [random.normalvariate(50000, 1000) for _ in range(100)]
        high_prices = [o + random.normalvariate(500, 100) for o in open_prices]
        low_prices = [o - random.normalvariate(500, 100) for o in open_prices]
        close_prices = [o + random.normalvariate(0, 200) for o in open_prices]
        volumes = [random.normalvariate(100, 20) for _ in range(100)]
        
        return jsonify({
            'timestamp': timestamps,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes
        })
    except Exception as e:
        logging.error(f"Error in get_market_data route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_settings', methods=['POST'])
@login_required
def update_settings():
    """Update bot settings."""
    try:
        return jsonify({
            'status': 'OK',
            'message': 'Settings updated successfully (Demo mode)'
        })
    except Exception as e:
        logging.error(f"Error in update_settings route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/start_bot', methods=['POST'])
@login_required
def start_bot():
    """Start the trading bot."""
    try:
        return jsonify({
            'status': 'OK',
            'message': 'Bot started successfully (Demo mode)'
        })
    except Exception as e:
        logging.error(f"Error in start_bot route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop_bot', methods=['POST'])
@login_required
def stop_bot():
    """Stop the trading bot."""
    try:
        return jsonify({
            'status': 'OK',
            'message': 'Bot stopped successfully (Demo mode)'
        })
    except Exception as e:
        logging.error(f"Error in stop_bot route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
@login_required
def get_logs():
    """Get bot logs."""
    try:
        return jsonify([
            {
                'timestamp': '2023-01-01T00:00:00',
                'level': 'INFO',
                'message': 'Bot started in demo mode'
            },
            {
                'timestamp': '2023-01-01T00:01:00',
                'level': 'INFO',
                'message': 'Connecting to Bybit API'
            },
            {
                'timestamp': '2023-01-01T00:02:00',
                'level': 'INFO',
                'message': 'Successfully connected to Bybit API'
            },
            {
                'timestamp': '2023-01-01T00:03:00',
                'level': 'INFO',
                'message': 'Analyzing market data for BTCUSDT'
            },
            {
                'timestamp': '2023-01-01T00:04:00',
                'level': 'INFO',
                'message': 'No trading signals detected'
            }
        ])
    except Exception as e:
        logging.error(f"Error in get_logs route: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = app.config['WEB_PORT']
    print(f"Starting Debug Bybit Trading Bot Web Interface on port {port}...")
    print(f"Access the web interface at http://localhost:{port}")
    print(f"Login with username: {app.config['WEB_USERNAME']} and password: {app.config['WEB_PASSWORD']}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        print(f"Error starting the web interface: {e}")
        logging.exception("Exception occurred when starting the web interface")
