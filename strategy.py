"""
Strategy module for the Bybit Trading Bot.
Implements the trading strategy using technical indicators.
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import config
from pattern_recognition import PatternRecognition

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

        # Volume filter parameters
        self.volume_ma_period = config.VOLUME_MA_PERIOD
        self.volume_threshold = config.VOLUME_THRESHOLD
        self.obv_smoothing = config.OBV_SMOOTHING
        self.volume_required = config.VOLUME_REQUIRED

        # Pattern recognition parameters
        self.pattern_recognition_enabled = config.PATTERN_RECOGNITION_ENABLED
        self.pattern_strength_threshold = config.PATTERN_STRENGTH_THRESHOLD
        self.pattern_confirmation_required = config.PATTERN_CONFIRMATION_REQUIRED

        # Complex pattern parameters
        self.complex_patterns_enabled = config.COMPLEX_PATTERNS_ENABLED
        self.complex_pattern_min_candles = config.COMPLEX_PATTERN_MIN_CANDLES
        self.hs_pattern_shoulder_diff_threshold = config.HS_PATTERN_SHOULDER_DIFF_THRESHOLD
        self.double_pattern_level_threshold = config.DOUBLE_PATTERN_LEVEL_THRESHOLD

        # Initialize pattern recognition module
        self.pattern_recognition = PatternRecognition(
            logger=self.logger,
            complex_patterns_enabled=self.complex_patterns_enabled,
            hs_shoulder_diff_threshold=self.hs_pattern_shoulder_diff_threshold,
            double_pattern_level_threshold=self.double_pattern_level_threshold
        )

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

            # Calculate Volume Indicators
            # Volume Moving Average
            df['volume_ma'] = ta.sma(df['volume'], length=self.volume_ma_period)
            df['volume_ratio'] = df['volume'] / df['volume_ma']

            # On-Balance Volume (OBV)
            df['obv'] = ta.obv(df['close'], df['volume'])
            df['obv_ema'] = ta.ema(df['obv'], length=self.obv_smoothing)

            # Calculate OBV slope (direction)
            df['obv_slope'] = df['obv_ema'].diff()

            # Drop NaN values
            df = df.dropna()

            # Detect candlestick patterns if enabled
            if self.pattern_recognition_enabled:
                df = self.pattern_recognition.detect_patterns(df)
                if self.logger:
                    self.logger.debug("Candlestick patterns detected")

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

            # Check for Volume conditions
            volume_ratio = current['volume_ratio']
            obv_slope = current['obv_slope']

            # Volume confirmation for long (bullish) signals
            volume_confirms_bullish = volume_ratio > self.volume_threshold and obv_slope > 0

            # Volume confirmation for short (bearish) signals
            volume_confirms_bearish = volume_ratio > self.volume_threshold and obv_slope < 0

            # Long signal conditions
            ema_crossover_up = fast_ema_previous < slow_ema_previous and fast_ema_current > slow_ema_current
            rsi_not_overbought = rsi_current < self.rsi_overbought
            macd_positive = macd_hist_current > 0 or macd_crossover_up

            # Short signal conditions
            ema_crossover_down = fast_ema_previous > slow_ema_previous and fast_ema_current < slow_ema_current
            rsi_not_oversold = rsi_current > self.rsi_oversold
            macd_negative = macd_hist_current < 0 or macd_crossover_down

            # Check for pattern recognition signals if enabled
            pattern_confirms_bullish = False
            pattern_confirms_bearish = False

            if self.pattern_recognition_enabled and 'bullish_pattern_strength' in current and 'bearish_pattern_strength' in current:
                bullish_pattern_strength = current['bullish_pattern_strength']
                bearish_pattern_strength = current['bearish_pattern_strength']

                pattern_confirms_bullish = bullish_pattern_strength >= self.pattern_strength_threshold
                pattern_confirms_bearish = bearish_pattern_strength >= self.pattern_strength_threshold

                if self.logger:
                    self.logger.debug(f"Pattern strengths - Bullish: {bullish_pattern_strength}, Bearish: {bearish_pattern_strength}")

            # Generate signal with volume and pattern confirmation if required
            if ema_crossover_up and rsi_not_overbought and macd_positive:
                # Check volume confirmation
                volume_confirmed = not self.volume_required or volume_confirms_bullish
                # Check pattern confirmation
                pattern_confirmed = not self.pattern_confirmation_required or pattern_confirms_bullish

                if volume_confirmed and pattern_confirmed:
                    signal = "LONG"
                else:
                    signal = "NONE"  # Confirmation failed
                    if self.logger:
                        if not volume_confirmed:
                            self.logger.debug("LONG signal rejected: Insufficient volume confirmation")
                        if not pattern_confirmed:
                            self.logger.debug("LONG signal rejected: Insufficient pattern confirmation")
            elif ema_crossover_down and rsi_not_oversold and macd_negative:
                # Check volume confirmation
                volume_confirmed = not self.volume_required or volume_confirms_bearish
                # Check pattern confirmation
                pattern_confirmed = not self.pattern_confirmation_required or pattern_confirms_bearish

                if volume_confirmed and pattern_confirmed:
                    signal = "SHORT"
                else:
                    signal = "NONE"  # Confirmation failed
                    if self.logger:
                        if not volume_confirmed:
                            self.logger.debug("SHORT signal rejected: Insufficient volume confirmation")
                        if not pattern_confirmed:
                            self.logger.debug("SHORT signal rejected: Insufficient pattern confirmation")
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
                    "Volume Ratio": round(volume_ratio, 2),
                    "OBV Slope": round(obv_slope, 2),
                    "ATR": round(current['atr'], 2)
                }

                # Add pattern information if enabled
                if self.pattern_recognition_enabled and 'bullish_pattern_strength' in current and 'bearish_pattern_strength' in current:
                    indicators["Bullish Pattern Strength"] = current['bullish_pattern_strength']
                    indicators["Bearish Pattern Strength"] = current['bearish_pattern_strength']

                    # Add detected patterns
                    bullish_patterns = []
                    bearish_patterns = []

                    # Check for bullish patterns
                    pattern_columns = ['hammer', 'bullish_engulfing', 'bullish_harami', 'tweezer_bottom',
                                      'morning_star', 'three_white_soldiers', 'bullish_marubozu']
                    for pattern in pattern_columns:
                        if pattern in current and current[pattern]:
                            bullish_patterns.append(pattern.replace('_', ' ').title())

                    # Check for complex bullish patterns if enabled
                    if self.complex_patterns_enabled:
                        complex_bullish_patterns = ['inverse_head_and_shoulders', 'double_bottom']
                        for pattern in complex_bullish_patterns:
                            if pattern in current and current[pattern]:
                                bullish_patterns.append(pattern.replace('_', ' ').title())

                    # Check for bearish patterns
                    pattern_columns = ['shooting_star', 'inverted_hammer', 'bearish_engulfing', 'bearish_harami',
                                      'tweezer_top', 'evening_star', 'three_black_crows', 'bearish_marubozu']
                    for pattern in pattern_columns:
                        if pattern in current and current[pattern]:
                            bearish_patterns.append(pattern.replace('_', ' ').title())

                    # Check for complex bearish patterns if enabled
                    if self.complex_patterns_enabled:
                        complex_bearish_patterns = ['head_and_shoulders', 'double_top']
                        for pattern in complex_bearish_patterns:
                            if pattern in current and current[pattern]:
                                bearish_patterns.append(pattern.replace('_', ' ').title())

                    if bullish_patterns:
                        indicators["Bullish Patterns"] = ", ".join(bullish_patterns)
                    if bearish_patterns:
                        indicators["Bearish Patterns"] = ", ".join(bearish_patterns)

                self.logger.debug(f"Current indicators: {indicators}")

                if signal != "NONE":
                    confirmation_info = []
                    if volume_confirms_bullish if signal == "LONG" else volume_confirms_bearish:
                        confirmation_info.append("Volume confirms")
                    if pattern_confirms_bullish if signal == "LONG" else pattern_confirms_bearish:
                        confirmation_info.append("Pattern confirms")

                    confirmation_str = ", ".join(confirmation_info) if confirmation_info else "No confirmations"
                    self.logger.info(f"Generated signal: {signal} ({confirmation_str})")

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
