"""
Main blueprint for the web interface.
"""

from flask import Blueprint

main_bp = Blueprint('main', __name__)

from web_app.main import routes
