"""
Very simple web interface for the Bybit Trading Bot.
This version has minimal dependencies and is designed to be as simple as possible.
"""

import os
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('web_app_simple.log')
    ]
)

# Create Flask application
app = Flask(__name__, 
            template_folder='templates', 
            static_folder='static')

# Configuration
app.config.update(
    SECRET_KEY='very-simple-secret-key',
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

# Simple login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
@login_required
def index():
    """Render dashboard page."""
    return render_template('very_simple_index.html', config=app.config)

@app.route('/settings')
@login_required
def settings():
    """Render settings page."""
    return render_template('very_simple_settings.html', config=app.config)

@app.route('/charts')
@login_required
def charts():
    """Render charts page."""
    return render_template('very_simple_charts.html', config=app.config)

@app.route('/trades')
@login_required
def trades():
    """Render trades page."""
    return render_template('very_simple_trades.html', config=app.config)

@app.route('/logs')
@login_required
def logs():
    """Render logs page."""
    return render_template('very_simple_logs.html', config=app.config)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login."""
    if 'logged_in' in session:
        return redirect(url_for('index'))
    
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        if username == app.config['WEB_USERNAME'] and password == app.config['WEB_PASSWORD']:
            session['logged_in'] = True
            session['username'] = username
            
            if remember:
                session.permanent = True
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('index')
            
            flash('You have been logged in successfully', 'success')
            return redirect(next_page)
        
        error = 'Invalid username or password'
    
    return render_template('very_simple_login.html', error=error)

@app.route('/logout')
def logout():
    """Handle logout."""
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# API endpoints
@app.route('/api/status', methods=['GET'])
@login_required
def get_status():
    """Get bot status."""
    return jsonify({
        'status': 'OK',
        'running': True,
        'mode': 'Demo',
        'uptime': '0:00:00',
        'last_update': '2023-01-01T00:00:00'
    })

@app.route('/api/balance', methods=['GET'])
@login_required
def get_balance():
    """Get account balance."""
    return jsonify({
        'total_equity': 10000.0,
        'available_balance': 8500.0,
        'position_margin': 1500.0,
        'unrealized_pnl': 250.0
    })

@app.route('/api/positions', methods=['GET'])
@login_required
def get_positions():
    """Get open positions."""
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

@app.route('/api/trade_history', methods=['GET'])
@login_required
def get_trade_history():
    """Get trade history."""
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

@app.route('/api/market_data', methods=['GET'])
@login_required
def get_market_data():
    """Get market data."""
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

@app.route('/api/update_settings', methods=['POST'])
@login_required
def update_settings():
    """Update bot settings."""
    return jsonify({
        'status': 'OK',
        'message': 'Settings updated successfully (Demo mode)'
    })

@app.route('/api/start_bot', methods=['POST'])
@login_required
def start_bot():
    """Start the trading bot."""
    return jsonify({
        'status': 'OK',
        'message': 'Bot started successfully (Demo mode)'
    })

@app.route('/api/stop_bot', methods=['POST'])
@login_required
def stop_bot():
    """Stop the trading bot."""
    return jsonify({
        'status': 'OK',
        'message': 'Bot stopped successfully (Demo mode)'
    })

@app.route('/api/logs', methods=['GET'])
@login_required
def get_logs():
    """Get bot logs."""
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

if __name__ == '__main__':
    port = app.config['WEB_PORT']
    print(f"Starting Very Simple Bybit Trading Bot Web Interface on port {port}...")
    print(f"Access the web interface at http://localhost:{port}")
    print(f"Login with username: {app.config['WEB_USERNAME']} and password: {app.config['WEB_PASSWORD']}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        print(f"Error starting the web interface: {e}")
        logging.exception("Exception occurred when starting the web interface")
