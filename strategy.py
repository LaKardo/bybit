"""
Strategy module for the Bybit Trading Bot.
Implements the trading strategy using technical indicators.
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import config

class Strategy:
    """
    Strategy class for the Bybit Trading Bot.
    Implements the trading strategy using technical indicators.
    """
    def __init__(self, logger=None):
        """
        Initialize the strategy.
        
        Args:
            logger (Logger, optional): Logger instance.
        """
        self.logger = logger
        
        # Strategy parameters
        self.fast_ema = config.FAST_EMA
        self.slow_ema = config.SLOW_EMA
        self.rsi_period = config.RSI_PERIOD
        self.rsi_overbought = config.RSI_OVERBOUGHT
        self.rsi_oversold = config.RSI_OVERSOLD
        self.macd_fast = config.MACD_FAST
        self.macd_slow = config.MACD_SLOW
        self.macd_signal = config.MACD_SIGNAL
        self.atr_period = config.ATR_PERIOD
        
        if self.logger:
            self.logger.info("Strategy initialized")
    
    def calculate_indicators(self, df):
        """
        Calculate technical indicators.
        
        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.
            
        Returns:
            pandas.DataFrame: DataFrame with indicators.
        """
        if df is None or df.empty:
            if self.logger:
                self.logger.error("Cannot calculate indicators: No data provided")
            return None
        
        # Make a copy to avoid modifying the original
        df = df.copy()
        
        try:
            # Calculate EMAs
            df[f'ema_{self.fast_ema}'] = ta.ema(df['close'], length=self.fast_ema)
            df[f'ema_{self.slow_ema}'] = ta.ema(df['close'], length=self.slow_ema)
            
            # Calculate RSI
            df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)
            
            # Calculate MACD
            macd = ta.macd(df['close'], fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)
            df['macd'] = macd['MACD_12_26_9']
            df['macd_signal'] = macd['MACDs_12_26_9']
            df['macd_hist'] = macd['MACDh_12_26_9']
            
            # Calculate ATR
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_period)
            
            # Drop NaN values
            df = df.dropna()
            
            if self.logger:
                self.logger.debug("Indicators calculated successfully")
            
            return df
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to calculate indicators: {e}")
            return None
    
    def generate_signal(self, df):
        """
        Generate trading signal based on indicators.
        
        Args:
            df (pandas.DataFrame): Price data with indicators.
            
        Returns:
            str: Signal (LONG, SHORT, NONE).
        """
        if df is None or df.empty or len(df) < 2:
            if self.logger:
                self.logger.error("Cannot generate signal: Insufficient data")
            return "NONE"
        
        try:
            # Get the last two rows for crossover detection
            current = df.iloc[-1]
            previous = df.iloc[-2]
            
            # Check for EMA crossover
            fast_ema_current = current[f'ema_{self.fast_ema}']
            fast_ema_previous = previous[f'ema_{self.fast_ema}']
            slow_ema_current = current[f'ema_{self.slow_ema}']
            slow_ema_previous = previous[f'ema_{self.slow_ema}']
            
            # Check for MACD conditions
            macd_current = current['macd']
            macd_signal_current = current['macd_signal']
            macd_hist_current = current['macd_hist']
            macd_previous = previous['macd']
            macd_signal_previous = previous['macd_signal']
            
            # Check for MACD crossover
            macd_crossover_up = macd_previous < macd_signal_previous and macd_current > macd_signal_current
            macd_crossover_down = macd_previous > macd_signal_previous and macd_current < macd_signal_current
            
            # Check for RSI conditions
            rsi_current = current['rsi']
            
            # Long signal conditions
            ema_crossover_up = fast_ema_previous < slow_ema_previous and fast_ema_current > slow_ema_current
            rsi_not_overbought = rsi_current < self.rsi_overbought
            macd_positive = macd_hist_current > 0 or macd_crossover_up
            
            # Short signal conditions
            ema_crossover_down = fast_ema_previous > slow_ema_previous and fast_ema_current < slow_ema_current
            rsi_not_oversold = rsi_current > self.rsi_oversold
            macd_negative = macd_hist_current < 0 or macd_crossover_down
            
            # Generate signal
            if ema_crossover_up and rsi_not_overbought and macd_positive:
                signal = "LONG"
            elif ema_crossover_down and rsi_not_oversold and macd_negative:
                signal = "SHORT"
            else:
                signal = "NONE"
            
            # Log indicator values
            if self.logger:
                indicators = {
                    f"EMA{self.fast_ema}": round(fast_ema_current, 2),
                    f"EMA{self.slow_ema}": round(slow_ema_current, 2),
                    "RSI": round(rsi_current, 2),
                    "MACD": round(macd_current, 4),
                    "MACD Signal": round(macd_signal_current, 4),
                    "MACD Hist": round(macd_hist_current, 4),
                    "ATR": round(current['atr'], 2)
                }
                self.logger.debug(f"Current indicators: {indicators}")
                
                if signal != "NONE":
                    self.logger.info(f"Generated signal: {signal}")
            
            return signal
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to generate signal: {e}")
            return "NONE"
    
    def should_exit_position(self, df, position_side):
        """
        Check if position should be exited based on opposite signal.
        
        Args:
            df (pandas.DataFrame): Price data with indicators.
            position_side (str): Current position side (Buy or Sell).
            
        Returns:
            bool: True if position should be exited, False otherwise.
        """
        if df is None or df.empty or len(df) < 2:
            return False
        
        try:
            signal = self.generate_signal(df)
            
            # Exit long position on SHORT signal
            if position_side == "Buy" and signal == "SHORT":
                if self.logger:
                    self.logger.info("Exit signal for LONG position: Opposite signal detected")
                return True
            
            # Exit short position on LONG signal
            if position_side == "Sell" and signal == "LONG":
                if self.logger:
                    self.logger.info("Exit signal for SHORT position: Opposite signal detected")
                return True
            
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to check exit signal: {e}")
            return False
    
    def get_atr_value(self, df):
        """
        Get the current ATR value.
        
        Args:
            df (pandas.DataFrame): Price data with indicators.
            
        Returns:
            float: ATR value or None on error.
        """
        if df is None or df.empty:
            return None
        
        try:
            return df.iloc[-1]['atr']
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get ATR value: {e}")
            return None
