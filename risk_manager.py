import math
import config

# Quantity precision constants
BTC_QUANTITY_PRECISION = 3
ETH_QUANTITY_PRECISION = 3
DEFAULT_QUANTITY_PRECISION = 2
class RiskManager:
    def __init__(self, logger=None):
        self.logger = logger
        self.risk_per_trade = config.RISK_PER_TRADE
        self.risk_reward_ratio = config.RISK_REWARD_RATIO
        self.sl_atr_multiplier = config.SL_ATR_MULTIPLIER
        if self.logger:
            self.logger.info(f"Risk Manager initialized with risk per trade: {self.risk_per_trade * 100}%")
    def calculate_position_size(self, balance, entry_price, stop_loss_price):
        if not balance or not entry_price or not stop_loss_price:
            if self.logger:
                self.logger.error("Cannot calculate position size: Missing parameters")
            return None
        try:
            risk_amount = balance * self.risk_per_trade
            sl_distance_percent = abs(entry_price - stop_loss_price) / entry_price
            position_size_usdt = risk_amount / sl_distance_percent
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
        if not entry_price or not atr_value:
            if self.logger:
                self.logger.error("Cannot calculate stop loss: Missing parameters")
            return None
        try:
            sl_distance = atr_value * self.sl_atr_multiplier
            if side.upper() == "BUY":
                stop_loss = entry_price - sl_distance
            else:
                stop_loss = entry_price + sl_distance
            stop_loss = round(stop_loss, self._get_price_precision(entry_price))
            if self.logger:
                self.logger.info(f"Calculated stop loss: {stop_loss} (ATR: {atr_value}, Distance: {sl_distance})")
            return stop_loss
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to calculate stop loss: {e}")
            return None
    def calculate_take_profit(self, entry_price, stop_loss_price, side):
        if not entry_price or not stop_loss_price:
            if self.logger:
                self.logger.error("Cannot calculate take profit: Missing parameters")
            return None
        try:
            risk_distance = abs(entry_price - stop_loss_price)
            reward_distance = risk_distance * self.risk_reward_ratio
            if side.upper() == "BUY":
                take_profit = entry_price + reward_distance
            else:
                take_profit = entry_price - reward_distance
            take_profit = round(take_profit, self._get_price_precision(entry_price))
            if self.logger:
                self.logger.info(f"Calculated take profit: {take_profit} (Risk: {risk_distance}, Reward: {reward_distance})")
            return take_profit
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to calculate take profit: {e}")
            return None
    def _get_price_precision(self, price):
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
        if symbol and "BTC" in symbol:
            return round(quantity, BTC_QUANTITY_PRECISION)
        elif symbol and "ETH" in symbol:
            return round(quantity, ETH_QUANTITY_PRECISION)
        else:
            return round(quantity, DEFAULT_QUANTITY_PRECISION)
    def validate_position_size(self, position_size, min_order_size=0.001):
        if position_size < min_order_size:
            if self.logger:
                self.logger.warning(f"Position size {position_size} is below minimum order size {min_order_size}")
            return None
        return position_size
