"""
Production server for the web interface.
This script runs the web interface using Eventlet, which is compatible with Socket.IO.
"""

import os
import logging
import eventlet
from web_app import create_app, socketio

# Patch standard library with eventlet
eventlet.monkey_patch()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('web_app_production.log')
    ]
)

# Create production configuration
production_config = {
    'SECRET_KEY': os.environ.get('WEB_SECRET_KEY', 'production-secret-key'),
    'WTF_CSRF_ENABLED': True,
    'DEBUG': False,
    'WEB_PORT': int(os.environ.get('WEB_PORT', 5000)),
    'WEB_USERNAME': os.environ.get('WEB_USERNAME', 'admin'),
    'WEB_PASSWORD': os.environ.get('WEB_PASSWORD', 'admin'),
}

# Create Flask application with production configuration
app = create_app(production_config)

if __name__ == '__main__':
    port = production_config['WEB_PORT']
    print(f"Starting Bybit Trading Bot Web Interface on port {port}...")
    print(f"Access the web interface at http://localhost:{port}")
    print(f"Login with username: {production_config['WEB_USERNAME']}")

    # Use socketio.run with eventlet
    try:
        socketio.run(app, host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"Error starting the web interface: {e}")
        logging.exception("Exception occurred when starting the web interface")
