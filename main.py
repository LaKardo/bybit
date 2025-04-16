import time
import signal
import sys
import os
import threading
from datetime import datetime

# --- Start: Add pandas_ta fix ---
import site

def apply_pandas_ta_fix():
    """Applies a compatibility fix for pandas_ta and numpy."""
    try:
        # Try standard site-packages path first
        file_path = os.path.join(sys.prefix, 'Lib', 'site-packages', 'pandas_ta', 'momentum', 'squeeze_pro.py')
        if not os.path.exists(file_path):
            # Fallback to user site-packages
            user_site = site.getusersitepackages()
            if user_site:
                file_path = os.path.join(user_site, 'pandas_ta', 'momentum', 'squeeze_pro.py')
            else:
                print("Could not determine user site-packages directory.")
                return # Exit if user site cannot be found

        if os.path.exists(file_path):
            print(f"Checking pandas_ta fix for: {file_path}")
            with open(file_path, 'r') as f:
                content = f.read()
            if 'from numpy import NaN as npNaN' in content:
                print("Applying pandas_ta compatibility fix...")
                content = content.replace('from numpy import NaN as npNaN', 'from numpy import nan as npNaN')
                with open(file_path, 'w') as f:
                    f.write(content)
                print("Fixed pandas_ta compatibility issue with numpy.")
            else:
                print("pandas_ta fix not needed or already applied.")
        else:
            print(f"Could not find pandas_ta file to patch at expected locations: {file_path}")
            print("Please ensure pandas_ta is installed correctly.")
    except Exception as e:
        print(f"Error applying pandas_ta fix: {e}")

apply_pandas_ta_fix() # Apply the fix on startup
# --- End: Add pandas_ta fix ---

