"""
Web Interface module for the Bybit Trading Bot.
Provides a web dashboard for monitoring and controlling the bot.
"""

import os
import json
import threading
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_socketio import SocketIO
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired
import config
from utils import convert_timeframe

# Global variables
trading_bot = None
socketio = None

class LoginForm(FlaskForm):
    """Login form for web interface."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class User(UserMixin):
    """User class for authentication."""
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def check_password(self, password):
        """Check if password is correct."""
        return self.password == password

class WebInterface:
    """
    Web Interface class for the Bybit Trading Bot.
    Provides a web dashboard for monitoring and controlling the bot.
    """
    def __init__(self, bot=None, logger=None):
        """
        Initialize the web interface.

        Args:
            bot (TradingBot, optional): Trading bot instance.
            logger (Logger, optional): Logger instance.
        """
        global trading_bot, socketio

        self.bot = bot
        self.logger = logger
        trading_bot = bot

        # Initialize Flask app
        self.app = Flask(__name__,
                         template_folder='templates',
                         static_folder='static')
        self.app.config['SECRET_KEY'] = config.WEB_SECRET_KEY
        self.app.config['WTF_CSRF_ENABLED'] = True

        # Add template context processor
        @self.app.context_processor
        def inject_now():
            return {'now': datetime.now()}

        # Initialize SocketIO
        socketio = SocketIO(self.app)

        # Initialize login manager
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = 'login'

        # Create user
        self.users = {
            config.WEB_USERNAME: User(1, config.WEB_USERNAME, config.WEB_PASSWORD)
        }

        # Register routes
        self._register_routes()

        # Register SocketIO events
        self._register_socketio_events()

        if self.logger:
            self.logger.info("Web Interface initialized")

    def _register_routes(self):
        """Register Flask routes."""
        @self.app.route('/')
        @login_required
        def index():
            """Render dashboard page."""
            return render_template('index.html',
                                  bot=self.bot,
                                  config=config)

        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            """Handle login."""
            if current_user.is_authenticated:
                return redirect(url_for('index'))

            form = LoginForm()
            if form.validate_on_submit():
                user = self.users.get(form.username.data)
                if user is None or not user.check_password(form.password.data):
                    flash('Invalid username or password', 'danger')
                    return redirect(url_for('login'))

                login_user(user, remember=form.remember_me.data)
                return redirect(url_for('index'))

            return render_template('login.html', form=form)

        @self.app.route('/logout')
        def logout():
            """Handle logout."""
            logout_user()
            return redirect(url_for('login'))

        @self.app.route('/settings')
        @login_required
        def settings():
            """Render settings page."""
            return render_template('settings.html',
                                  bot=self.bot,
                                  config=config)

        @self.app.route('/trades')
        @login_required
        def trades():
            """Render trades page."""
            return render_template('trades.html',
                                  bot=self.bot,
                                  config=config)

        @self.app.route('/api/status')
        @login_required
        def api_status():
            """API endpoint for bot status."""
            if self.bot is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not initialized'
                })

            # Convert timeframe to human-readable format for display
            human_timeframe = convert_timeframe(self.bot.timeframe, from_format='bybit_v5', to_format='human')

            return jsonify({
                'status': 'OK',
                'running': self.bot.running,
                'symbol': self.bot.symbol,
                'timeframe': self.bot.timeframe,
                'timeframe_display': human_timeframe,  # Human-readable timeframe for display
                'dry_run': self.bot.dry_run,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        @self.app.route('/api/start', methods=['POST'])
        @login_required
        def api_start():
            """API endpoint to start the bot."""
            if self.bot is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not initialized'
                })

            if not self.bot.running:
                # Start the bot in a new thread
                threading.Thread(target=self.bot.run).start()

                if self.logger:
                    self.logger.info("Bot started via web interface")

                return jsonify({
                    'status': 'OK',
                    'message': 'Bot started'
                })
            else:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot already running'
                })

        @self.app.route('/api/stop', methods=['POST'])
        @login_required
        def api_stop():
            """API endpoint to stop the bot."""
            if self.bot is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not initialized'
                })

            if self.bot.running:
                self.bot.shutdown()

                if self.logger:
                    self.logger.info("Bot stopped via web interface")

                return jsonify({
                    'status': 'OK',
                    'message': 'Bot stopped'
                })
            else:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not running'
                })

        @self.app.route('/api/balance')
        @login_required
        def api_balance():
            """API endpoint for account balance."""
            if self.bot is None or self.bot.bybit_client is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot or API client not initialized'
                })

            # Get wallet balance using V5 API
            balance = self.bot.bybit_client.get_wallet_balance()

            if balance is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failed to get balance'
                })

            # Format balance data for API V5
            formatted_balance = {
                'available_balance': balance.get('available_balance', 0),
                'wallet_balance': balance.get('wallet_balance', 0),
                'unrealized_pnl': balance.get('unrealized_pnl', 0),
                'equity': balance.get('equity', 0),
                'used_margin': balance.get('used_margin', 0),
                'used_margin_rate': balance.get('used_margin_rate', 0),
                'margin_ratio': balance.get('margin_ratio', 0),
                'free_margin': balance.get('free_margin', 0),
                'coin': balance.get('coin', 'USDT')
            }

            return jsonify({
                'status': 'OK',
                'balance': formatted_balance
            })

        @self.app.route('/api/positions')
        @login_required
        def api_positions():
            """API endpoint for open positions."""
            if self.bot is None or self.bot.bybit_client is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot or API client not initialized'
                })

            # Get positions using V5 API
            positions = self.bot.bybit_client.get_positions(self.bot.symbol)

            if positions is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failed to get positions'
                })

            # Format positions data for API V5
            formatted_positions = []
            for pos in positions:
                formatted_pos = {
                    'symbol': pos.get('symbol', ''),
                    'side': pos.get('side', ''),
                    'size': pos.get('size', 0),
                    'position_value': pos.get('position_value', 0),
                    'entry_price': pos.get('entry_price', 0),
                    'mark_price': pos.get('mark_price', 0),
                    'unrealized_pnl': pos.get('unrealized_pnl', 0),
                    'leverage': pos.get('leverage', 0),
                    'liq_price': pos.get('liq_price', 0),
                    'take_profit': pos.get('take_profit', 0),
                    'stop_loss': pos.get('stop_loss', 0),
                    'trailing_stop': pos.get('trailing_stop', 0),
                    'created_time': pos.get('created_time', ''),
                    'updated_time': pos.get('updated_time', '')
                }
                formatted_positions.append(formatted_pos)

            return jsonify({
                'status': 'OK',
                'positions': formatted_positions
            })

        @self.app.route('/api/close_position', methods=['POST'])
        @login_required
        def api_close_position():
            """API endpoint to close a position."""
            if self.bot is None or self.bot.order_manager is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot or order manager not initialized'
                })

            # Get symbol from request or use bot's symbol
            symbol = request.json.get('symbol', self.bot.symbol) if request.json else self.bot.symbol

            # Close position using V5 API
            result = self.bot.order_manager.exit_position(symbol=symbol, reason="MANUAL_WEB")

            if result:
                if self.logger:
                    self.logger.info(f"Position for {symbol} closed via web interface")

                return jsonify({
                    'status': 'OK',
                    'message': f'Position for {symbol} closed'
                })
            else:
                return jsonify({
                    'status': 'ERROR',
                    'message': f'Failed to close position for {symbol}'
                })

        @self.app.route('/api/update_settings', methods=['POST'])
        @login_required
        def api_update_settings():
            """API endpoint to update settings."""
            if self.bot is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not initialized'
                })

            # Get settings from request
            data = request.json

            # Update settings
            # Note: This is a simplified example. In a real implementation,
            # you would need to validate the settings and handle more complex updates.
            if 'symbol' in data:
                self.bot.symbol = data['symbol']

            if 'timeframe' in data:
                self.bot.timeframe = data['timeframe']

            if 'dry_run' in data:
                self.bot.dry_run = data['dry_run']

            # Update strategy parameters if strategy is initialized
            if self.bot.strategy is not None:
                if 'fast_ema' in data:
                    self.bot.strategy.fast_ema = int(data['fast_ema'])

                if 'slow_ema' in data:
                    self.bot.strategy.slow_ema = int(data['slow_ema'])

                if 'rsi_period' in data:
                    self.bot.strategy.rsi_period = int(data['rsi_period'])

                if 'rsi_overbought' in data:
                    self.bot.strategy.rsi_overbought = int(data['rsi_overbought'])

                if 'rsi_oversold' in data:
                    self.bot.strategy.rsi_oversold = int(data['rsi_oversold'])

                if 'multi_timeframe_enabled' in data:
                    self.bot.strategy.multi_timeframe_enabled = bool(data['multi_timeframe_enabled'])

                if 'confirmation_timeframes' in data and isinstance(data['confirmation_timeframes'], list):
                    self.bot.strategy.confirmation_timeframes = data['confirmation_timeframes']

            # Update risk management parameters if risk manager is initialized
            if self.bot.risk_manager is not None:
                if 'risk_per_trade' in data:
                    self.bot.risk_manager.risk_per_trade = float(data['risk_per_trade'])

                if 'risk_reward_ratio' in data:
                    self.bot.risk_manager.risk_reward_ratio = float(data['risk_reward_ratio'])

            if self.logger:
                self.logger.info(f"Settings updated via web interface: {data}")

            return jsonify({
                'status': 'OK',
                'message': 'Settings updated'
            })

        @self.app.route('/api/trade_history')
        @login_required
        def api_trade_history():
            """API endpoint for trade history."""
            if self.bot is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not initialized'
                })

            # Get trade history from bot
            trade_history = getattr(self.bot, 'trade_history', [])

            # Calculate performance metrics
            total_trades = len(trade_history)
            winning_trades = sum(1 for trade in trade_history if trade.get('pnl', 0) > 0)
            losing_trades = sum(1 for trade in trade_history if trade.get('pnl', 0) < 0)

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            total_profit = sum(trade.get('pnl', 0) for trade in trade_history if trade.get('pnl', 0) > 0)
            total_loss = sum(abs(trade.get('pnl', 0)) for trade in trade_history if trade.get('pnl', 0) < 0)

            profit_factor = total_profit / total_loss if total_loss > 0 else 0
            total_pnl = sum(trade.get('pnl', 0) for trade in trade_history)

            # Create equity curve
            equity_curve = []
            equity = 10000  # Starting equity

            for trade in sorted(trade_history, key=lambda x: x.get('datetime', '')):
                equity += trade.get('pnl', 0)
                equity_curve.append({
                    'date': trade.get('datetime', '').split(' ')[0],
                    'equity': equity
                })

            return jsonify({
                'status': 'OK',
                'trade_history': trade_history,
                'performance': {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'total_pnl': total_pnl,
                    'equity_curve': equity_curve
                }
            })

        @self.app.route('/api/market_data')
        @login_required
        def api_market_data():
            """API endpoint for market data."""
            if self.bot is None or self.bot.bybit_client is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot or API client not initialized'
                })

            symbol = request.args.get('symbol', self.bot.symbol)
            interval = request.args.get('interval', self.bot.timeframe)
            limit = int(request.args.get('limit', 100))

            # Check if WebSocket is enabled and use real-time data if available
            if self.bot.use_websocket:
                klines = self.bot.bybit_client.get_realtime_kline(symbol=symbol, interval=interval)
            else:
                # Get market data from REST API
                klines = self.bot.bybit_client.get_klines(symbol=symbol, interval=interval, limit=limit)

            if klines is None or klines.empty:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failed to get market data'
                })

            # Convert to list of dictionaries
            market_data = []
            for _, row in klines.iterrows():
                market_data.append({
                    'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row['timestamp'], 'strftime') else str(row['timestamp']),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume']),
                    'turnover': float(row['turnover']) if 'turnover' in row else 0,
                    'confirm': bool(row['confirm']) if 'confirm' in row else True
                })

            # Get current ticker using V5 API
            ticker = self.bot.bybit_client.get_ticker(symbol=symbol)

            # Format ticker data for API V5
            formatted_ticker = {
                'symbol': ticker.get('symbol', symbol),
                'lastPrice': ticker.get('lastPrice', 0),
                'markPrice': ticker.get('markPrice', 0),
                'indexPrice': ticker.get('indexPrice', 0),
                'highPrice24h': ticker.get('highPrice24h', 0),
                'lowPrice24h': ticker.get('lowPrice24h', 0),
                'volume24h': ticker.get('volume24h', 0),
                'turnover24h': ticker.get('turnover24h', 0),
                'price24hPcnt': ticker.get('price24hPcnt', 0),
                'openInterest': ticker.get('openInterest', 0),
                'fundingRate': ticker.get('fundingRate', 0),
                'nextFundingTime': ticker.get('nextFundingTime', 0)
            }

            return jsonify({
                'status': 'OK',
                'market_data': market_data,
                'ticker': formatted_ticker
            })

        @self.app.route('/api/strategy_parameters')
        @login_required
        def api_strategy_parameters():
            """API endpoint for strategy parameters."""
            if self.bot is None or self.bot.strategy is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot or strategy not initialized'
                })

            # Get strategy parameters
            strategy = self.bot.strategy

            parameters = {
                'fast_ema': strategy.fast_ema,
                'slow_ema': strategy.slow_ema,
                'rsi_period': strategy.rsi_period,
                'rsi_overbought': strategy.rsi_overbought,
                'rsi_oversold': strategy.rsi_oversold,
                'macd_fast': strategy.macd_fast,
                'macd_slow': strategy.macd_slow,
                'macd_signal': strategy.macd_signal,
                'volume_ma_period': strategy.volume_ma_period,
                'volume_threshold': strategy.volume_threshold,
                'atr_period': strategy.atr_period,
                'obv_smoothing': strategy.obv_smoothing,
                'multi_timeframe_enabled': strategy.multi_timeframe_enabled,
                'confirmation_timeframes': strategy.confirmation_timeframes,
                'mtf_alignment_required': strategy.mtf_alignment_required,

                'volume_required': strategy.volume_required
            }

            return jsonify({
                'status': 'OK',
                'parameters': parameters
            })

        @self.app.route('/api/export_data', methods=['POST'])
        @login_required
        def api_export_data():
            """API endpoint to export data."""
            if self.bot is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not initialized'
                })

            data_type = request.json.get('type', 'trades')

            if data_type == 'trades':
                # Export trade history
                trade_history = getattr(self.bot, 'trade_history', [])
                return jsonify({
                    'status': 'OK',
                    'data': trade_history,
                    'filename': f'trade_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                })
            elif data_type == 'settings':
                # Export settings
                settings = {
                    'symbol': self.bot.symbol,
                    'timeframe': self.bot.timeframe,
                    'dry_run': self.bot.dry_run,
                    'strategy_parameters': {}
                }

                if self.bot.strategy is not None:
                    strategy = self.bot.strategy
                    settings['strategy_parameters'] = {
                        'fast_ema': strategy.fast_ema,
                        'slow_ema': strategy.slow_ema,
                        'rsi_period': strategy.rsi_period,
                        'rsi_overbought': strategy.rsi_overbought,
                        'rsi_oversold': strategy.rsi_oversold,
                        'multi_timeframe_enabled': strategy.multi_timeframe_enabled,
                        'confirmation_timeframes': strategy.confirmation_timeframes,
                        'mtf_alignment_required': strategy.mtf_alignment_required
                    }

                return jsonify({
                    'status': 'OK',
                    'data': settings,
                    'filename': f'settings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                })
            else:
                return jsonify({
                    'status': 'ERROR',
                    'message': f'Unknown data type: {data_type}'
                })

        @self.login_manager.user_loader
        def load_user(user_id):
            """Load user by ID."""
            for user in self.users.values():
                if user.id == int(user_id):
                    return user
            return None

    def _register_socketio_events(self):
        """Register SocketIO events."""
        @socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            if self.logger:
                self.logger.debug("Client connected to SocketIO")

        @socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            if self.logger:
                self.logger.debug("Client disconnected from SocketIO")

    def run(self, host=None, port=None, debug=None):
        """
        Run the web interface.

        Args:
            host (str, optional): Host to run on. Defaults to config.WEB_HOST.
            port (int, optional): Port to run on. Defaults to config.WEB_PORT.
            debug (bool, optional): Enable debug mode. Defaults to config.WEB_DEBUG.
        """
        host = host or config.WEB_HOST
        port = port or config.WEB_PORT
        debug = debug if debug is not None else config.WEB_DEBUG

        if self.logger:
            self.logger.info(f"Starting Web Interface on {host}:{port}")

        socketio.run(self.app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)

def emit_log(message, level="info"):
    """
    Emit log message to connected clients.

    Args:
        message (str): Log message.
        level (str, optional): Log level. Defaults to "info".
    """
    if socketio:
        socketio.emit('log', {
            'message': message,
            'level': level,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

def emit_trade(trade_data):
    """
    Emit trade data to connected clients.

    Args:
        trade_data (dict): Trade data.
    """
    if socketio:
        socketio.emit('trade', trade_data)

        # Also store trade in trade history
        if hasattr(trading_bot, 'trade_history'):
            trading_bot.trade_history.append(trade_data)
        else:
            trading_bot.trade_history = [trade_data]

def emit_status_update(status_data):
    """
    Emit status update to connected clients.

    Args:
        status_data (dict): Status data.
    """
    if socketio:
        socketio.emit('status_update', status_data)
