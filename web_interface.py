import os
import json
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_socketio import SocketIO
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired
import config
from utils import convert_timeframe
try:
    from health_check import HealthCheck
except ImportError:
    HealthCheck = None
try:
    from metrics import MetricsCollector
except ImportError:
    MetricsCollector = None
try:
    from failover import FailoverManager
except ImportError:
    FailoverManager = None
trading_bot = None
socketio = None
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password
    def check_password(self, password):
        return self.password == password
class WebInterface:
    def __init__(self, bot=None, logger=None):
        global trading_bot, socketio
        self.bot = bot
        self.logger = logger
        trading_bot = bot
        self.health_check = HealthCheck(logger=logger, check_interval=60) if HealthCheck else None
        self.metrics_collector = MetricsCollector(bot=bot, logger=logger) if MetricsCollector else None
        self.failover_manager = FailoverManager(bot=bot, logger=logger) if FailoverManager else None
        if self.health_check:
            self.health_check.start()
            if self.logger:
                self.logger.info("Health check module started")
        if self.metrics_collector:
            self.metrics_collector.start()
            if self.logger:
                self.logger.info("Metrics collector started")
        if self.failover_manager:
            self.failover_manager.start()
            if self.logger:
                self.logger.info("Failover manager started")
        self.app = Flask(__name__,
                         template_folder='templates',
                         static_folder='static')
        self.app.config['SECRET_KEY'] = config.WEB_SECRET_KEY
        self.app.config['WTF_CSRF_ENABLED'] = True
        @self.app.context_processor
        def inject_now():
            return {'now': datetime.now()}
        socketio = SocketIO(self.app)
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = 'login'
        self.users = {
            config.WEB_USERNAME: User(1, config.WEB_USERNAME, config.WEB_PASSWORD)
        }
        self._register_routes()
        self._register_socketio_events()
        if self.logger:
            self.logger.info("Web Interface initialized")
    def _register_routes(self):
        @self.app.route('/')
        @login_required
        def index():
            return render_template('index.html',
                                  bot=self.bot,
                                  config=config)
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if current_user.is_authenticated:
                return redirect(url_for('main.index'))
            form = LoginForm()
            if form.validate_on_submit():
                user = self.users.get(form.username.data)
                if user is None or not user.check_password(form.password.data):
                    flash('Invalid username or password', 'danger')
                    return redirect(url_for('auth.login'))
                login_user(user, remember=form.remember_me.data)
                return redirect(url_for('main.index'))
            return render_template('login.html', form=form)
        @self.app.route('/logout')
        def logout():
            logout_user()
            return redirect(url_for('auth.login'))
        @self.app.route('/settings')
        @login_required
        def settings():
            return render_template('settings.html',
                                  bot=self.bot,
                                  config=config)
        @self.app.route('/trades')
        @login_required
        def trades():
            return render_template('trades.html',
                                  bot=self.bot,
                                  config=config)
        @self.app.route('/health')
        @login_required
        def health():
            return render_template('health.html',
                                  bot=self.bot,
                                  config=config)
        @self.app.route('/metrics')
        @login_required
        def metrics():
            return render_template('metrics.html',
                                  bot=self.bot,
                                  config=config)
        @self.app.route('/failover')
        @login_required
        def failover():
            return render_template('failover.html',
                                  bot=self.bot,
                                  config=config)
        @self.app.route('/api/status')
        @login_required
        def api_status():
            if self.bot is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not initialized'
                })
            human_timeframe = convert_timeframe(self.bot.timeframe, from_format='bybit_v5', to_format='human')
            return jsonify({
                'status': 'OK',
                'running': self.bot.running,
                'symbol': self.bot.symbol,
                'timeframe': self.bot.timeframe,
                'timeframe_display': human_timeframe,
                'dry_run': self.bot.dry_run,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        @self.app.route('/api/start', methods=['POST'])
        @login_required
        def api_start():
            if self.bot is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not initialized'
                })
            if not self.bot.running:
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
            if self.bot is None or self.bot.bybit_client is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot or API client not initialized'
                })
            balance = self.bot.bybit_client.get_wallet_balance()
            if balance is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failed to get balance'
                })
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
            if self.bot is None or self.bot.bybit_client is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot or API client not initialized'
                })
            positions = self.bot.bybit_client.get_positions(self.bot.symbol)
            if positions is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failed to get positions'
                })
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
            if self.bot is None or self.bot.order_manager is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot or order manager not initialized'
                })
            symbol = request.json.get('symbol', self.bot.symbol) if request.json else self.bot.symbol
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
            if self.bot is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not initialized'
                })
            data = request.json
            if 'symbol' in data:
                self.bot.symbol = data['symbol']
            if 'timeframe' in data:
                self.bot.timeframe = data['timeframe']
            if 'dry_run' in data:
                self.bot.dry_run = data['dry_run']
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
            if self.bot.risk_manager is not None:
                if 'risk_per_trade' in data:
                    self.bot.risk_manager.risk_per_trade = float(data['risk_per_trade'])
                if 'risk_reward_ratio' in data:
                    self.bot.risk_manager.risk_reward_ratio = float(data['risk_reward_ratio'])
            if self.logger:
                self.logger.info(f"Settings updated via web interface: {data}")
            # Optionally, add logic here to persist settings if needed
            # e.g., self.bot.save_settings()
            return jsonify({
                'status': 'OK',
                'message': 'Settings updated successfully'
            })
        # Add error handling for potential exceptions during settings update
        @self.app.errorhandler(Exception)
        def handle_exception(e):
            if self.logger:
                self.logger.error(f"An error occurred: {e}", exc_info=True)
            # You might want to return a more user-friendly error page or JSON response
            return jsonify({'status': 'ERROR', 'message': 'An internal error occurred'}), 500
        @self.app.route('/api/trade_history')
        @login_required
        def api_trade_history():
            if self.bot is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not initialized'
                })
            trade_history = getattr(self.bot, 'trade_history', [])
            total_trades = len(trade_history)
            winning_trades = sum(1 for trade in trade_history if trade.get('pnl', 0) > 0)
            losing_trades = sum(1 for trade in trade_history if trade.get('pnl', 0) < 0)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            total_profit = sum(trade.get('pnl', 0) for trade in trade_history if trade.get('pnl', 0) > 0)
            total_loss = sum(abs(trade.get('pnl', 0)) for trade in trade_history if trade.get('pnl', 0) < 0)
            profit_factor = total_profit / total_loss if total_loss > 0 else 0
            total_pnl = sum(trade.get('pnl', 0) for trade in trade_history)
            equity_curve = []
            equity = 10000
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
            if self.bot is None or self.bot.bybit_client is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot or API client not initialized'
                })
            symbol = request.args.get('symbol', self.bot.symbol)
            interval = request.args.get('interval', self.bot.timeframe)
            limit = int(request.args.get('limit', 100))
            if self.bot.use_websocket:
                klines = self.bot.bybit_client.get_realtime_kline(symbol=symbol, interval=interval)
            else:
                klines = self.bot.bybit_client.get_klines(symbol=symbol, interval=interval, limit=limit)
            if klines is None or klines.empty:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failed to get market data'
                })
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
            ticker = self.bot.bybit_client.get_ticker(symbol=symbol)
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
            if self.bot is None or self.bot.strategy is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot or strategy not initialized'
                })
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
                'atr_period': strategy.atr_period
            }
            return jsonify({
                'status': 'OK',
                'parameters': parameters
            })
        @self.app.route('/api/export_data', methods=['POST'])
        @login_required
        def api_export_data():
            if self.bot is None:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Bot not initialized'
                })
            data_type = request.json.get('type', 'trades')
            if data_type == 'trades':
                trade_history = getattr(self.bot, 'trade_history', [])
                return jsonify({
                    'status': 'OK',
                    'data': trade_history,
                    'filename': f'trade_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                })
            elif data_type == 'settings':
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
        @self.app.route('/api/health')
        @login_required
        def api_health():
            if not self.health_check:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Health check module not initialized'
                })
            health_data = self.health_check.get_health_data()
            health_history = []
            return jsonify({
                'status': 'OK',
                'health': health_data,
                'history': health_history
            })
        @self.app.route('/api/health/export')
        @login_required
        def api_health_export():
            if not self.health_check:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Health check module not initialized'
                })
            file_path = self.health_check.export_health_data()
            if not file_path or not os.path.exists(file_path):
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failed to export health data'
                })
            return send_file(file_path, as_attachment=True)
        @self.app.route('/api/metrics')
        @login_required
        def api_metrics():
            if not self.metrics_collector:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Metrics collector not initialized'
                })
            time_range = request.args.get('range', '1h')
            metrics = self.metrics_collector.get_metrics()
            system_history = {
                'timestamps': [],
                'cpu_usage': [],
                'memory_usage': [],
                'disk_usage': []
            }
            api_history = {
                'timestamps': [],
                'latency': [],
                'calls': []
            }
            trading_history = {
                'timestamps': [],
                'profit_loss': [],
                'win_rate': []
            }
            performance_history = {
                'timestamps': [],
                'loop_time': [],
                'strategy_time': []
            }
            return jsonify({
                'status': 'OK',
                'metrics': metrics,
                'system_history': system_history,
                'api_history': api_history,
                'trading_history': trading_history,
                'performance_history': performance_history
            })
        @self.app.route('/api/metrics/export')
        @login_required
        def api_metrics_export():
            if not self.metrics_collector:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Metrics collector not initialized'
                })
            export_format = request.args.get('format', 'json')
            file_path = self.metrics_collector.export_metrics(format=export_format)
            if not file_path or not os.path.exists(file_path):
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failed to export metrics data'
                })
            return send_file(file_path, as_attachment=True)
        @self.app.route('/api/failover/status')
        @login_required
        def api_failover_status():
            if not self.failover_manager:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failover manager not initialized'
                })
            failover_status = self.failover_manager.get_failover_status()
            recovery_history = []
            return jsonify({
                'status': 'OK',
                'failover': failover_status,
                'history': recovery_history
            })
        @self.app.route('/api/failover/config', methods=['POST'])
        @login_required
        def api_failover_config():
            if not self.failover_manager:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failover manager not initialized'
                })
            config_data = request.json
            success = self.failover_manager.update_failover_config(config_data)
            if not success:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failed to update failover configuration'
                })
            return jsonify({
                'status': 'OK',
                'message': 'Failover configuration updated successfully'
            })
        @self.app.route('/api/failover/reset_component', methods=['POST'])
        @login_required
        def api_failover_reset_component():
            if not self.failover_manager:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failover manager not initialized'
                })
            component = request.json.get('component')
            if not component:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Component not specified'
                })
            success = self.failover_manager.reset_component(component)
            if not success:
                return jsonify({
                    'status': 'ERROR',
                    'message': f'Failed to reset component: {component}'
                })
            return jsonify({
                'status': 'OK',
                'message': f'Component {component} reset successfully'
            })
        @self.app.route('/api/failover/emergency_shutdown', methods=['POST'])
        @login_required
        def api_failover_emergency_shutdown():
            if not self.failover_manager:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failover manager not initialized'
                })
            if not self.failover_manager.failover_config.get('emergency_shutdown', False):
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Emergency shutdown is disabled'
                })
            if self.bot and hasattr(self.bot, 'shutdown'):
                self.bot.shutdown()
                if self.logger:
                    self.logger.critical("Emergency shutdown initiated via web interface")
                return jsonify({
                    'status': 'OK',
                    'message': 'Emergency shutdown initiated'
                })
            else:
                return jsonify({
                    'status': 'ERROR',
                    'message': 'Failed to perform emergency shutdown'
                })
        @self.login_manager.user_loader
        def load_user(user_id):
            for user in self.users.values():
                if user.id == int(user_id):
                    return user
            return None
    def _register_socketio_events(self):
        @socketio.on('connect')
        def handle_connect():
            if self.logger:
                self.logger.debug("Client connected to SocketIO")
        @socketio.on('disconnect')
        def handle_disconnect():
            if self.logger:
                self.logger.debug("Client disconnected from SocketIO")
    def run(self, host=None, port=None, debug=None):
        host = host or config.WEB_HOST
        port = port or config.WEB_PORT
        debug = debug if debug is not None else config.WEB_DEBUG
        if self.logger:
            self.logger.info(f"Starting Web Interface on {host}:{port}")
        # Python 3.11 has improved error handling for socket operations
        try:
            socketio.run(self.app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
        except OSError as e:
            error_message = f"Failed to start web interface on {host}:{port}. Error: {e}"
            if self.logger:
                self.logger.error(error_message, exc_info=True) # Add traceback
            print(f"Error: {error_message}")
            if "address already in use" in str(e).lower():
                print("Hint: The port might already be in use by another application.")
            elif "permission denied" in str(e).lower():
                print("Hint: You might not have the necessary permissions to bind to this port/address.")
            else:
                print("Hint: Check network configuration and firewall settings.")
            # Consider exiting or raising the exception depending on desired behavior
            # sys.exit(1) # Uncomment to exit if the server fails to start
        except Exception as e:
            # Catch other potential exceptions during startup
            error_message = f"An unexpected error occurred while starting the web interface: {e}"
            if self.logger:
                self.logger.error(error_message, exc_info=True)
            print(f"Error: {error_message}")
def emit_log(message, level="info"):
    if socketio:
        socketio.emit('log', {
            'message': message,
            'level': level,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
def emit_trade(trade_data):
    if socketio:
        socketio.emit('trade', trade_data)
        if hasattr(trading_bot, 'trade_history'):
            trading_bot.trade_history.append(trade_data)
        else:
            trading_bot.trade_history = [trade_data]
def emit_status_update(status_data):
    if socketio:
        socketio.emit('status_update', status_data)
