"""
Test script for the refactored web interface.
"""

# os module is used for environment variables in a full implementation
import logging
from web_app import create_app, socketio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create test configuration
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
    # Multi-timeframe analysis has been removed
}

# Create Flask application with test configuration
app = create_app(test_config)

if __name__ == '__main__':
    print("Starting web interface test...")
    socketio.run(app, host='0.0.0.0', port=test_config['WEB_PORT'], debug=test_config['DEBUG'])
