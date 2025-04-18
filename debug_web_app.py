"""
Debug script for the web interface.
This script runs the web interface with detailed error logging.
"""

import os
import sys
import logging
from web_app import create_app, socketio

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('web_app_debug.log')
    ]
)

# Create test configuration with debugging enabled
test_config = {
    'SECRET_KEY': 'test-secret-key',
    'WTF_CSRF_ENABLED': True,
    'DEBUG': True,
    'WEB_PORT': 5000,
    'WEB_USERNAME': 'admin',
    'WEB_PASSWORD': 'admin',
    'DARK_MODE': False,
    'SYMBOL': 'BTCUSDT',
    'TIMEFRAME': '15',
    'LEVERAGE': 10,
    'DRY_RUN': True,
    'RISK_PER_TRADE': 0.015,
    'RISK_REWARD_RATIO': 2.0,
    'SL_ATR_MULTIPLIER': 1.5,
    'FAST_EMA': 12,
    'SLOW_EMA': 26,
    'RSI_PERIOD': 14,
    'RSI_OVERBOUGHT': 70,
    'RSI_OVERSOLD': 30,
    'MULTI_TIMEFRAME_ENABLED': True,
    'CONFIRMATION_TIMEFRAMES': ['60', '240'],
    'MTF_ALIGNMENT_REQUIRED': 2
}

# Create Flask application with test configuration
app = create_app(test_config)

# Add a route to test if the app is running
@app.route('/test')
def test():
    return 'Web interface is running!'

if __name__ == '__main__':
    print("Starting web interface in debug mode...")
    print(f"Access the web interface at http://localhost:{test_config['WEB_PORT']}")
    print(f"Login with username: {test_config['WEB_USERNAME']} and password: {test_config['WEB_PASSWORD']}")
    print("Press Ctrl+C to stop the server")
    
    try:
        socketio.run(app, host='0.0.0.0', port=test_config['WEB_PORT'], debug=test_config['DEBUG'])
    except Exception as e:
        print(f"Error starting the web interface: {e}")
        logging.exception("Exception occurred when starting the web interface")
