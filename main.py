"""
Main module for the Bybit Trading Bot.
Coordinates all components and implements the main trading loop.
"""

import time
import signal
import sys
import os
from datetime import datetime

import config
from logger import Logger
from notifier import TelegramNotifier
from bybit_client import BybitAPIClient
from strategy import Strategy
from risk_manager import RiskManager
from order_manager import OrderManager

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
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
        # Bot state
        self.running = False
        
        self.logger.info(f"Trading Bot initialized for {self.symbol} on {self.timeframe} timeframe")
        self.logger.info(f"Dry run mode: {self.dry_run}")
        
        # Send startup notification
        if self.notifier:
            mode = "DRY RUN" if self.dry_run else "LIVE TRADING"
            self.notifier.notify_bot_status(
                status="STARTED",
                additional_info=f"Trading {self.symbol} on {self.timeframe} timeframe\nMode: {mode}"
            )
    
    def run(self):
        """Run the main trading loop."""
        self.running = True
        self.logger.info("Starting main trading loop...")
        
        while self.running:
            try:
                # Get historical data
                klines = self.bybit_client.get_klines(
                    symbol=self.symbol,
                    interval=self.timeframe,
                    limit=100
                )
                
                if klines is None or klines.empty:
                    self.logger.error("Failed to get historical data, retrying...")
                    time.sleep(self.check_interval)
                    continue
                
                # Calculate indicators
                price_data = self.strategy.calculate_indicators(klines)
                if price_data is None:
                    self.logger.error("Failed to calculate indicators, retrying...")
                    time.sleep(self.check_interval)
                    continue
                
                # Check if we should exit current position based on opposite signal
                self.order_manager.check_and_exit_on_signal(price_data)
                
                # Generate trading signal
                signal = self.strategy.generate_signal(price_data)
                
                # Log signal
                if signal != "NONE":
                    self.logger.signal(
                        symbol=self.symbol,
                        timeframe=self.timeframe,
                        signal_type=signal,
                        indicators={
                            f"EMA{config.FAST_EMA}": round(price_data.iloc[-1][f'ema_{config.FAST_EMA}'], 2),
                            f"EMA{config.SLOW_EMA}": round(price_data.iloc[-1][f'ema_{config.SLOW_EMA}'], 2),
                            "RSI": round(price_data.iloc[-1]['rsi'], 2),
                            "MACD": round(price_data.iloc[-1]['macd'], 4),
                            "MACD Signal": round(price_data.iloc[-1]['macd_signal'], 4),
                            "MACD Hist": round(price_data.iloc[-1]['macd_hist'], 4),
                            "ATR": round(price_data.iloc[-1]['atr'], 2)
                        }
                    )
                
                # Execute trading signal
                if signal in ["LONG", "SHORT"]:
                    self.order_manager.enter_position(signal, price_data)
                
                # Get and log balance
                balance_info = self.bybit_client.get_wallet_balance()
                if balance_info:
                    self.logger.balance(
                        available_balance=balance_info["available_balance"],
                        wallet_balance=balance_info["wallet_balance"],
                        unrealized_pnl=balance_info["unrealized_pnl"]
                    )
                
                # Get and log positions
                positions = self.bybit_client.get_positions(self.symbol)
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
                self.logger.error(f"Error in main loop: {e}")
                if self.notifier:
                    self.notifier.notify_error(f"Error in main loop: {e}")
                time.sleep(self.check_interval)
    
    def shutdown(self, signum=None, frame=None):
        """Shutdown the bot gracefully."""
        self.logger.info("Shutting down Trading Bot...")
        self.running = False
        
        # Close all positions if configured
        if config.CLOSE_POSITIONS_ON_SHUTDOWN:
            self.logger.info("Closing all positions...")
            self.order_manager.exit_position(reason="SHUTDOWN")
        
        # Send shutdown notification
        if self.notifier:
            self.notifier.notify_bot_status(status="STOPPED")
        
        self.logger.info("Trading Bot stopped")
        sys.exit(0)

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
