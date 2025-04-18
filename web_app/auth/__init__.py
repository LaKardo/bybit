"""
Authentication blueprint for the web interface.
"""

from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

from web_app.auth import routes
