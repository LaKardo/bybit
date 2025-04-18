"""
Script to install the required dependencies for the web interface.
"""

import subprocess
import sys

def install_dependencies():
    """Install the required dependencies for the web interface."""
    dependencies = [
        'flask',
        'flask-login',
        'flask-socketio',
        'flask-wtf',
        'python-dotenv',
        'eventlet',  # For Socket.IO
    ]

    print("Installing dependencies...")
    for dependency in dependencies:
        print(f"Installing {dependency}...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', dependency])
            print(f"Successfully installed {dependency}")
        except subprocess.CalledProcessError:
            print(f"Failed to install {dependency}")

    print("\nAll dependencies installed.")
    print("You can now run the web interface using one of the following commands:")
    print("  - For development: python debug_web_app.py")
    print("  - For production: python production_web_app.py")

if __name__ == '__main__':
    install_dependencies()
