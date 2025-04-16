import os
import logging
import argparse
import sys
import socket
import threading
from web_app import create_app, socketio
import config
from check_python_version import check_python_version

# Configure logging
LOGS_DIR = 'logs'
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOGS_DIR, 'web_app.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE_PATH)
    ]
)

logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Bybit Trading Bot Web Interface')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to run the web interface on (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=config.WEB_PORT,
                        help=f'Port to run the web interface on (default: {config.WEB_PORT})')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode (default: False)')
    parser.add_argument('--production', action='store_true',
                        help='Run in production mode with optimized settings')
    parser.add_argument('--auto-port', action='store_true',
                        help='Automatically find an available port if the specified port is in use')
    return parser.parse_args()

def find_available_port(start_port, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    return None

def main():
    """Main entry point for the web application"""
    # Check Python version before starting the web app
    # This ensures we're running on Python 3.11 or higher
    check_python_version()

    args = parse_arguments()

    # Override config with environment variables if available
    if os.environ.get('WEB_PORT'):
        args.port = int(os.environ.get('WEB_PORT'))

    # Create app with appropriate configuration
    app_config = {}

    if args.production:
        app_config.update({
            'SECRET_KEY': os.environ.get('WEB_SECRET_KEY', config.WEB_SECRET_KEY),
            'WTF_CSRF_ENABLED': True,
            'DEBUG': False,
        })
        logger.info("Running in production mode")
    else:
        app_config.update({
            'DEBUG': args.debug or config.DEBUG,
        })
        if args.debug:
            logger.info("Running in debug mode")

    # Determine port, finding an available one if necessary
    port_to_use = args.port
    if args.auto_port:
        available_port = find_available_port(args.port)
        if available_port and available_port != args.port:
            logger.info(f"Port {args.port} is in use, using port {available_port} instead")
            port_to_use = available_port
        elif not available_port:
            logger.error(f"Could not find an available port after trying {args.port} through {args.port + 9}")
            print(f"Error: Could not find an available port. Please specify a different port with --port.")
            sys.exit(1)
    args.port = port_to_use # Update args with the final port

    # Create the Flask application
    app = create_app(app_config)

    # Print startup information
    print(f"Starting Bybit Trading Bot Web Interface on {args.host}:{args.port}...")
    print(f"Access the web interface at http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}")
    print(f"Login with username: {config.WEB_USERNAME}")

    try:
        # Run the application with Socket.IO
        # Python 3.11 has improved error messages and exception handling
        socketio.run(app, host=args.host, port=args.port, debug=app_config.get('DEBUG', False))
    except OSError as e:
        # More specific error handling for network-related issues
        logger.error(f"Network error starting the web interface: {e}", exc_info=True)
        print(f"Network error: Failed to start web interface on {args.host}:{args.port}")
        print(f"Reason: {e}")
        print("Please check if the port is already in use or if you have permission to bind to this address.")
        print("Try using the --auto-port flag to automatically find an available port.")
    except Exception as e:
        # Python 3.11 provides more detailed exception information
        logger.error(f"Error starting the web interface: {e}", exc_info=True)
        print(f"Error starting the web interface: {e}")
        print(f"Error type: {type(e).__name__}")

def run_web_app_in_thread(host=None, port=None, debug=False):
    """Run the web app in a separate thread

    Args:
        host (str): Host to bind to
        port (int): Port to bind to
        debug (bool): Whether to run in debug mode

    Returns:
        threading.Thread: The thread running the web app
    """
    host = host or config.WEB_HOST
    port = port or config.WEB_PORT
    debug = debug or config.WEB_DEBUG

    # Determine port, finding an available one if necessary
    port_to_use = port
    if port:
        available_port = find_available_port(port)
        if available_port and available_port != port:
            logger.info(f"Port {port} is in use, using port {available_port} instead")
            port_to_use = available_port
        elif not available_port:
            logger.error(f"Could not find an available port after trying {port} through {port + 9}")
            print(f"Error: Could not find an available port. Please specify a different port.")
            return None

    # Create app with appropriate configuration
    app_config = {
        'DEBUG': debug,
    }
    if not debug:
        app_config.update({
            'SECRET_KEY': os.environ.get('WEB_SECRET_KEY', config.WEB_SECRET_KEY),
            'WTF_CSRF_ENABLED': True,
        })

    # Create the Flask application
    app = create_app(app_config)

    def _run_web_app():
        try:
            # Use the determined port_to_use
            socketio.run(app, host=host, port=port_to_use, debug=app_config.get('DEBUG', False))
        except Exception as e:
            logger.error(f"Error running web app: {e}", exc_info=True)

    # Create and start the thread
    web_thread = threading.Thread(target=_run_web_app)
    web_thread.daemon = True
    web_thread.start()

    return web_thread

if __name__ == '__main__':
    main()
