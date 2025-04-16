from flask import render_template
from flask_login import login_required
from web_app.main import main_bp
import config
import logging
from web_app.bot_integration import get_bot_instance

# Helper function to get the bot instance
def get_bot():
    return get_bot_instance()
@main_bp.route('/')
@login_required
def index():
    try:
        bot = get_bot()
        return render_template('index.html', bot=bot, config=config)
    except Exception as e:
        logging.error(f"Error rendering index page: {e}")
        return render_template('error.html', error=str(e), config=config)
@main_bp.route('/settings')
@login_required
def settings():
    bot = get_bot()
    return render_template('settings.html', bot=bot, config=config)
@main_bp.route('/charts')
@login_required
def charts():
    bot = get_bot()
    return render_template('charts.html', bot=bot, config=config)
@main_bp.route('/trades')
@login_required
def trades():
    bot = get_bot()
    return render_template('trades.html', bot=bot, config=config)
@main_bp.route('/logs')
@login_required
def logs():
    bot = get_bot()
    return render_template('logs.html', bot=bot, config=config)
@main_bp.route('/health')
@login_required
def health():
    bot = get_bot()
    return render_template('health.html', bot=bot, config=config)
@main_bp.route('/metrics')
@login_required
def metrics():
    bot = get_bot()
    return render_template('metrics.html', bot=bot, config=config)
@main_bp.route('/failover')
@login_required
def failover():
    bot = get_bot()
    return render_template('failover.html', bot=bot, config=config)
