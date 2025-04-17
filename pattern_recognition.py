"""
Pattern Recognition module for the Bybit Trading Bot.
Implements candlestick pattern detection for trading signals.
"""

import numpy as np
import pandas as pd


class PatternRecognition:
    """
    Pattern Recognition class for detecting candlestick patterns.
    Implements various candlestick pattern detection algorithms.
    """

    def __init__(self, logger=None, complex_patterns_enabled=True, hs_shoulder_diff_threshold=0.1, double_pattern_level_threshold=0.03):
        """
        Initialize the pattern recognition module.

        Args:
            logger (Logger, optional): Logger instance.
            complex_patterns_enabled (bool): Whether to detect complex patterns.
            hs_shoulder_diff_threshold (float): Maximum allowed difference between shoulders in H&S patterns.
            double_pattern_level_threshold (float): Maximum allowed difference between tops/bottoms in double patterns.
        """
        self.logger = logger
        self.complex_patterns_enabled = complex_patterns_enabled
        self.hs_shoulder_diff_threshold = hs_shoulder_diff_threshold
        self.double_pattern_level_threshold = double_pattern_level_threshold

        if self.logger:
            self.logger.info("Pattern Recognition module initialized")

    def detect_patterns(self, df):
        """
        Detect candlestick patterns in the price data.

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with pattern columns added.
        """
        if df is None or df.empty:
            if self.logger:
                self.logger.error("Cannot detect patterns: No data provided")
            return None

        # Make a copy to avoid modifying the original
        df = df.copy()

        try:
            # Detect single candlestick patterns
            df = self.detect_doji(df)
            df = self.detect_hammer(df)
            df = self.detect_shooting_star(df)
            df = self.detect_marubozu(df)

            # Detect double candlestick patterns
            df = self.detect_engulfing(df)
            df = self.detect_harami(df)
            df = self.detect_tweezer(df)

            # Detect triple candlestick patterns
            df = self.detect_morning_star(df)
            df = self.detect_evening_star(df)
            df = self.detect_three_white_soldiers(df)
            df = self.detect_three_black_crows(df)

            # Detect complex chart patterns if enabled
            if self.complex_patterns_enabled:
                df = self.detect_head_and_shoulders(df)
                df = self.detect_inverse_head_and_shoulders(df)
                df = self.detect_double_top(df)
                df = self.detect_double_bottom(df)
                if self.logger:
                    self.logger.debug("Complex chart patterns detected")

            # Calculate pattern strength
            df = self.calculate_pattern_strength(df)

            if self.logger:
                self.logger.debug("Patterns detected successfully")

            return df

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to detect patterns: {e}")
            return df

    def detect_doji(self, df):
        """
        Detect Doji candlestick pattern.
        A Doji has almost the same open and close prices.

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with doji pattern column added.
        """
        # Calculate body size as percentage of the candle range
        body_size = abs(df['close'] - df['open'])
        candle_range = df['high'] - df['low']
        body_percentage = (body_size / candle_range) * 100

        # A Doji has a very small body (typically less than 5% of the range)
        df['doji'] = (body_percentage < 5) & (candle_range > 0)

        return df

    def detect_hammer(self, df):
        """
        Detect Hammer and Inverted Hammer patterns.
        A hammer has a small body at the top with a long lower shadow.

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with hammer pattern columns added.
        """
        # Calculate body and shadow sizes
        body_size = abs(df['close'] - df['open'])
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']

        # Hammer criteria: small body, very small upper shadow, long lower shadow
        df['hammer'] = (
            (body_size <= (df['high'] - df['low']) * 0.3) &  # Small body
            (lower_shadow >= body_size * 2) &  # Long lower shadow
            (upper_shadow <= body_size * 0.1)  # Very small upper shadow
        )

        # Inverted Hammer criteria: small body, long upper shadow, very small lower shadow
        df['inverted_hammer'] = (
            (body_size <= (df['high'] - df['low']) * 0.3) &  # Small body
            (upper_shadow >= body_size * 2) &  # Long upper shadow
            (lower_shadow <= body_size * 0.1)  # Very small lower shadow
        )

        return df

    def detect_shooting_star(self, df):
        """
        Detect Shooting Star pattern.
        A shooting star has a small body at the bottom with a long upper shadow.

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with shooting_star pattern column added.
        """
        # Calculate body and shadow sizes
        body_size = abs(df['close'] - df['open'])
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']

        # Shooting Star criteria: small body, long upper shadow, very small lower shadow
        # and appears in an uptrend
        df['shooting_star'] = (
            (body_size <= (df['high'] - df['low']) * 0.3) &  # Small body
            (upper_shadow >= body_size * 2) &  # Long upper shadow
            (lower_shadow <= body_size * 0.1)  # Very small lower shadow
        )

        return df

    def detect_marubozu(self, df):
        """
        Detect Marubozu candlestick pattern.
        A Marubozu has no or very small shadows.

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with marubozu pattern columns added.
        """
        # Calculate body and shadow sizes
        body_size = abs(df['close'] - df['open'])
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']

        # Marubozu criteria: large body, very small shadows
        df['bullish_marubozu'] = (
            (df['close'] > df['open']) &  # Bullish candle
            (body_size >= (df['high'] - df['low']) * 0.95) &  # Large body
            (upper_shadow <= (df['high'] - df['low']) * 0.01) &  # Very small upper shadow
            (lower_shadow <= (df['high'] - df['low']) * 0.01)  # Very small lower shadow
        )

        df['bearish_marubozu'] = (
            (df['close'] < df['open']) &  # Bearish candle
            (body_size >= (df['high'] - df['low']) * 0.95) &  # Large body
            (upper_shadow <= (df['high'] - df['low']) * 0.01) &  # Very small upper shadow
            (lower_shadow <= (df['high'] - df['low']) * 0.01)  # Very small lower shadow
        )

        return df

    def detect_engulfing(self, df):
        """
        Detect Bullish and Bearish Engulfing patterns.
        An engulfing pattern occurs when a candle completely engulfs the body of the previous candle.

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with engulfing pattern columns added.
        """
        # Initialize columns
        df['bullish_engulfing'] = False
        df['bearish_engulfing'] = False

        # We need at least 2 candles to detect engulfing patterns
        if len(df) < 2:
            return df

        # Loop through the dataframe starting from the second candle
        for i in range(1, len(df)):
            # Current candle
            curr_open = df['open'].iloc[i]
            curr_close = df['close'].iloc[i]
            curr_body_size = abs(curr_close - curr_open)

            # Previous candle
            prev_open = df['open'].iloc[i-1]
            prev_close = df['close'].iloc[i-1]
            prev_body_size = abs(prev_close - prev_open)

            # Bullish Engulfing: current candle is bullish and engulfs previous bearish candle
            if (curr_close > curr_open and  # Current candle is bullish
                prev_close < prev_open and  # Previous candle is bearish
                curr_open <= prev_close and  # Current open is below or equal to previous close
                curr_close >= prev_open and  # Current close is above or equal to previous open
                curr_body_size > prev_body_size):  # Current body is larger than previous body
                df['bullish_engulfing'].iloc[i] = True

            # Bearish Engulfing: current candle is bearish and engulfs previous bullish candle
            elif (curr_close < curr_open and  # Current candle is bearish
                  prev_close > prev_open and  # Previous candle is bullish
                  curr_open >= prev_close and  # Current open is above or equal to previous close
                  curr_close <= prev_open and  # Current close is below or equal to previous open
                  curr_body_size > prev_body_size):  # Current body is larger than previous body
                df['bearish_engulfing'].iloc[i] = True

        return df

    def detect_harami(self, df):
        """
        Detect Bullish and Bearish Harami patterns.
        A harami pattern occurs when a small candle is contained within the body of the previous larger candle.

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with harami pattern columns added.
        """
        # Initialize columns
        df['bullish_harami'] = False
        df['bearish_harami'] = False

        # We need at least 2 candles to detect harami patterns
        if len(df) < 2:
            return df

        # Loop through the dataframe starting from the second candle
        for i in range(1, len(df)):
            # Current candle
            curr_open = df['open'].iloc[i]
            curr_close = df['close'].iloc[i]
            curr_body_size = abs(curr_close - curr_open)

            # Previous candle
            prev_open = df['open'].iloc[i-1]
            prev_close = df['close'].iloc[i-1]
            prev_body_size = abs(prev_close - prev_open)

            # Bullish Harami: small bullish candle inside previous large bearish candle
            if (curr_close > curr_open and  # Current candle is bullish
                prev_close < prev_open and  # Previous candle is bearish
                curr_open > prev_close and  # Current open is above previous close
                curr_close < prev_open and  # Current close is below previous open
                curr_body_size < prev_body_size * 0.6):  # Current body is smaller than previous body
                df['bullish_harami'].iloc[i] = True

            # Bearish Harami: small bearish candle inside previous large bullish candle
            elif (curr_close < curr_open and  # Current candle is bearish
                  prev_close > prev_open and  # Previous candle is bullish
                  curr_open < prev_close and  # Current open is below previous close
                  curr_close > prev_open and  # Current close is above previous open
                  curr_body_size < prev_body_size * 0.6):  # Current body is smaller than previous body
                df['bearish_harami'].iloc[i] = True

        return df

    def detect_tweezer(self, df):
        """
        Detect Tweezer Top and Bottom patterns.
        Tweezer patterns occur when two consecutive candles have the same high (top) or low (bottom).

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with tweezer pattern columns added.
        """
        # Initialize columns
        df['tweezer_top'] = False
        df['tweezer_bottom'] = False

        # We need at least 2 candles to detect tweezer patterns
        if len(df) < 2:
            return df

        # Loop through the dataframe starting from the second candle
        for i in range(1, len(df)):
            # Check for Tweezer Top: two candles with same high, first bullish, second bearish
            if (abs(df['high'].iloc[i] - df['high'].iloc[i-1]) / df['high'].iloc[i] < 0.001 and  # Same high (within 0.1%)
                df['close'].iloc[i-1] > df['open'].iloc[i-1] and  # First candle is bullish
                df['close'].iloc[i] < df['open'].iloc[i]):  # Second candle is bearish
                df['tweezer_top'].iloc[i] = True

            # Check for Tweezer Bottom: two candles with same low, first bearish, second bullish
            if (abs(df['low'].iloc[i] - df['low'].iloc[i-1]) / df['low'].iloc[i] < 0.001 and  # Same low (within 0.1%)
                df['close'].iloc[i-1] < df['open'].iloc[i-1] and  # First candle is bearish
                df['close'].iloc[i] > df['open'].iloc[i]):  # Second candle is bullish
                df['tweezer_bottom'].iloc[i] = True

        return df

    def detect_morning_star(self, df):
        """
        Detect Morning Star pattern.
        A morning star is a bullish reversal pattern consisting of three candles:
        1. A large bearish candle
        2. A small-bodied candle (star) that gaps down
        3. A large bullish candle that gaps up and closes above the midpoint of the first candle

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with morning_star pattern column added.
        """
        # Initialize column
        df['morning_star'] = False

        # We need at least 3 candles to detect morning star patterns
        if len(df) < 3:
            return df

        # Loop through the dataframe starting from the third candle
        for i in range(2, len(df)):
            # First candle (bearish)
            first_open = df['open'].iloc[i-2]
            first_close = df['close'].iloc[i-2]
            first_body_size = abs(first_close - first_open)

            # Second candle (star)
            second_open = df['open'].iloc[i-1]
            second_close = df['close'].iloc[i-1]
            second_body_size = abs(second_close - second_open)

            # Third candle (bullish)
            third_open = df['open'].iloc[i]
            third_close = df['close'].iloc[i]
            third_body_size = abs(third_close - third_open)

            # Morning Star criteria
            if (first_close < first_open and  # First candle is bearish
                second_body_size < first_body_size * 0.3 and  # Second candle has a small body
                third_close > third_open and  # Third candle is bullish
                third_body_size > second_body_size * 2 and  # Third candle has a large body
                third_close > (first_open + first_close) / 2):  # Third candle closes above midpoint of first candle
                df['morning_star'].iloc[i] = True

        return df

    def detect_evening_star(self, df):
        """
        Detect Evening Star pattern.
        An evening star is a bearish reversal pattern consisting of three candles:
        1. A large bullish candle
        2. A small-bodied candle (star) that gaps up
        3. A large bearish candle that gaps down and closes below the midpoint of the first candle

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with evening_star pattern column added.
        """
        # Initialize column
        df['evening_star'] = False

        # We need at least 3 candles to detect evening star patterns
        if len(df) < 3:
            return df

        # Loop through the dataframe starting from the third candle
        for i in range(2, len(df)):
            # First candle (bullish)
            first_open = df['open'].iloc[i-2]
            first_close = df['close'].iloc[i-2]
            first_body_size = abs(first_close - first_open)

            # Second candle (star)
            second_open = df['open'].iloc[i-1]
            second_close = df['close'].iloc[i-1]
            second_body_size = abs(second_close - second_open)

            # Third candle (bearish)
            third_open = df['open'].iloc[i]
            third_close = df['close'].iloc[i]
            third_body_size = abs(third_close - third_open)

            # Evening Star criteria
            if (first_close > first_open and  # First candle is bullish
                second_body_size < first_body_size * 0.3 and  # Second candle has a small body
                third_close < third_open and  # Third candle is bearish
                third_body_size > second_body_size * 2 and  # Third candle has a large body
                third_close < (first_open + first_close) / 2):  # Third candle closes below midpoint of first candle
                df['evening_star'].iloc[i] = True

        return df

    def detect_three_white_soldiers(self, df):
        """
        Detect Three White Soldiers pattern.
        Three consecutive bullish candles, each closing higher than the previous.

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with three_white_soldiers pattern column added.
        """
        # Initialize column
        df['three_white_soldiers'] = False

        # We need at least 3 candles to detect three white soldiers patterns
        if len(df) < 3:
            return df

        # Loop through the dataframe starting from the third candle
        for i in range(2, len(df)):
            # Check if we have three consecutive bullish candles
            if (df['close'].iloc[i-2] > df['open'].iloc[i-2] and  # First candle is bullish
                df['close'].iloc[i-1] > df['open'].iloc[i-1] and  # Second candle is bullish
                df['close'].iloc[i] > df['open'].iloc[i] and  # Third candle is bullish
                df['close'].iloc[i] > df['close'].iloc[i-1] > df['close'].iloc[i-2] and  # Each closes higher than previous
                df['open'].iloc[i] > df['open'].iloc[i-1] > df['open'].iloc[i-2]):  # Each opens higher than previous
                df['three_white_soldiers'].iloc[i] = True

        return df

    def detect_three_black_crows(self, df):
        """
        Detect Three Black Crows pattern.
        Three consecutive bearish candles, each closing lower than the previous.

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with three_black_crows pattern column added.
        """
        # Initialize column
        df['three_black_crows'] = False

        # We need at least 3 candles to detect three black crows patterns
        if len(df) < 3:
            return df

        # Loop through the dataframe starting from the third candle
        for i in range(2, len(df)):
            # Check if we have three consecutive bearish candles
            if (df['close'].iloc[i-2] < df['open'].iloc[i-2] and  # First candle is bearish
                df['close'].iloc[i-1] < df['open'].iloc[i-1] and  # Second candle is bearish
                df['close'].iloc[i] < df['open'].iloc[i] and  # Third candle is bearish
                df['close'].iloc[i] < df['close'].iloc[i-1] < df['close'].iloc[i-2] and  # Each closes lower than previous
                df['open'].iloc[i] < df['open'].iloc[i-1] < df['open'].iloc[i-2]):  # Each opens lower than previous
                df['three_black_crows'].iloc[i] = True

        return df

    def detect_head_and_shoulders(self, df):
        """
        Detect Head and Shoulders pattern.
        A bearish reversal pattern consisting of three peaks, with the middle peak (head)
        being higher than the two surrounding peaks (shoulders).

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with head_and_shoulders pattern column added.
        """
        # Initialize column
        df['head_and_shoulders'] = False

        # We need at least 7 candles to detect head and shoulders patterns
        # (left shoulder + head + right shoulder with valleys in between)
        if len(df) < 7:
            return df

        # Use a rolling window to detect the pattern
        window_size = 7  # Minimum size for a basic H&S pattern

        for i in range(window_size - 1, len(df)):
            # Extract the window
            window = df.iloc[i-(window_size-1):i+1]

            # Find local maxima (peaks) in the window
            # A point is a peak if it's higher than its neighbors
            highs = window['high'].values
            peaks = []

            for j in range(1, len(highs) - 1):
                if highs[j] > highs[j-1] and highs[j] > highs[j+1]:
                    peaks.append((j, highs[j]))

            # We need at least 3 peaks for H&S pattern
            if len(peaks) >= 3:
                # Sort peaks by height
                peaks.sort(key=lambda x: x[1], reverse=True)

                # The highest peak is the head
                head_idx, head_value = peaks[0]

                # Find potential shoulders (should be lower than the head)
                potential_shoulders = [(idx, val) for idx, val in peaks[1:] if val < head_value]

                # We need at least 2 shoulders
                if len(potential_shoulders) >= 2:
                    # Sort potential shoulders by index to find left and right shoulders
                    potential_shoulders.sort(key=lambda x: x[0])

                    # Check if we have shoulders on both sides of the head
                    left_shoulders = [(idx, val) for idx, val in potential_shoulders if idx < head_idx]
                    right_shoulders = [(idx, val) for idx, val in potential_shoulders if idx > head_idx]

                    if left_shoulders and right_shoulders:
                        # Take the highest peak on each side as the shoulders
                        left_shoulder = max(left_shoulders, key=lambda x: x[1])
                        right_shoulder = max(right_shoulders, key=lambda x: x[1])

                        # Check if shoulders are at similar heights (within threshold)
                        shoulder_height_diff = abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1]
                        if shoulder_height_diff <= self.hs_shoulder_diff_threshold:
                            # Find the neckline (connecting the troughs between shoulders and head)
                            left_trough_idx = min(range(left_shoulder[0], head_idx), key=lambda x: window['low'].iloc[x])
                            right_trough_idx = min(range(head_idx, right_shoulder[0]), key=lambda x: window['low'].iloc[x])

                            left_trough = window['low'].iloc[left_trough_idx]
                            right_trough = window['low'].iloc[right_trough_idx]

                            # Check if troughs are at similar levels (neckline should be relatively flat)
                            trough_diff = abs(left_trough - right_trough) / left_trough
                            if trough_diff <= 0.05:  # Troughs within 5% of each other
                                # Pattern confirmed at the last candle in the window
                                df['head_and_shoulders'].iloc[i] = True

        return df

    def detect_inverse_head_and_shoulders(self, df):
        """
        Detect Inverse Head and Shoulders pattern.
        A bullish reversal pattern consisting of three troughs, with the middle trough (head)
        being lower than the two surrounding troughs (shoulders).

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with inverse_head_and_shoulders pattern column added.
        """
        # Initialize column
        df['inverse_head_and_shoulders'] = False

        # We need at least 7 candles to detect inverse head and shoulders patterns
        if len(df) < 7:
            return df

        # Use a rolling window to detect the pattern
        window_size = 7  # Minimum size for a basic IH&S pattern

        for i in range(window_size - 1, len(df)):
            # Extract the window
            window = df.iloc[i-(window_size-1):i+1]

            # Find local minima (troughs) in the window
            # A point is a trough if it's lower than its neighbors
            lows = window['low'].values
            troughs = []

            for j in range(1, len(lows) - 1):
                if lows[j] < lows[j-1] and lows[j] < lows[j+1]:
                    troughs.append((j, lows[j]))

            # We need at least 3 troughs for IH&S pattern
            if len(troughs) >= 3:
                # Sort troughs by depth (lowest first)
                troughs.sort(key=lambda x: x[1])

                # The lowest trough is the head
                head_idx, head_value = troughs[0]

                # Find potential shoulders (should be higher than the head)
                potential_shoulders = [(idx, val) for idx, val in troughs[1:] if val > head_value]

                # We need at least 2 shoulders
                if len(potential_shoulders) >= 2:
                    # Sort potential shoulders by index to find left and right shoulders
                    potential_shoulders.sort(key=lambda x: x[0])

                    # Check if we have shoulders on both sides of the head
                    left_shoulders = [(idx, val) for idx, val in potential_shoulders if idx < head_idx]
                    right_shoulders = [(idx, val) for idx, val in potential_shoulders if idx > head_idx]

                    if left_shoulders and right_shoulders:
                        # Take the lowest trough on each side as the shoulders
                        left_shoulder = min(left_shoulders, key=lambda x: x[1])
                        right_shoulder = min(right_shoulders, key=lambda x: x[1])

                        # Check if shoulders are at similar heights (within threshold)
                        shoulder_height_diff = abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1]
                        if shoulder_height_diff <= self.hs_shoulder_diff_threshold:
                            # Find the neckline (connecting the peaks between shoulders and head)
                            left_peak_idx = max(range(left_shoulder[0], head_idx), key=lambda x: window['high'].iloc[x])
                            right_peak_idx = max(range(head_idx, right_shoulder[0]), key=lambda x: window['high'].iloc[x])

                            left_peak = window['high'].iloc[left_peak_idx]
                            right_peak = window['high'].iloc[right_peak_idx]

                            # Check if peaks are at similar levels (neckline should be relatively flat)
                            peak_diff = abs(left_peak - right_peak) / left_peak
                            if peak_diff <= 0.05:  # Peaks within 5% of each other
                                # Pattern confirmed at the last candle in the window
                                df['inverse_head_and_shoulders'].iloc[i] = True

        return df

    def detect_double_top(self, df):
        """
        Detect Double Top pattern.
        A bearish reversal pattern consisting of two peaks at approximately the same price level,
        with a moderate trough in between.

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with double_top pattern column added.
        """
        # Initialize column
        df['double_top'] = False

        # We need at least 5 candles to detect double top patterns
        if len(df) < 5:
            return df

        # Use a rolling window to detect the pattern
        window_size = 5  # Minimum size for a basic double top pattern

        for i in range(window_size - 1, len(df)):
            # Extract the window
            window = df.iloc[i-(window_size-1):i+1]

            # Find local maxima (peaks) in the window
            highs = window['high'].values
            peaks = []

            for j in range(1, len(highs) - 1):
                if highs[j] > highs[j-1] and highs[j] > highs[j+1]:
                    peaks.append((j, highs[j]))

            # We need at least 2 peaks for double top pattern
            if len(peaks) >= 2:
                # Sort peaks by index
                peaks.sort(key=lambda x: x[0])

                # Check if the two highest peaks are at similar levels
                if len(peaks) >= 2:
                    # Get the two highest peaks
                    sorted_by_height = sorted(peaks, key=lambda x: x[1], reverse=True)[:2]
                    peak1_idx, peak1_val = sorted_by_height[0]
                    peak2_idx, peak2_val = sorted_by_height[1]

                    # Ensure they're in chronological order
                    if peak1_idx > peak2_idx:
                        peak1_idx, peak2_idx = peak2_idx, peak1_idx
                        peak1_val, peak2_val = peak2_val, peak1_val

                    # Check if peaks are at similar heights (within threshold)
                    peak_height_diff = abs(peak1_val - peak2_val) / peak1_val
                    if peak_height_diff <= self.double_pattern_level_threshold:
                        # Find the trough between the peaks
                        trough_idx = min(range(peak1_idx, peak2_idx), key=lambda x: window['low'].iloc[x])
                        trough_val = window['low'].iloc[trough_idx]

                        # Check if the trough is significantly lower than the peaks (at least 3%)
                        trough_depth = (peak1_val - trough_val) / peak1_val
                        if trough_depth >= 0.03:
                            # Check if the price has started to decline after the second peak
                            if peak2_idx < len(window) - 1 and window['close'].iloc[-1] < window['close'].iloc[peak2_idx]:
                                # Pattern confirmed at the last candle in the window
                                df['double_top'].iloc[i] = True

        return df

    def detect_double_bottom(self, df):
        """
        Detect Double Bottom pattern.
        A bullish reversal pattern consisting of two troughs at approximately the same price level,
        with a moderate peak in between.

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with double_bottom pattern column added.
        """
        # Initialize column
        df['double_bottom'] = False

        # We need at least 5 candles to detect double bottom patterns
        if len(df) < 5:
            return df

        # Use a rolling window to detect the pattern
        window_size = 5  # Minimum size for a basic double bottom pattern

        for i in range(window_size - 1, len(df)):
            # Extract the window
            window = df.iloc[i-(window_size-1):i+1]

            # Find local minima (troughs) in the window
            lows = window['low'].values
            troughs = []

            for j in range(1, len(lows) - 1):
                if lows[j] < lows[j-1] and lows[j] < lows[j+1]:
                    troughs.append((j, lows[j]))

            # We need at least 2 troughs for double bottom pattern
            if len(troughs) >= 2:
                # Sort troughs by index
                troughs.sort(key=lambda x: x[0])

                # Check if the two lowest troughs are at similar levels
                if len(troughs) >= 2:
                    # Get the two lowest troughs
                    sorted_by_depth = sorted(troughs, key=lambda x: x[1])[:2]
                    trough1_idx, trough1_val = sorted_by_depth[0]
                    trough2_idx, trough2_val = sorted_by_depth[1]

                    # Ensure they're in chronological order
                    if trough1_idx > trough2_idx:
                        trough1_idx, trough2_idx = trough2_idx, trough1_idx
                        trough1_val, trough2_val = trough2_val, trough1_val

                    # Check if troughs are at similar depths (within threshold)
                    trough_depth_diff = abs(trough1_val - trough2_val) / trough1_val
                    if trough_depth_diff <= self.double_pattern_level_threshold:
                        # Find the peak between the troughs
                        peak_idx = max(range(trough1_idx, trough2_idx), key=lambda x: window['high'].iloc[x])
                        peak_val = window['high'].iloc[peak_idx]

                        # Check if the peak is significantly higher than the troughs (at least 3%)
                        peak_height = (peak_val - trough1_val) / trough1_val
                        if peak_height >= 0.03:
                            # Check if the price has started to rise after the second trough
                            if trough2_idx < len(window) - 1 and window['close'].iloc[-1] > window['close'].iloc[trough2_idx]:
                                # Pattern confirmed at the last candle in the window
                                df['double_bottom'].iloc[i] = True

        return df

    def calculate_pattern_strength(self, df):
        """
        Calculate the overall pattern strength for bullish and bearish signals.

        Args:
            df (pandas.DataFrame): Price data with pattern columns.

        Returns:
            pandas.DataFrame: DataFrame with pattern_strength columns added.
        """
        # Initialize strength columns
        df['bullish_pattern_strength'] = 0
        df['bearish_pattern_strength'] = 0

        # Define pattern weights
        pattern_weights = {
            # Bullish patterns
            'hammer': 1,
            'bullish_engulfing': 2,
            'bullish_harami': 1,
            'tweezer_bottom': 1,
            'morning_star': 3,
            'three_white_soldiers': 3,
            'bullish_marubozu': 2,
            'inverse_head_and_shoulders': 4,  # Complex pattern, higher weight
            'double_bottom': 4,  # Complex pattern, higher weight

            # Bearish patterns
            'shooting_star': 1,
            'inverted_hammer': 1,
            'bearish_engulfing': 2,
            'bearish_harami': 1,
            'tweezer_top': 1,
            'evening_star': 3,
            'three_black_crows': 3,
            'bearish_marubozu': 2,
            'head_and_shoulders': 4,  # Complex pattern, higher weight
            'double_top': 4  # Complex pattern, higher weight
        }

        # Calculate bullish pattern strength
        bullish_patterns = ['hammer', 'bullish_engulfing', 'bullish_harami',
                           'tweezer_bottom', 'morning_star', 'three_white_soldiers',
                           'bullish_marubozu', 'inverse_head_and_shoulders', 'double_bottom']

        for pattern in bullish_patterns:
            if pattern in df.columns:
                df['bullish_pattern_strength'] += df[pattern].astype(int) * pattern_weights[pattern]

        # Calculate bearish pattern strength
        bearish_patterns = ['shooting_star', 'inverted_hammer', 'bearish_engulfing',
                           'bearish_harami', 'tweezer_top', 'evening_star',
                           'three_black_crows', 'bearish_marubozu', 'head_and_shoulders', 'double_top']

        for pattern in bearish_patterns:
            if pattern in df.columns:
                df['bearish_pattern_strength'] += df[pattern].astype(int) * pattern_weights[pattern]

        return df
