"""
Run the web interface for the Bybit Trading Bot.
"""

import logging
from web_app import create_app, socketio
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('web_app.log')
    ]
)

# Create Flask application
app = create_app()

if __name__ == '__main__':
    print(f"Starting Bybit Trading Bot Web Interface on port {config.WEB_PORT}...")
    socketio.run(app, host='0.0.0.0', port=config.WEB_PORT, debug=config.DEBUG)
