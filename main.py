"""
Main module for the Bybit Trading Bot.
Coordinates all components and implements the main trading loop.
"""

import time
import signal
import sys
import os
import threading
from datetime import datetime

import config
from logger import Logger
from notifier import TelegramNotifier
from bybit_client import BybitAPIClient
from strategy import Strategy
from risk_manager import RiskManager
from order_manager import OrderManager
from health_check import HealthCheck

from web_interface import WebInterface, emit_log, emit_status_update

class TradingBot:
    """
    Main Trading Bot class.
    Coordinates all components and implements the main trading loop.
    """
    def __init__(self):
        """Initialize the Trading Bot."""
        # Create logs directory
        os.makedirs("logs", exist_ok=True)

        # Initialize logger
        self.logger = Logger(log_file="logs/trading_bot.log", log_level=config.LOG_LEVEL)
        self.logger.info("Initializing Trading Bot...")

        # Initialize notifier
        self.notifier = TelegramNotifier(logger=self.logger)

        # Initialize API client
        self.bybit_client = BybitAPIClient(logger=self.logger)

        # Get account information
        account_info = self.bybit_client.get_account_info()
        if account_info:
            self.logger.info(f"Account type: {account_info.get('unifiedMarginStatus')}")
            self.logger.info(f"Account mode: {account_info.get('marginMode')}")
            self.logger.info(f"Account status: {account_info.get('accountStatus')}")

        # Log account type status
        self.logger.info("ВНИМАНИЕ: Бот настроен на работу с РЕАЛЬНЫМ СЧЕТОМ Bybit")

        # Initialize strategy
        self.strategy = Strategy(logger=self.logger)

        # Initialize risk manager
        self.risk_manager = RiskManager(logger=self.logger)

        # Initialize order manager
        self.order_manager = OrderManager(
            bybit_client=self.bybit_client,
            risk_manager=self.risk_manager,
            logger=self.logger,
            notifier=self.notifier
        )

        # Trading parameters
        self.symbol = config.SYMBOL
        self.timeframe = config.TIMEFRAME
        self.check_interval = config.CHECK_INTERVAL
        self.dry_run = config.DRY_RUN

        # Multi-timeframe analysis has been removed

        # WebSocket parameters
        self.use_websocket = config.USE_WEBSOCKET



        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        # Bot state
        self.running = False

        # Initialize health check system
        self.health_check = HealthCheck(logger=self.logger, check_interval=60)
        self.health_check.start()
        self.logger.info("Health check system started")

        # Initialize web interface if enabled
        self.web_interface = None
        if config.WEB_INTERFACE_ENABLED:
            self.web_interface = WebInterface(bot=self, logger=self.logger)
            self.logger.info("Web Interface initialized")

        # Initialize WebSocket if enabled
        if self.use_websocket:
            self.logger.info("Starting WebSocket connection...")
            if self.bybit_client.start_websocket():
                self.logger.info("WebSocket connection started successfully")
                self.health_check.update_component_status("websocket", "ok")

                # Subscribe to kline data for main timeframe
                self.bybit_client.subscribe_kline(symbol=self.symbol, interval=self.timeframe)
            else:
                self.logger.error("Failed to start WebSocket connection")
                self.health_check.update_component_status("websocket", "error")
                self.use_websocket = False

        self.logger.info(f"Trading Bot initialized for {self.symbol} on {self.timeframe} timeframe")

        # Update component status in health check
        self.health_check.update_component_status("api_client", "ok")
        self.health_check.update_component_status("strategy", "ok")
        self.health_check.update_component_status("risk_manager", "ok")
        self.health_check.update_component_status("order_manager", "ok")
        if config.WEB_INTERFACE_ENABLED:
            self.health_check.update_component_status("web_interface", "ok")

        # Log trading mode
        if self.dry_run:
            self.logger.info("Режим торговли: РЕАЛЬНЫЙ СЧЕТ с симуляцией сделок (DRY RUN)")
        else:
            self.logger.info("Режим торговли: РЕАЛЬНЫЙ СЧЕТ с реальным исполнением сделок")

        # Send startup notification
        if self.notifier:
            mode = "DRY RUN" if self.dry_run else "РЕАЛЬНЫЙ СЧЕТ (реальная торговля)"

            self.notifier.notify_bot_status(
                status="STARTED",
                additional_info=f"Trading {self.symbol} on {self.timeframe} timeframe\nMode: {mode}"
            )

        # Emit status update to web interface
        emit_status_update({
            'running': self.running,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'dry_run': self.dry_run,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    def run(self):
        """Run the main trading loop."""
        self.running = True
        self.logger.info("Starting main trading loop...")

        # Emit status update to web interface
        emit_status_update({
            'running': self.running,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'dry_run': self.dry_run,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        # Emit log message to web interface
        emit_log("Starting main trading loop...", "info")

        while self.running:
            try:
                # Get historical data for main timeframe (use WebSocket if enabled)
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
                    # Update API metrics in health check
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    self.health_check.update_api_metrics(success=True, response_time=response_time)
                except Exception as e:
                    self.logger.error(f"Error getting klines data: {e}")
                    # Update API metrics in health check
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    self.health_check.update_api_metrics(success=False, response_time=response_time)
                    time.sleep(self.check_interval)
                    continue

                if main_klines is None or main_klines.empty:
                    self.logger.error("Failed to get historical data for main timeframe, retrying...")
                    time.sleep(self.check_interval)
                    continue

                # Calculate indicators for main timeframe
                try:
                    main_data = self.strategy.calculate_indicators(main_klines)
                    if main_data is None:
                        self.logger.error("Failed to calculate indicators for main timeframe, retrying...")
                        self.health_check.update_component_status("strategy", "warning")
                        time.sleep(self.check_interval)
                        continue
                    # Update strategy status in health check
                    self.health_check.update_component_status("strategy", "ok")
                except Exception as e:
                    self.logger.error(f"Error calculating indicators: {e}")
                    self.health_check.update_component_status("strategy", "error")
                    time.sleep(self.check_interval)
                    continue

                # Check if we should exit current position based on opposite signal
                self.order_manager.check_and_exit_on_signal(main_data)

                # Generate trading signal
                signal = self.strategy.generate_signal(main_data)

                # Log signal
                if signal != "NONE":
                    # Prepare indicators dictionary
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

                # Execute trading signal
                if signal in ["LONG", "SHORT"]:
                    try:
                        result = self.order_manager.enter_position(signal, main_data)
                        # Update trading metrics in health check
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

                # Get and log balance
                start_time = time.time()
                try:
                    balance_info = self.bybit_client.get_wallet_balance()
                    # Update API metrics in health check
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    self.health_check.update_api_metrics(success=True, response_time=response_time)
                except Exception as e:
                    self.logger.error(f"Error getting wallet balance: {e}")
                    # Update API metrics in health check
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    self.health_check.update_api_metrics(success=False, response_time=response_time)
                    balance_info = None

                if balance_info:
                    self.logger.balance(
                        available_balance=balance_info["available_balance"],
                        wallet_balance=balance_info["wallet_balance"],
                        unrealized_pnl=balance_info["unrealized_pnl"]
                    )

                # Get and log positions
                start_time = time.time()
                try:
                    positions = self.bybit_client.get_positions(self.symbol)
                    # Update API metrics in health check
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    self.health_check.update_api_metrics(success=True, response_time=response_time)
                except Exception as e:
                    self.logger.error(f"Error getting positions: {e}")
                    # Update API metrics in health check
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
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

                # Wait for next check
                self.logger.debug(f"Waiting {self.check_interval} seconds until next check...")
                time.sleep(self.check_interval)

            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                self.logger.error(f"Error in main loop: {e}")
                self.logger.error(f"Detailed error: {error_details}")

                # Update health check with error
                self.health_check.update_component_status("api_client", "error")

                if self.notifier:
                    self.notifier.notify_error(f"Error in main loop: {e}")

                # Emit error to web interface
                emit_log(f"Error in main loop: {e}", "error")

                # Wait before retrying
                self.logger.info(f"Waiting {self.check_interval} seconds before retrying...")
                time.sleep(self.check_interval)



    def shutdown(self, signum=None, _=None):
        """Shutdown the bot gracefully.

        Args:
            signum (int, optional): Signal number. Defaults to None.
            _ (object, optional): Unused frame parameter. Defaults to None.
        """
        self.logger.info("Shutting down Trading Bot...")
        self.running = False

        # Emit status update to web interface
        emit_status_update({
            'running': self.running,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'dry_run': self.dry_run,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        # Emit log message to web interface
        emit_log("Shutting down Trading Bot...", "info")

        # Stop WebSocket if enabled
        if self.use_websocket:
            self.logger.info("Stopping WebSocket...")
            self.bybit_client.stop_websocket()
            self.health_check.update_component_status("websocket", "unknown")
            emit_log("WebSocket stopped", "info")

        # Close all positions if configured
        if config.CLOSE_POSITIONS_ON_SHUTDOWN:
            self.logger.info("Closing all positions...")
            self.order_manager.exit_position(reason="SHUTDOWN")
            emit_log("Closing all positions...", "info")

        # Stop health check system
        self.logger.info("Stopping health check system...")
        self.health_check.stop()
        emit_log("Health check system stopped", "info")

        # Send shutdown notification
        if self.notifier:
            self.notifier.notify_bot_status(status="STOPPED")

        self.logger.info("Trading Bot stopped")
        emit_log("Trading Bot stopped", "info")

        # Don't exit if called from web interface
        if signum is not None:
            sys.exit(0)

if __name__ == "__main__":
    bot = TradingBot()

    # Start web interface in a separate thread if enabled
    if config.WEB_INTERFACE_ENABLED and bot.web_interface:
        web_thread = threading.Thread(
            target=bot.web_interface.run,
            kwargs={
                'host': config.WEB_HOST,
                'port': config.WEB_PORT,
                'debug': config.WEB_DEBUG
            }
        )
        web_thread.daemon = True
        web_thread.start()
        print(f"Web interface started on http://{config.WEB_HOST}:{config.WEB_PORT}")

    # Start the bot
    bot.run()
