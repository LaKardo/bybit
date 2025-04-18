"""
API routes for the web interface.
"""

import json
import logging
from datetime import datetime, timedelta
from flask import jsonify, request
from flask_login import login_required
from web_app.api import api_bp
from web_app import socketio
import config
# Try to import numpy and pandas, but provide fallbacks if they're not available
try:
    import numpy as np
    import pandas as pd
    NUMPY_AVAILABLE = True
except ImportError:
    import random
    NUMPY_AVAILABLE = False
    # Create a simple random number generator as a fallback
    def random_normal(mean, std_dev, size=1):
        return [random.normalvariate(mean, std_dev) for _ in range(size)]
    # Let the code know to use our fallback

# Get the bot instance
try:
    from main import bot
except ImportError:
    bot = None
    logging.warning("Bot instance not available. Running in demo mode.")

# Helper function to generate mock data for demo mode
def generate_mock_data():
    """Generate mock data for demo mode."""
    # Generate timestamps for market data
    timestamps = [(datetime.now() - timedelta(minutes=i*15)).timestamp() * 1000 for i in range(100, 0, -1)]

    # Generate price and volume data based on whether numpy is available
    if NUMPY_AVAILABLE:
        open_prices = [np.random.normal(50000, 1000) for _ in range(100)]
        high_prices = [np.random.normal(50500, 1000) for _ in range(100)]
        low_prices = [np.random.normal(49500, 1000) for _ in range(100)]
        close_prices = [np.random.normal(50000, 1000) for _ in range(100)]
        volumes = [np.random.normal(100, 20) for _ in range(100)]
    else:
        # Use our fallback random generator
        open_prices = random_normal(50000, 1000, 100)
        high_prices = random_normal(50500, 1000, 100)
        low_prices = random_normal(49500, 1000, 100)
        close_prices = random_normal(50000, 1000, 100)
        volumes = random_normal(100, 20, 100)

    return {
        'balance': {
            'total_equity': 10000.0,
            'available_balance': 8500.0,
            'position_margin': 1500.0,
            'unrealized_pnl': 250.0
        },
        'positions': [
            {
                'symbol': 'BTCUSDT',
                'side': 'Buy',
                'size': 0.1,
                'entry_price': 50000.0,
                'mark_price': 51000.0,
                'unrealized_pnl': 100.0,
                'leverage': 10,
                'liquidation_price': 45000.0,
                'timestamp': datetime.now().isoformat()
            }
        ],
        'trades': [
            {
                'symbol': 'BTCUSDT',
                'side': 'Buy',
                'size': 0.1,
                'price': 50000.0,
                'pnl': 0.0,
                'fee': 5.0,
                'timestamp': (datetime.now() - timedelta(hours=2)).isoformat()
            },
            {
                'symbol': 'BTCUSDT',
                'side': 'Sell',
                'size': 0.1,
                'price': 51000.0,
                'pnl': 100.0,
                'fee': 5.1,
                'timestamp': (datetime.now() - timedelta(hours=1)).isoformat()
            }
        ],
        'market_data': {
            'BTCUSDT': {
                'timestamp': timestamps,
                'open': open_prices,
                'high': high_prices,
                'low': low_prices,
                'close': close_prices,
                'volume': volumes
            }
        }
    }

# Mock data for demo mode
mock_data = generate_mock_data()

@api_bp.route('/status', methods=['GET'])
@login_required
def get_status():
    """Get bot status."""
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
        # Demo mode
        return jsonify({
            'status': 'OK',
            'running': True,
            'mode': 'Demo',
            'uptime': '0:00:00',
            'last_update': datetime.now().isoformat()
        })

@api_bp.route('/balance', methods=['GET'])
@login_required
def get_balance():
    """Get account balance."""
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
        # Demo mode
        return jsonify(mock_data['balance'])

@api_bp.route('/positions', methods=['GET'])
@login_required
def get_positions():
    """Get open positions."""
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
        # Demo mode
        return jsonify(mock_data['positions'])

@api_bp.route('/trade_history', methods=['GET'])
@login_required
def get_trade_history():
    """Get trade history."""
    if bot:
        try:
            trades = bot.get_trade_history()
            return jsonify(trades)
        except Exception as e:
            logging.error(f"Error getting trade history: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        # Demo mode
        return jsonify(mock_data['trades'])

@api_bp.route('/market_data', methods=['GET'])
@login_required
def get_market_data():
    """Get market data."""
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
        # Demo mode
        if symbol in mock_data['market_data']:
            return jsonify(mock_data['market_data'][symbol])
        else:
            return jsonify({
                'status': 'ERROR',
                'message': f"Symbol {symbol} not found"
            }), 404

@api_bp.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    """Update bot settings."""
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
        # Demo mode
        return jsonify({
            'status': 'OK',
            'message': 'Settings updated successfully (Demo mode)'
        })

@api_bp.route('/start_bot', methods=['POST'])
@login_required
def start_bot():
    """Start the trading bot."""
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
        # Demo mode
        return jsonify({
            'status': 'OK',
            'message': 'Bot started successfully (Demo mode)'
        })

@api_bp.route('/stop_bot', methods=['POST'])
@login_required
def stop_bot():
    """Stop the trading bot."""
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
        # Demo mode
        return jsonify({
            'status': 'OK',
            'message': 'Bot stopped successfully (Demo mode)'
        })

@api_bp.route('/logs', methods=['GET'])
@login_required
def get_logs():
    """Get bot logs."""
    limit = request.args.get('limit', 100, type=int)

    if bot:
        try:
            logs = bot.get_logs(limit)
            return jsonify(logs)
        except Exception as e:
            logging.error(f"Error getting logs: {e}")
            return jsonify({
                'status': 'ERROR',
                'message': str(e)
            }), 500
    else:
        # Demo mode
        return jsonify([
            {
                'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
                'level': 'INFO',
                'message': 'Bot started in demo mode'
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=4)).isoformat(),
                'level': 'INFO',
                'message': 'Connecting to Bybit API'
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=3)).isoformat(),
                'level': 'INFO',
                'message': 'Successfully connected to Bybit API'
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=2)).isoformat(),
                'level': 'INFO',
                'message': 'Analyzing market data for BTCUSDT'
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=1)).isoformat(),
                'level': 'INFO',
                'message': 'No trading signals detected'
            }
        ])

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logging.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logging.info('Client disconnected')

# Emit market data updates periodically
def emit_market_data_updates():
    """Emit market data updates to connected clients."""
    if bot:
        try:
            data = bot.get_market_data(config.SYMBOL, config.TIMEFRAME)
            socketio.emit('market_data_update', data)
        except Exception as e:
            logging.error(f"Error emitting market data updates: {e}")
    else:
        # Demo mode
        socketio.emit('market_data_update', mock_data['market_data'][config.SYMBOL])
