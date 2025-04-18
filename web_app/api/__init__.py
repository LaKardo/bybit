"""
API blueprint for the web interface.
"""

from flask import Blueprint

api_bp = Blueprint('api', __name__)

from web_app.api import routes
