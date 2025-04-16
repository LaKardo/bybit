import logging
from datetime import datetime
from flask import jsonify, request
from flask_login import login_required
from web_app.api import api_bp
from web_app import socketio
import config

# Get the bot instance from the bot_integration module
from web_app.bot_integration import get_bot_instance

# Helper function to get the bot instance
def get_bot():
    return get_bot_instance()
@api_bp.route('/status', methods=['GET'])
@login_required
def get_status():
    bot = get_bot()
    if bot:
        try:
            return jsonify({
                'status': 'OK',
                'running': bot.is_running,
                'mode': 'Live' if not config.DRY_RUN else 'Dry Run',
                'uptime': bot.get_uptime(),
                'last_update': bot.last_update.isoformat() if hasattr(bot, 'last_update') else None
            })
        except Exception as e:
            logging.error(f"Error getting bot status: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        return jsonify({
            'status': 'ERROR',
            'message': 'Bot not initialized'
        }), 500
@api_bp.route('/balance', methods=['GET'])
@login_required
def get_balance():
    bot = get_bot()
    if bot:
        try:
            balance = bot.get_balance()
            return jsonify(balance)
        except Exception as e:
            logging.error(f"Error getting balance: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        return jsonify({
            'status': 'ERROR',
            'message': 'Bot not initialized'
        }), 500
@api_bp.route('/positions', methods=['GET'])
@login_required
def get_positions():
    bot = get_bot()
    if bot:
        try:
            positions = bot.get_positions()
            return jsonify(positions)
        except Exception as e:
            logging.error(f"Error getting positions: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        return jsonify({
            'status': 'ERROR',
            'message': 'Bot not initialized'
        }), 500
@api_bp.route('/performance', methods=['GET'])
@login_required
def get_performance_data():
    bot = get_bot()
    if bot and hasattr(bot, 'health_check'):
        try:
            metrics = bot.health_check.get_performance_metrics()
            # Assuming get_performance_metrics returns a dict like {'total_trades': ..., 'win_rate': ..., ...}
            # Format the response to match frontend expectation (data.performance with equity_curve)
            response_data = {
                'status': 'OK',
                'performance': {
                    'total_trades': metrics.get('trading_metrics', {}).get('trades_total', 0),
                    'win_rate': metrics.get('trading_metrics', {}).get('win_rate', 0),
                    'profit_factor': metrics.get('trading_metrics', {}).get('profit_factor', 0),
                    'total_pnl': metrics.get('trading_metrics', {}).get('total_pnl', 0),
                    'equity_curve': metrics.get('equity_curve', []) # Include equity_curve if available, otherwise empty
                }
            }
            return jsonify(response_data)
        except Exception as e:
            logging.error(f"Error getting performance data: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        return jsonify({
            'status': 'ERROR',
            'message': 'Bot not initialized or health check not available'
        }), 500

@api_bp.route('/market_data', methods=['GET'])
@login_required
def get_market_data():
    bot = get_bot()
    symbol = request.args.get('symbol', config.SYMBOL)
    interval = request.args.get('interval', config.TIMEFRAME)
    if bot:
        try:
            data = bot.get_market_data(symbol, interval)
            return jsonify(data)
        except Exception as e:
            logging.error(f"Error getting market data: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        return jsonify({
            'status': 'ERROR',
            'message': 'Bot not initialized'
        }), 500
@api_bp.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    bot = get_bot()
    if not request.is_json:
        return jsonify({
            'status': 'ERROR',
            'message': 'Invalid request format. JSON expected.'
        }), 400
    settings = request.get_json()
    if bot:
        try:
            bot.update_settings(settings)
            return jsonify({
                'status': 'OK',
                'message': 'Settings updated successfully'
            })
        except Exception as e:
            logging.error(f"Error updating settings: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        return jsonify({
            'status': 'ERROR',
            'message': 'Bot not initialized'
        }), 500
