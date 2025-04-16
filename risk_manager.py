"""
Risk Manager module for the Bybit Trading Bot.
Handles risk management and position sizing.
"""

import math
import config

class RiskManager:
    """
    Risk Manager class for the Bybit Trading Bot.
    Handles risk management and position sizing.
    """
    def __init__(self, logger=None):
        """
        Initialize the risk manager.
        
        Args:
            logger (Logger, optional): Logger instance.
        """
        self.logger = logger
        
        # Risk parameters
        self.risk_per_trade = config.RISK_PER_TRADE
        self.risk_reward_ratio = config.RISK_REWARD_RATIO
        self.sl_atr_multiplier = config.SL_ATR_MULTIPLIER
        
        if self.logger:
            self.logger.info(f"Risk Manager initialized with risk per trade: {self.risk_per_trade * 100}%")
    
    def calculate_position_size(self, balance, entry_price, stop_loss_price):
        """
        Calculate position size based on risk parameters.
        
        Args:
            balance (float): Available balance.
            entry_price (float): Entry price.
            stop_loss_price (float): Stop loss price.
            
        Returns:
            float: Position size in base currency or None on error.
        """
        if not balance or not entry_price or not stop_loss_price:
            if self.logger:
                self.logger.error("Cannot calculate position size: Missing parameters")
            return None
        
        try:
            # Calculate risk amount in USDT
            risk_amount = balance * self.risk_per_trade
            
            # Calculate stop loss distance in percentage
            sl_distance_percent = abs(entry_price - stop_loss_price) / entry_price
            
            # Calculate position size in USDT
            position_size_usdt = risk_amount / sl_distance_percent
            
            # Calculate position size in base currency (e.g., BTC)
            position_size = position_size_usdt / entry_price
            
            if self.logger:
                self.logger.info(f"Calculated position size: {position_size} ({position_size_usdt} USDT)")
                self.logger.debug(f"Risk amount: {risk_amount} USDT, SL distance: {sl_distance_percent * 100}%")
            
            return position_size
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to calculate position size: {e}")
            return None
    
    def calculate_stop_loss(self, entry_price, side, atr_value):
        """
        Calculate stop loss price based on ATR.
        
        Args:
            entry_price (float): Entry price.
            side (str): Position side (Buy or Sell).
            atr_value (float): ATR value.
            
        Returns:
            float: Stop loss price or None on error.
        """
        if not entry_price or not atr_value:
            if self.logger:
                self.logger.error("Cannot calculate stop loss: Missing parameters")
            return None
        
        try:
            # Calculate stop loss distance
            sl_distance = atr_value * self.sl_atr_multiplier
            
            # Calculate stop loss price
            if side.upper() == "BUY":
                stop_loss = entry_price - sl_distance
            else:
                stop_loss = entry_price + sl_distance
            
            # Round to appropriate precision
            stop_loss = round(stop_loss, self._get_price_precision(entry_price))
            
            if self.logger:
                self.logger.info(f"Calculated stop loss: {stop_loss} (ATR: {atr_value}, Distance: {sl_distance})")
            
            return stop_loss
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to calculate stop loss: {e}")
            return None
    
    def calculate_take_profit(self, entry_price, stop_loss_price, side):
        """
        Calculate take profit price based on risk-reward ratio.
        
        Args:
            entry_price (float): Entry price.
            stop_loss_price (float): Stop loss price.
            side (str): Position side (Buy or Sell).
            
        Returns:
            float: Take profit price or None on error.
        """
        if not entry_price or not stop_loss_price:
            if self.logger:
                self.logger.error("Cannot calculate take profit: Missing parameters")
            return None
        
        try:
            # Calculate risk distance
            risk_distance = abs(entry_price - stop_loss_price)
            
            # Calculate reward distance
            reward_distance = risk_distance * self.risk_reward_ratio
            
            # Calculate take profit price
            if side.upper() == "BUY":
                take_profit = entry_price + reward_distance
            else:
                take_profit = entry_price - reward_distance
            
            # Round to appropriate precision
            take_profit = round(take_profit, self._get_price_precision(entry_price))
            
            if self.logger:
                self.logger.info(f"Calculated take profit: {take_profit} (Risk: {risk_distance}, Reward: {reward_distance})")
            
            return take_profit
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to calculate take profit: {e}")
            return None
    
    def _get_price_precision(self, price):
        """
        Get appropriate price precision based on price magnitude.
        
        Args:
            price (float): Price.
            
        Returns:
            int: Price precision.
        """
        if price >= 10000:
            return 1
        elif price >= 1000:
            return 2
        elif price >= 100:
            return 3
        elif price >= 10:
            return 4
        else:
            return 5
    
    def adjust_quantity_precision(self, quantity, symbol=None):
        """
        Adjust quantity precision based on symbol.
        
        Args:
            quantity (float): Quantity.
            symbol (str, optional): Trading symbol.
            
        Returns:
            float: Adjusted quantity.
        """
        # This is a simplified version. In a real implementation,
        # you would fetch the actual precision from the exchange.
        if symbol and "BTC" in symbol:
            return round(quantity, 3)
        elif symbol and "ETH" in symbol:
            return round(quantity, 3)
        else:
            return round(quantity, 2)
    
    def validate_position_size(self, position_size, min_order_size=0.001):
        """
        Validate position size against minimum order size.
        
        Args:
            position_size (float): Position size.
            min_order_size (float, optional): Minimum order size.
            
        Returns:
            float: Valid position size or None if too small.
        """
        if position_size < min_order_size:
            if self.logger:
                self.logger.warning(f"Position size {position_size} is below minimum order size {min_order_size}")
            return None
        
        return position_size
