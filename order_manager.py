"""
Order Manager module for the Bybit Trading Bot.
Handles order placement and management.
"""

import time
import config

class OrderManager:
    """
    Order Manager class for the Bybit Trading Bot.
    Handles order placement and management.
    """
    def __init__(self, bybit_client, risk_manager, logger=None, notifier=None):
        """
        Initialize the order manager.
        
        Args:
            bybit_client (BybitAPIClient): Bybit API client.
            risk_manager (RiskManager): Risk manager.
            logger (Logger, optional): Logger instance.
            notifier (TelegramNotifier, optional): Telegram notifier.
        """
        self.bybit_client = bybit_client
        self.risk_manager = risk_manager
        self.logger = logger
        self.notifier = notifier
        
        # Trading parameters
        self.symbol = config.SYMBOL
        self.max_open_positions = config.MAX_OPEN_POSITIONS
        
        if self.logger:
            self.logger.info("Order Manager initialized")
    
    def enter_position(self, signal, price_data):
        """
        Enter a new position based on signal.
        
        Args:
            signal (str): Trading signal (LONG or SHORT).
            price_data (pandas.DataFrame): Price data with indicators.
            
        Returns:
            bool: Success or failure.
        """
        if signal not in ["LONG", "SHORT"]:
            if self.logger:
                self.logger.warning(f"Invalid signal for position entry: {signal}")
            return False
        
        # Check if we already have open positions
        positions = self.bybit_client.get_positions(self.symbol)
        if positions:
            for position in positions:
                size = float(position.get("size", 0))
                if size > 0:
                    if self.logger:
                        self.logger.warning(f"Already have an open position for {self.symbol}, skipping entry")
                    return False
        
        # Get current balance
        balance_info = self.bybit_client.get_wallet_balance()
        if not balance_info:
            if self.logger:
                self.logger.error("Failed to get wallet balance")
            return False
        
        available_balance = balance_info["available_balance"]
        
        # Get current ticker
        ticker = self.bybit_client.get_ticker(self.symbol)
        if not ticker:
            if self.logger:
                self.logger.error("Failed to get ticker")
            return False
        
        # Get entry price
        entry_price = float(ticker["lastPrice"])
        
        # Get ATR value
        atr_value = price_data.iloc[-1]["atr"] if "atr" in price_data.columns else None
        if not atr_value:
            if self.logger:
                self.logger.error("Failed to get ATR value")
            return False
        
        # Determine order side
        side = "Buy" if signal == "LONG" else "Sell"
        
        # Calculate stop loss
        stop_loss = self.risk_manager.calculate_stop_loss(entry_price, side, atr_value)
        if not stop_loss:
            if self.logger:
                self.logger.error("Failed to calculate stop loss")
            return False
        
        # Calculate take profit
        take_profit = self.risk_manager.calculate_take_profit(entry_price, stop_loss, side)
        if not take_profit:
            if self.logger:
                self.logger.error("Failed to calculate take profit")
            return False
        
        # Calculate position size
        position_size = self.risk_manager.calculate_position_size(available_balance, entry_price, stop_loss)
        if not position_size:
            if self.logger:
                self.logger.error("Failed to calculate position size")
            return False
        
        # Validate position size
        position_size = self.risk_manager.validate_position_size(position_size)
        if not position_size:
            if self.logger:
                self.logger.error("Position size is too small")
            return False
        
        # Adjust position size precision
        position_size = self.risk_manager.adjust_quantity_precision(position_size, self.symbol)
        
        # Set leverage
        leverage_set = self.bybit_client.set_leverage(self.symbol, config.LEVERAGE)
        if not leverage_set:
            if self.logger:
                self.logger.warning("Failed to set leverage, continuing anyway")
        
        # Place order
        order_result = self.bybit_client.place_market_order(
            symbol=self.symbol,
            side=side,
            qty=position_size,
            take_profit=take_profit,
            stop_loss=stop_loss
        )
        
        if not order_result:
            if self.logger:
                self.logger.error("Failed to place market order")
            return False
        
        # Log trade
        if self.logger:
            self.logger.trade(
                action="ENTRY",
                symbol=self.symbol,
                side=side,
                quantity=position_size,
                price=entry_price,
                sl=stop_loss,
                tp=take_profit
            )
        
        # Send notification
        if self.notifier:
            self.notifier.notify_trade_entry(
                symbol=self.symbol,
                side=side,
                quantity=position_size,
                price=entry_price,
                sl=stop_loss,
                tp=take_profit
            )
        
        return True
    
    def exit_position(self, reason="SIGNAL"):
        """
        Exit current position.
        
        Args:
            reason (str, optional): Exit reason. Defaults to "SIGNAL".
            
        Returns:
            bool: Success or failure.
        """
        # Get current position
        positions = self.bybit_client.get_positions(self.symbol)
        if not positions:
            if self.logger:
                self.logger.info(f"No position to exit for {self.symbol}")
            return True
        
        has_position = False
        for position in positions:
            size = float(position.get("size", 0))
            if size == 0:
                continue
                
            has_position = True
            side = position.get("side")
            entry_price = float(position.get("entryPrice", 0))
            position_value = float(position.get("positionValue", 0))
            unrealized_pnl = float(position.get("unrealisedPnl", 0))
            
            # Get current ticker for exit price
            ticker = self.bybit_client.get_ticker(self.symbol)
            exit_price = float(ticker["lastPrice"]) if ticker else 0
            
            # Close position
            close_result = self.bybit_client.close_position(self.symbol)
            if not close_result:
                if self.logger:
                    self.logger.error(f"Failed to close {side} position for {self.symbol}")
                return False
            
            # Log trade exit
            if self.logger:
                self.logger.trade(
                    action="EXIT",
                    symbol=self.symbol,
                    side=side,
                    quantity=size,
                    price=exit_price
                )
            
            # Send notification
            if self.notifier:
                self.notifier.notify_trade_exit(
                    symbol=self.symbol,
                    side=side,
                    quantity=size,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    pnl=unrealized_pnl,
                    exit_reason=reason
                )
        
        if not has_position:
            if self.logger:
                self.logger.info(f"No position to exit for {self.symbol}")
        
        return True
    
    def check_and_exit_on_signal(self, price_data):
        """
        Check if position should be exited based on opposite signal.
        
        Args:
            price_data (pandas.DataFrame): Price data with indicators.
            
        Returns:
            bool: True if position was exited, False otherwise.
        """
        # Get current position
        positions = self.bybit_client.get_positions(self.symbol)
        if not positions:
            return False
        
        for position in positions:
            size = float(position.get("size", 0))
            if size == 0:
                continue
                
            side = position.get("side")
            
            # Check if position should be exited
            from strategy import Strategy
            strategy = Strategy(self.logger)
            should_exit = strategy.should_exit_position(price_data, side)
            
            if should_exit:
                if self.logger:
                    self.logger.info(f"Exiting {side} position for {self.symbol} based on opposite signal")
                
                return self.exit_position(reason="OPPOSITE_SIGNAL")
        
        return False