import config
from check_python_version import check_python_version
from logger import Logger
from notifier import TelegramNotifier
from bybit_client import BybitAPIClient
from strategy import Strategy
from risk_manager import RiskManager
from order_manager import OrderManager
from health_check import HealthCheck
from web_app.bot_integration import set_bot_instance, emit_log, emit_status_update, emit_trade, emit_health_update
class TradingBot:
    def __init__(self):
        LOGS_DIR = 'logs'
        os.makedirs(LOGS_DIR, exist_ok=True)
        self.logger = Logger(log_file=os.path.join(LOGS_DIR, "trading_bot.log"), log_level=config.LOG_LEVEL)
        self.logger.info("Initializing Trading Bot...")
        self.notifier = TelegramNotifier(logger=self.logger)
        self.bybit_client = BybitAPIClient(logger=self.logger)
        account_info = self.bybit_client.get_account_info()
        if account_info:
            self.logger.info(f"Account type: {account_info.get('unifiedMarginStatus')}")
            self.logger.info(f"Account mode: {account_info.get('marginMode')}")
            self.logger.info(f"Account status: {account_info.get('accountStatus')}")
        self.logger.info("ВНИМАНИЕ: Бот настроен на работу с РЕАЛЬНЫМ СЧЕТОМ Bybit")
        self.strategy = Strategy(logger=self.logger)
        self.risk_manager = RiskManager(logger=self.logger)
        self.order_manager = OrderManager(
            bybit_client=self.bybit_client,
            risk_manager=self.risk_manager,
            logger=self.logger,
            notifier=self.notifier
        )
        self.symbol = config.SYMBOL
        self.timeframe = config.TIMEFRAME
        self.check_interval = config.CHECK_INTERVAL
        self.dry_run = config.DRY_RUN
        self.use_websocket = config.USE_WEBSOCKET
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        self.running = False
        self.health_check = HealthCheck(logger=self.logger, check_interval=60)
        self.health_check.start()
        self.logger.info("Health check system started")
        # Register bot instance with web interface
        if config.WEB_INTERFACE_ENABLED:
            set_bot_instance(self)
            self.logger.info("Bot instance registered with web interface")
        if self.use_websocket:
            self.logger.info("Starting WebSocket connection...")
            if self.bybit_client.start_websocket():
                self.logger.info("WebSocket connection started successfully")
                self.health_check.update_component_status("websocket", "ok")
                self.bybit_client.subscribe_kline(symbol=self.symbol, interval=self.timeframe)
            else:
                self.logger.error("Failed to start WebSocket connection")
                self.health_check.update_component_status("websocket", "error")
                self.use_websocket = False
        self.logger.info(f"Trading Bot initialized for {self.symbol} on {self.timeframe} timeframe")
        self.health_check.update_component_status("api_client", "ok")
        self.health_check.update_component_status("strategy", "ok")
        self.health_check.update_component_status("risk_manager", "ok")
        self.health_check.update_component_status("order_manager", "ok")
        if config.WEB_INTERFACE_ENABLED:
            self.health_check.update_component_status("web_interface", "ok")
        if self.dry_run:
            self.logger.info("Режим торговли: РЕАЛЬНЫЙ СЧЕТ с симуляцией сделок (DRY RUN)")
        else:
            self.logger.info("Режим торговли: РЕАЛЬНЫЙ СЧЕТ с реальным исполнением сделок")
        if self.notifier:
            mode = "DRY RUN" if self.dry_run else "РЕАЛЬНЫЙ СЧЕТ (реальная торговля)"
            self.notifier.notify_bot_status(
                status="STARTED",
                additional_info=f"Trading {self.symbol} on {self.timeframe} timeframe\nMode: {mode}"
            )
        emit_status_update({
            'running': self.running,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'dry_run': self.dry_run,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    def run(self):
        self.running = True
        self.logger.info("Starting main trading loop...")
        emit_status_update({
            'running': self.running,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'dry_run': self.dry_run,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        emit_log("Starting main trading loop...", "info")
        while self.running:
            try:
                start_time = time.time()
                try:
                    if self.use_websocket:
                        main_klines = self.bybit_client.get_realtime_kline(
                            symbol=self.symbol,
                            interval=self.timeframe
                        )
                    else:
                        main_klines = self.bybit_client.get_klines(
                            symbol=self.symbol,
                            interval=self.timeframe,
                            limit=100
                        )
                    response_time = (time.time() - start_time) * 1000
                    self.health_check.update_api_metrics(success=True, response_time=response_time)
                except Exception as e:
                    self.logger.error(f"Error getting klines data: {e}")
                    response_time = (time.time() - start_time) * 1000
                    self.health_check.update_api_metrics(success=False, response_time=response_time)
                    time.sleep(self.check_interval)
                    continue
                if main_klines is None or main_klines.empty:
                    self.logger.error("Failed to get historical data for main timeframe, retrying...")
                    time.sleep(self.check_interval)
                    continue
                try:
                    main_data = self.strategy.calculate_indicators(main_klines)
                    if main_data is None:
                        self.logger.error("Failed to calculate indicators for main timeframe, retrying...")
                        self.health_check.update_component_status("strategy", "warning")
                        time.sleep(self.check_interval)
                        continue
                    self.health_check.update_component_status("strategy", "ok")
                except Exception as e:
                    self.logger.error(f"Error calculating indicators: {e}")
                    self.health_check.update_component_status("strategy", "error")
                    time.sleep(self.check_interval)
                    continue
                self.order_manager.check_and_exit_on_signal(main_data)
                signal = self.strategy.generate_signal(main_data)
                if signal != "NONE":
                    indicators = {
                        f"EMA{config.FAST_EMA}": round(main_data.iloc[-1][f'ema_{config.FAST_EMA}'], 2),
                        f"EMA{config.SLOW_EMA}": round(main_data.iloc[-1][f'ema_{config.SLOW_EMA}'], 2),
                        "RSI": round(main_data.iloc[-1]['rsi'], 2),
                        "MACD": round(main_data.iloc[-1]['macd'], 4),
                        "MACD Signal": round(main_data.iloc[-1]['macd_signal'], 4),
                        "MACD Hist": round(main_data.iloc[-1]['macd_hist'], 4),
                        "ATR": round(main_data.iloc[-1]['atr'], 2)
                    }
                    self.logger.signal(
                        symbol=self.symbol,
                        timeframe=self.timeframe,
                        signal_type=signal,
                        indicators=indicators
                    )
                if signal in ["LONG", "SHORT"]:
                    try:
                        result = self.order_manager.enter_position(signal, main_data)
                        if result:
                            self.health_check.update_trading_metrics({
                                "trades_total": self.health_check.trading_metrics["trades_total"] + 1,
                                "trades_successful": self.health_check.trading_metrics["trades_successful"] + 1
                            })
                        else:
                            self.health_check.update_trading_metrics({
                                "trades_total": self.health_check.trading_metrics["trades_total"] + 1,
                                "trades_failed": self.health_check.trading_metrics["trades_failed"] + 1
                            })
                    except Exception as e:
                        self.logger.error(f"Error entering position: {e}")
                        self.health_check.update_component_status("order_manager", "error")
                        self.health_check.update_trading_metrics({
                            "trades_total": self.health_check.trading_metrics["trades_total"] + 1,
                            "trades_failed": self.health_check.trading_metrics["trades_failed"] + 1
                        })
                start_time = time.time()
                try:
                    balance_info = self.bybit_client.get_wallet_balance()
                    response_time = (time.time() - start_time) * 1000
                    self.health_check.update_api_metrics(success=True, response_time=response_time)
                except Exception as e:
                    self.logger.error(f"Error getting wallet balance: {e}")
                    response_time = (time.time() - start_time) * 1000
                    self.health_check.update_api_metrics(success=False, response_time=response_time)
                    balance_info = None
                if balance_info:
                    self.logger.balance(
                        available_balance=balance_info["available_balance"],
                        wallet_balance=balance_info["wallet_balance"],
                        unrealized_pnl=balance_info["unrealized_pnl"]
                    )
                start_time = time.time()
                try:
                    positions = self.bybit_client.get_positions(self.symbol)
                    response_time = (time.time() - start_time) * 1000
                    self.health_check.update_api_metrics(success=True, response_time=response_time)
                except Exception as e:
                    self.logger.error(f"Error getting positions: {e}")
                    response_time = (time.time() - start_time) * 1000
                    self.health_check.update_api_metrics(success=False, response_time=response_time)
                    positions = []
                if positions:
                    for position in positions:
                        size = float(position.get("size", 0))
                        if size > 0:
                            self.logger.position(
                                symbol=position.get("symbol"),
                                side=position.get("side"),
                                size=size,
                                entry_price=float(position.get("entryPrice", 0)),
                                liq_price=float(position.get("liqPrice", 0)),
                                unrealized_pnl=float(position.get("unrealisedPnl", 0))
                            )
                self.logger.debug(f"Waiting {self.check_interval} seconds until next check...")
                time.sleep(self.check_interval)
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                self.logger.error(f"Error in main loop: {e}")
                self.logger.error(f"Detailed error: {error_details}")
                self.health_check.update_component_status("api_client", "error")
                if self.notifier:
                    self.notifier.notify_error(f"Error in main loop: {e}")
                emit_log(f"Error in main loop: {e}", "error")
                self.logger.info(f"Waiting {self.check_interval} seconds before retrying...")
                time.sleep(self.check_interval)
    def shutdown(self, signum=None, _=None):
        self.logger.info("Shutting down Trading Bot...")
        self.running = False
        emit_status_update({
            'running': self.running,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'dry_run': self.dry_run,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        emit_log("Shutting down Trading Bot...", "info")
        if self.use_websocket:
            self.logger.info("Stopping WebSocket...")
            self.bybit_client.stop_websocket()
            self.health_check.update_component_status("websocket", "unknown")
            emit_log("WebSocket stopped", "info")
        if config.CLOSE_POSITIONS_ON_SHUTDOWN:
            self.logger.info("Closing all positions...")
            self.order_manager.exit_position(reason="SHUTDOWN")
            emit_log("Closing all positions...", "info")
        self.logger.info("Stopping health check system...")
        self.health_check.stop()
        emit_log("Health check system stopped", "info")
        if self.notifier:
            self.notifier.notify_bot_status(status="STOPPED")
        self.logger.info("Trading Bot stopped")
        emit_log("Trading Bot stopped", "info")
        if signum is not None:
            sys.exit(0)
if __name__ == "__main__":
    # Check Python version before starting the bot
    # This ensures we're running on Python 3.11 or higher
    check_python_version()

    bot = TradingBot()
    if config.WEB_INTERFACE_ENABLED:
        # Import here to avoid circular imports
        from run_web_app import run_web_app_in_thread
        web_thread = run_web_app_in_thread(
            host=config.WEB_HOST,
            port=config.WEB_PORT,
            debug=config.WEB_DEBUG
        )
        print(f"Web interface started on http://{config.WEB_HOST}:{config.WEB_PORT}")
    bot.run()
