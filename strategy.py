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

        # Multi-timeframe analysis parameters
        self.multi_timeframe_enabled = config.MULTI_TIMEFRAME_ENABLED
        self.confirmation_timeframes = config.CONFIRMATION_TIMEFRAMES
        self.mtf_alignment_required = config.MTF_ALIGNMENT_REQUIRED
        self.mtf_weight_main = config.MTF_WEIGHT_MAIN
        self.mtf_weight_lower = config.MTF_WEIGHT_LOWER
        self.mtf_weight_higher = config.MTF_WEIGHT_HIGHER
        self.mtf_volatility_adjustment = config.MTF_VOLATILITY_ADJUSTMENT

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

            # Calculate MACD using our own implementation
            try:
                # Make sure we have enough data for MACD calculation
                min_periods = max(self.macd_slow, self.macd_fast, self.macd_signal)
                if len(df) >= min_periods:
                    # Make sure there are no NaN values in the close price
                    if not df['close'].isna().any():
                        # Calculate MACD using our own implementation
                        try:
                            # Calculate EMAs for MACD
                            fast_ema = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
                            slow_ema = df['close'].ewm(span=self.macd_slow, adjust=False).mean()

                            # Calculate MACD line
                            macd_line = fast_ema - slow_ema

                            # Calculate signal line
                            signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()

                            # Calculate histogram
                            histogram = macd_line - signal_line

                            # Assign to dataframe
                            df['macd'] = macd_line
                            df['macd_signal'] = signal_line
                            df['macd_hist'] = histogram

                            # Fill any remaining NaN values with 0
                            df['macd'] = df['macd'].fillna(0.0)
                            df['macd_signal'] = df['macd_signal'].fillna(0.0)
                            df['macd_hist'] = df['macd_hist'].fillna(0.0)

                            if self.logger:
                                self.logger.debug("MACD calculated successfully using custom implementation")

                        except Exception as inner_e:
                            if self.logger:
                                self.logger.warning(f"Custom MACD calculation failed: {inner_e}, using default values")
                            # Use default values
                            df['macd'] = 0.0
                            df['macd_signal'] = 0.0
                            df['macd_hist'] = 0.0
                    else:
                        if self.logger:
                            self.logger.warning("Close price contains NaN values, using default MACD values")
                        # Use default values
                        df['macd'] = 0.0
                        df['macd_signal'] = 0.0
                        df['macd_hist'] = 0.0
                else:
                    if self.logger:
                        self.logger.warning(f"Not enough data for MACD calculation. Need at least {min_periods} rows, got {len(df)}. Using default values.")
                    # Use default values
                    df['macd'] = 0.0
                    df['macd_signal'] = 0.0
                    df['macd_hist'] = 0.0
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to calculate MACD: {e}, using default values")
                # Use default values
                df['macd'] = 0.0
                df['macd_signal'] = 0.0
                df['macd_hist'] = 0.0

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
                # Log more detailed error information
                import traceback
                self.logger.error(f"Detailed error: {traceback.format_exc()}")
                # Log the DataFrame info
                if df is not None and not df.empty:
                    self.logger.error(f"DataFrame columns: {df.columns.tolist()}")
                    self.logger.error(f"DataFrame head: {df.head(1).to_dict()}")
            return None

    def generate_signal(self, df, mtf_data=None):
        """
        Generate trading signal based on indicators.

        Args:
            df (pandas.DataFrame): Price data with indicators for the main timeframe.
            mtf_data (dict, optional): Dictionary of DataFrames with indicators for other timeframes.
                                      Format: {timeframe: dataframe}

        Returns:
            str: Signal (LONG, SHORT, NONE).
        """
        if df is None or df.empty or len(df) < 2:
            if self.logger:
                self.logger.error("Cannot generate signal: Insufficient data")
            return "NONE"

        try:
            # Use multi-timeframe analysis if enabled and data is available
            if self.multi_timeframe_enabled and mtf_data is not None:
                signal, score, timeframe_scores = self.analyze_multi_timeframe(df, mtf_data)

                # Log detailed multi-timeframe analysis results
                if self.logger and signal != "NONE":
                    self.logger.info(f"Multi-timeframe signal generated: {signal} (score: {score:.2f})")
                    for tf, tf_score in timeframe_scores.items():
                        self.logger.debug(f"  {tf} timeframe score: {tf_score:.2f}")

                return signal
            else:
                # Fall back to single timeframe analysis
                return self._generate_signal_from_single_timeframe(df)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to generate signal: {e}")
            return "NONE"

    def analyze_timeframe(self, df, timeframe):
        """
        Analyze a single timeframe and return a signal score.

        Args:
            df (pandas.DataFrame): Price data with indicators for the timeframe.
            timeframe (str): The timeframe being analyzed.

        Returns:
            float: Signal score (-1.0 to 1.0) where:
                  - Positive values indicate bullish bias (higher = stronger)
                  - Negative values indicate bearish bias (lower = stronger)
                  - Zero indicates no clear bias
        """
        if df is None or df.empty or len(df) < 2:
            if self.logger:
                self.logger.debug(f"Cannot analyze {timeframe} timeframe: Insufficient data")
            return 0.0

        try:
            # Get the last two rows for crossover detection
            current = df.iloc[-1]
            previous = df.iloc[-2]

            # Initialize score
            score = 0.0

            # EMA trend and crossover (weight: 0.3)
            fast_ema_current = current[f'ema_{self.fast_ema}']
            fast_ema_previous = previous[f'ema_{self.fast_ema}']
            slow_ema_current = current[f'ema_{self.slow_ema}']
            slow_ema_previous = previous[f'ema_{self.slow_ema}']

            # EMA crossover
            ema_crossover_up = fast_ema_previous < slow_ema_previous and fast_ema_current > slow_ema_current
            ema_crossover_down = fast_ema_previous > slow_ema_previous and fast_ema_current < slow_ema_current

            # EMA trend
            ema_trend = (fast_ema_current - fast_ema_previous) / fast_ema_previous

            if ema_crossover_up:
                score += 0.3
            elif ema_crossover_down:
                score -= 0.3
            else:
                # Add smaller score based on EMA trend direction
                score += min(max(ema_trend * 10, -0.15), 0.15)  # Cap at ±0.15

            # RSI (weight: 0.2)
            rsi_current = current['rsi']

            # RSI oversold/overbought
            if rsi_current < 30:  # Oversold
                score += 0.15
            elif rsi_current > 70:  # Overbought
                score -= 0.15
            else:
                # Normalize RSI between -0.1 and 0.1 for values between 30 and 70
                normalized_rsi = ((rsi_current - 50) / 20) * 0.1
                score += normalized_rsi

            # MACD (weight: 0.25)
            try:
                macd_current = float(current['macd'])
                macd_signal_current = float(current['macd_signal'])
                macd_hist_current = float(current['macd_hist'])
                macd_previous = float(previous['macd'])
                macd_signal_previous = float(previous['macd_signal'])

                # MACD crossover
                macd_crossover_up = macd_previous < macd_signal_previous and macd_current > macd_signal_current
                macd_crossover_down = macd_previous > macd_signal_previous and macd_current < macd_signal_current
            except (TypeError, ValueError, KeyError) as e:
                if self.logger:
                    self.logger.debug(f"MACD calculation error in analyze_timeframe: {e}, using default values")
                macd_current = 0.0
                macd_signal_current = 0.0
                macd_hist_current = 0.0
                macd_crossover_up = False
                macd_crossover_down = False

            if macd_crossover_up:
                score += 0.2
            elif macd_crossover_down:
                score -= 0.2
            else:
                # Add smaller score based on histogram
                score += min(max(macd_hist_current * 5, -0.15), 0.15)  # Cap at ±0.15

            # Volume (weight: 0.15)
            volume_ratio = current['volume_ratio']
            obv_slope = current['obv_slope']

            # Volume confirmation
            if volume_ratio > self.volume_threshold:
                if obv_slope > 0:
                    score += 0.15
                elif obv_slope < 0:
                    score -= 0.15

            # Pattern recognition (weight: 0.1)
            if self.pattern_recognition_enabled and 'bullish_pattern_strength' in current and 'bearish_pattern_strength' in current:
                bullish_strength = current['bullish_pattern_strength']
                bearish_strength = current['bearish_pattern_strength']

                # Normalize pattern strength to -0.1 to 0.1 range
                pattern_score = (bullish_strength - bearish_strength) / 10
                score += min(max(pattern_score, -0.1), 0.1)  # Cap at ±0.1

            # Cap final score between -1.0 and 1.0
            score = min(max(score, -1.0), 1.0)

            if self.logger:
                self.logger.debug(f"{timeframe} analysis score: {score:.2f}")

            return score

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to analyze {timeframe} timeframe: {e}")
            return 0.0

    def analyze_multi_timeframe(self, main_df, mtf_data):
        """
        Analyze multiple timeframes and generate a weighted signal score.

        Args:
            main_df (pandas.DataFrame): Price data with indicators for the main timeframe.
            mtf_data (dict): Dictionary of DataFrames with indicators for other timeframes.
                             Format: {timeframe: dataframe}

        Returns:
            tuple: (signal, score, timeframe_scores)
                  - signal: 'LONG', 'SHORT', or 'NONE'
                  - score: Overall weighted score (-1.0 to 1.0)
                  - timeframe_scores: Dictionary of scores by timeframe
        """
        if not self.multi_timeframe_enabled or mtf_data is None:
            # If multi-timeframe analysis is disabled, use only the main timeframe
            signal = self._generate_signal_from_single_timeframe(main_df)
            return signal, 0.0, {}

        try:
            main_timeframe = config.TIMEFRAME
            timeframe_scores = {}
            timeframe_weights = {}

            # Get main timeframe score
            main_score = self.analyze_timeframe(main_df, main_timeframe)
            timeframe_scores[main_timeframe] = main_score
            timeframe_weights[main_timeframe] = self.mtf_weight_main

            # Get scores for other timeframes
            for timeframe, df in mtf_data.items():
                if df is not None and not df.empty:
                    score = self.analyze_timeframe(df, timeframe)
                    timeframe_scores[timeframe] = score

                    # Assign weight based on timeframe (higher timeframes get more weight)
                    if self._is_higher_timeframe(timeframe, main_timeframe):
                        timeframe_weights[timeframe] = self.mtf_weight_higher
                    else:
                        timeframe_weights[timeframe] = self.mtf_weight_lower

            # Adjust weights based on volatility if enabled
            if self.mtf_volatility_adjustment and 'atr' in main_df.columns:
                self._adjust_weights_by_volatility(timeframe_weights, main_df)

            # Calculate weighted average score
            total_weight = sum(timeframe_weights.values())
            weighted_score = sum(score * timeframe_weights[tf] for tf, score in timeframe_scores.items()) / total_weight

            # Count aligned timeframes
            aligned_bullish = sum(1 for score in timeframe_scores.values() if score > 0.3)
            aligned_bearish = sum(1 for score in timeframe_scores.values() if score < -0.3)

            # Generate signal based on weighted score and alignment requirement
            signal = "NONE"
            if weighted_score > 0.4 and aligned_bullish >= self.mtf_alignment_required:
                signal = "LONG"
            elif weighted_score < -0.4 and aligned_bearish >= self.mtf_alignment_required:
                signal = "SHORT"

            if self.logger:
                self.logger.info(f"Multi-timeframe analysis - Weighted score: {weighted_score:.2f}, Signal: {signal}")
                self.logger.debug(f"Timeframe scores: {timeframe_scores}")
                self.logger.debug(f"Aligned timeframes - Bullish: {aligned_bullish}, Bearish: {aligned_bearish}")

            return signal, weighted_score, timeframe_scores

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to perform multi-timeframe analysis: {e}")
            return "NONE", 0.0, {}

    def _generate_signal_from_single_timeframe(self, df):
        """
        Generate trading signal based on indicators from a single timeframe.
        This is the original signal generation logic.

        Args:
            df (pandas.DataFrame): Price data with indicators.

        Returns:
            str: Signal (LONG, SHORT, NONE).
        """
        if df is None or df.empty or len(df) < 2:
            if self.logger:
                self.logger.warning("Cannot generate signal from single timeframe: Insufficient data")
            return "NONE"

        # Check if required indicators are present
        required_indicators = ['ema_20', 'ema_50', 'rsi', 'macd', 'macd_signal', 'macd_hist', 'volume_ratio', 'obv_slope']
        missing_indicators = [ind for ind in required_indicators if ind not in df.columns]

        if missing_indicators:
            if self.logger:
                self.logger.warning(f"Cannot generate signal from single timeframe: Missing indicators {missing_indicators}")
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
            try:
                macd_current = float(current['macd'])
                macd_signal_current = float(current['macd_signal'])
                macd_hist_current = float(current['macd_hist'])
                macd_previous = float(previous['macd'])
                macd_signal_previous = float(previous['macd_signal'])

                # Check for MACD crossover
                macd_crossover_up = macd_previous < macd_signal_previous and macd_current > macd_signal_current
                macd_crossover_down = macd_previous > macd_signal_previous and macd_current < macd_signal_current
            except (TypeError, ValueError, KeyError) as e:
                if self.logger:
                    self.logger.debug(f"MACD calculation error in _generate_signal_from_single_timeframe: {e}, using default values")
                macd_current = 0.0
                macd_signal_current = 0.0
                macd_hist_current = 0.0
                macd_crossover_up = False
                macd_crossover_down = False

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

            # Generate signal with volume and pattern confirmation if required
            if ema_crossover_up and rsi_not_overbought and macd_positive:
                # Check volume confirmation
                volume_confirmed = not self.volume_required or volume_confirms_bullish
                # Check pattern confirmation
                pattern_confirmed = not self.pattern_confirmation_required or pattern_confirms_bullish

                if volume_confirmed and pattern_confirmed:
                    return "LONG"
                else:
                    return "NONE"  # Confirmation failed
            elif ema_crossover_down and rsi_not_oversold and macd_negative:
                # Check volume confirmation
                volume_confirmed = not self.volume_required or volume_confirms_bearish
                # Check pattern confirmation
                pattern_confirmed = not self.pattern_confirmation_required or pattern_confirms_bearish

                if volume_confirmed and pattern_confirmed:
                    return "SHORT"
                else:
                    return "NONE"  # Confirmation failed
            else:
                return "NONE"

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to generate signal from single timeframe: {e}")
            return "NONE"

    def _is_higher_timeframe(self, timeframe1, timeframe2):
        """
        Check if timeframe1 is higher than timeframe2.

        Args:
            timeframe1 (str): First timeframe (e.g., '1h', '4h', '1d').
            timeframe2 (str): Second timeframe (e.g., '1h', '4h', '1d').

        Returns:
            bool: True if timeframe1 is higher than timeframe2, False otherwise.
        """
        # Define timeframe hierarchy (from lowest to highest)
        hierarchy = {
            '1m': 1, '3m': 2, '5m': 3, '15m': 4, '30m': 5,
            '1h': 6, '2h': 7, '4h': 8, '6h': 9, '12h': 10,
            '1d': 11, '3d': 12, '1w': 13, '1M': 14
        }

        # Get hierarchy values
        value1 = hierarchy.get(timeframe1, 0)
        value2 = hierarchy.get(timeframe2, 0)

        return value1 > value2

    def _adjust_weights_by_volatility(self, weights, df):
        """
        Adjust timeframe weights based on market volatility.
        In high volatility, give more weight to higher timeframes.
        In low volatility, weights remain balanced.

        Args:
            weights (dict): Dictionary of timeframe weights to adjust.
            df (pandas.DataFrame): Price data with ATR indicator.
        """
        try:
            # Calculate volatility using ATR relative to price
            current_price = df.iloc[-1]['close']
            current_atr = df.iloc[-1]['atr']
            volatility_ratio = current_atr / current_price

            # Adjust weights based on volatility
            # Higher volatility = more weight to higher timeframes
            if volatility_ratio > 0.03:  # High volatility
                for tf in weights:
                    if self._is_higher_timeframe(tf, config.TIMEFRAME):
                        weights[tf] *= 1.3  # Increase higher timeframe weight
                    elif tf != config.TIMEFRAME:  # Lower timeframe
                        weights[tf] *= 0.7  # Decrease lower timeframe weight

            if self.logger:
                self.logger.debug(f"Adjusted weights by volatility (ratio: {volatility_ratio:.4f}): {weights}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to adjust weights by volatility: {e}")

    def should_exit_position(self, df, position_side, mtf_data=None):
        """
        Check if position should be exited based on opposite signal.

        Args:
            df (pandas.DataFrame): Price data with indicators.
            position_side (str): Current position side (Buy or Sell).
            mtf_data (dict, optional): Dictionary of DataFrames with indicators for other timeframes.

        Returns:
            bool: True if position should be exited, False otherwise.
        """
        if df is None or df.empty or len(df) < 2:
            return False

        try:
            # Generate signal using multi-timeframe analysis if enabled and data is available
            if self.multi_timeframe_enabled and mtf_data is not None:
                signal, score, _ = self.analyze_multi_timeframe(df, mtf_data)
            else:
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