@api_bp.route('/start_bot', methods=['POST'])
@login_required
def start_bot():
    bot = get_bot()
    if bot:
        try:
            bot.start()
            return jsonify({
                'status': 'OK',
                'message': 'Bot started successfully'
            })
        except Exception as e:
            logging.error(f"Error starting bot: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        return jsonify({
            'status': 'ERROR',
            'message': 'Bot not initialized'
        }), 500
@api_bp.route('/stop_bot', methods=['POST'])
@login_required
def stop_bot():
    bot = get_bot()
    if bot:
        try:
            bot.stop()
            return jsonify({
                'status': 'OK',
                'message': 'Bot stopped successfully'
            })
        except Exception as e:
            logging.error(f"Error stopping bot: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        return jsonify({
            'status': 'ERROR',
            'message': 'Bot not initialized'
        }), 500
@api_bp.route('/logs', methods=['GET'])
@login_required
def get_logs():
    bot = get_bot()
    limit = request.args.get('limit', 100, type=int)
    if bot:
        try:
            # Assuming the bot instance has a logger attribute which has get_logs
            if hasattr(bot, 'logger') and hasattr(bot.logger, 'get_logs'):
                logs = bot.logger.get_logs(limit)
            else:
                # Fallback or error handling if logger or get_logs is not available
                logging.warning("Bot instance does not have a logger with get_logs method.")
                logs = [] # Return empty list or appropriate error response
            return jsonify(logs)
        except Exception as e:
            logging.error(f"Error getting logs: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        return jsonify({
            'status': 'ERROR',
            'message': 'Bot not initialized'
        }), 500
@socketio.on('connect')
def handle_connect():
    logging.info('Client connected')
@socketio.on('disconnect')
def handle_disconnect():
    logging.info('Client disconnected')
@api_bp.route('/health', methods=['GET'])
@login_required
def get_health():
    bot = get_bot()
    if bot and hasattr(bot, 'health_check'):
        try:
            health_summary = bot.health_check.get_health_summary()
            return jsonify(health_summary)
        except Exception as e:
            logging.error(f"Error getting health check summary: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        return jsonify({
            'status': 'ERROR',
            'message': 'Bot not initialized'
        }), 500
@api_bp.route('/health/history', methods=['GET'])
@login_required
def get_health_history():
    bot = get_bot()
    hours = request.args.get('hours', 24, type=int)
    if bot and hasattr(bot, 'health_check'):
        try:
            history = bot.health_check.get_health_history(hours=hours)
            return jsonify(history)
        except Exception as e:
            logging.error(f"Error getting health check history: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        return jsonify({
            'status': 'ERROR',
            'message': 'Bot not initialized'
        }), 500
@api_bp.route('/health/performance', methods=['GET'])
@login_required
def get_performance_metrics():
    bot = get_bot()
    if bot and hasattr(bot, 'health_check'):
        try:
            metrics = bot.health_check.get_performance_metrics()
            metrics['trading_metrics'] = bot.health_check.trading_metrics
            return jsonify(metrics)
        except Exception as e:
            logging.error(f"Error getting performance metrics: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        return jsonify({
            'status': 'ERROR',
            'message': 'Bot not initialized'
        }), 500
def emit_market_data_updates():
    bot = get_bot()
    if bot:
        try:
            data = bot.get_market_data(config.SYMBOL, config.TIMEFRAME)
            socketio.emit('market_data_update', data)
        except Exception as e:
            logging.error(f"Error emitting market data updates: {e}")
    else:
        logging.error("Cannot emit market data updates: Bot not initialized")
def emit_health_check_updates():
    bot = get_bot()
    if bot and hasattr(bot, 'health_check'):
        try:
            health_summary = bot.health_check.get_health_summary()
            socketio.emit('health_update', health_summary)
        except Exception as e:
            logging.error(f"Error emitting health check updates: {e}")
    else:
        logging.error("Cannot emit health updates: Bot not initialized")
