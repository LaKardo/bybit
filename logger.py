"""
Logger module for the Bybit Trading Bot.
Handles logging to file and console.
"""

import logging
import os
from datetime import datetime
import config

class Logger:
    """
    Logger class for the Bybit Trading Bot.
    Handles logging to file and console.
    """
    def __init__(self, log_file=None, log_level=None):
        """
        Initialize the logger.
        
        Args:
            log_file (str, optional): Path to the log file. Defaults to config.LOG_FILE.
            log_level (str, optional): Log level. Defaults to config.LOG_LEVEL.
        """
        self.log_file = log_file or config.LOG_FILE
        self.log_level = log_level or config.LOG_LEVEL
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Set up logging
        self.logger = logging.getLogger("TradingBot")
        self.logger.setLevel(self._get_log_level(self.log_level))
        
        # Clear existing handlers
        self.logger.handlers = []
        
        # Create file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(self._get_log_level(self.log_level))
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self._get_log_level(self.log_level))
        
        # Create formatter
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', 
                                     datefmt='%Y-%m-%d %H:%M:%S')
        
        # Add formatter to handlers
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.info(f"Logger initialized with level: {self.log_level}")
    
    def _get_log_level(self, level_str):
        """
        Convert string log level to logging level.
        
        Args:
            level_str (str): Log level as string.
            
        Returns:
            int: Logging level.
        """
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return levels.get(level_str.upper(), logging.INFO)
    
    def debug(self, message):
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message):
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message):
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message):
        """Log critical message."""
        self.logger.critical(message)
    
    def trade(self, action, symbol, side, quantity, price, sl=None, tp=None):
        """
        Log trade information.
        
        Args:
            action (str): Trade action (ENTRY, EXIT).
            symbol (str): Trading symbol.
            side (str): Trade side (BUY, SELL).
            quantity (float): Trade quantity.
            price (float): Trade price.
            sl (float, optional): Stop loss price.
            tp (float, optional): Take profit price.
        """
        message = f"TRADE: {action} {side} {quantity} {symbol} @ {price}"
        if sl:
            message += f", SL: {sl}"
        if tp:
            message += f", TP: {tp}"
        self.info(message)
    
    def signal(self, symbol, timeframe, signal_type, indicators=None):
        """
        Log signal information.
        
        Args:
            symbol (str): Trading symbol.
            timeframe (str): Timeframe.
            signal_type (str): Signal type (LONG, SHORT, EXIT).
            indicators (dict, optional): Indicator values.
        """
        message = f"SIGNAL: {signal_type} on {symbol} ({timeframe})"
        if indicators:
            message += f", Indicators: {indicators}"
        self.info(message)
    
    def balance(self, available_balance, wallet_balance, unrealized_pnl=None):
        """
        Log balance information.
        
        Args:
            available_balance (float): Available balance.
            wallet_balance (float): Wallet balance.
            unrealized_pnl (float, optional): Unrealized PnL.
        """
        message = f"BALANCE: Available: {available_balance}, Wallet: {wallet_balance}"
        if unrealized_pnl is not None:
            message += f", Unrealized PnL: {unrealized_pnl}"
        self.info(message)
    
    def position(self, symbol, side, size, entry_price, liq_price=None, unrealized_pnl=None):
        """
        Log position information.
        
        Args:
            symbol (str): Trading symbol.
            side (str): Position side (BUY, SELL).
            size (float): Position size.
            entry_price (float): Entry price.
            liq_price (float, optional): Liquidation price.
            unrealized_pnl (float, optional): Unrealized PnL.
        """
        message = f"POSITION: {side} {size} {symbol} @ {entry_price}"
        if liq_price:
            message += f", Liq: {liq_price}"
        if unrealized_pnl is not None:
            message += f", PnL: {unrealized_pnl}"
        self.info(message)
