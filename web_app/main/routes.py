"""
Main routes for the web interface.
"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from web_app.main import main_bp
import config
import logging

# Get the bot instance
try:
    from main import bot
except ImportError:
    bot = None
    logging.warning("Bot instance not available. Running in demo mode.")

@main_bp.route('/')
@login_required
def index():
    """Render dashboard page."""
    return render_template('index.html', bot=bot, config=config)

@main_bp.route('/settings')
@login_required
def settings():
    """Render settings page."""
    return render_template('settings.html', bot=bot, config=config)

@main_bp.route('/charts')
@login_required
def charts():
    """Render charts page."""
    return render_template('charts.html', bot=bot, config=config)

@main_bp.route('/trades')
@login_required
def trades():
    """Render trades page."""
    return render_template('trades.html', bot=bot, config=config)

@main_bp.route('/logs')
@login_required
def logs():
    """Render logs page."""
    return render_template('logs.html', bot=bot, config=config)
