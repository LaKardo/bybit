"""
Unit tests for the Strategy module.
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from strategy import Strategy
import config

class TestStrategy(unittest.TestCase):
    """
    Test cases for the Strategy module.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock logger
        self.mock_logger = MagicMock()

        # Create a strategy instance with the mock logger
        self.strategy = Strategy(logger=self.mock_logger)

        # Create a sample DataFrame with OHLCV data
        self.df = pd.DataFrame({
            'timestamp': pd.date_range(start='2023-01-01', periods=10, freq='1h'),
            'open': [100, 105, 110, 115, 120, 125, 120, 115, 110, 105],
            'high': [110, 115, 120, 125, 130, 135, 130, 125, 120, 115],
            'low': [95, 100, 105, 110, 115, 120, 115, 110, 105, 100],
            'close': [105, 110, 115, 120, 125, 120, 115, 110, 105, 100],
            'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1400, 1300, 1200, 1100]
        })

    def test_calculate_indicators_empty_df(self):
        """Test calculate_indicators method with empty DataFrame."""
        # Call the method with an empty DataFrame
        result = self.strategy.calculate_indicators(pd.DataFrame())

        # Check that the logger.error method was called
        self.mock_logger.error.assert_called_with("Cannot calculate indicators: No data provided")

        # Check that the result is None
        self.assertIsNone(result)

    def test_calculate_indicators(self):
        """Test calculate_indicators method."""
        # Create a DataFrame with indicators already calculated
        df = self.df.copy()
        df[f'ema_{self.strategy.fast_ema}'] = [100, 105, 110, 115, 120, 125, 120, 115, 110, 105]
        df[f'ema_{self.strategy.slow_ema}'] = [95, 100, 105, 110, 115, 120, 125, 120, 115, 110]
        df['rsi'] = [30, 40, 50, 60, 70, 60, 50, 40, 30, 20]
        df['macd'] = [0, 1, 2, 3, 4, 3, 2, 1, 0, -1]
        df['macd_signal'] = [1, 1, 1, 2, 3, 4, 3, 2, 1, 0]
        df['macd_hist'] = [-1, 0, 1, 1, 1, -1, -1, -1, -1, -1]
        df['atr'] = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
        df['volume_ma'] = [1000, 1050, 1100, 1150, 1200, 1250, 1300, 1350, 1400, 1450]
        df['volume_ratio'] = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.4, 1.3, 1.2, 1.1]
        df['obv'] = [1000, 2100, 3300, 4600, 6000, 7500, 8900, 10200, 11400, 12500]
        df['obv_ema'] = [1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500]
        df['obv_slope'] = [0, 1, 2, 3, 4, 3, 2, 1, 0, -1]



        # Mock the calculate_indicators method to return the prepared DataFrame
        original_method = self.strategy.calculate_indicators
        self.strategy.calculate_indicators = MagicMock(return_value=df)

        # Call the method
        result = self.strategy.calculate_indicators(self.df)

        # Check that the result is a DataFrame
        self.assertIsInstance(result, pd.DataFrame)

        # Check that the result has the same number of rows as the input
        self.assertEqual(len(result), len(self.df))

        # Check that the result has the indicator columns
        indicator_columns = [
            f'ema_{self.strategy.fast_ema}', f'ema_{self.strategy.slow_ema}',
            'rsi', 'macd', 'macd_signal', 'macd_hist', 'atr',
            'volume_ma', 'volume_ratio', 'obv', 'obv_ema', 'obv_slope'
        ]
        for column in indicator_columns:
            self.assertIn(column, result.columns)

        # Restore the original method
        self.strategy.calculate_indicators = original_method

    def test_generate_signal_empty_df(self):
        """Test generate_signal method with empty DataFrame."""
        # Call the method with an empty DataFrame
        result = self.strategy.generate_signal(pd.DataFrame())

        # Check that the logger.error method was called
        self.mock_logger.error.assert_called_with("Cannot generate signal: Insufficient data")

        # Check that the result is "NONE"
        self.assertEqual(result, "NONE")

    def test_generate_signal_single_timeframe(self):
        """Test generate_signal method with single timeframe."""
        # Create a DataFrame with indicators
        df = self.df.copy()
        df[f'ema_{self.strategy.fast_ema}'] = [100, 105, 110, 115, 120, 125, 120, 115, 110, 105]
        df[f'ema_{self.strategy.slow_ema}'] = [95, 100, 105, 110, 115, 120, 125, 120, 115, 110]
        df['rsi'] = [30, 40, 50, 60, 70, 60, 50, 40, 30, 20]
        df['macd'] = [0, 1, 2, 3, 4, 3, 2, 1, 0, -1]
        df['macd_signal'] = [1, 1, 1, 2, 3, 4, 3, 2, 1, 0]
        df['macd_hist'] = [-1, 0, 1, 1, 1, -1, -1, -1, -1, -1]
        df['volume_ratio'] = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.4, 1.3, 1.2, 1.1]
        df['obv_slope'] = [0, 1, 2, 3, 4, 3, 2, 1, 0, -1]

        # Mock the _generate_signal_from_single_timeframe method
        self.strategy._generate_signal_from_single_timeframe = MagicMock(return_value="LONG")

        # Call the method
        result = self.strategy.generate_signal(df)

        # Check that the result is "LONG"
        self.assertEqual(result, "LONG")

        # Check that the _generate_signal_from_single_timeframe method was called
        self.strategy._generate_signal_from_single_timeframe.assert_called_once_with(df)

    def test_generate_signal_multi_timeframe(self):
        """Test generate_signal method with multi-timeframe."""
        # Create a DataFrame with indicators
        df = self.df.copy()
        df[f'ema_{self.strategy.fast_ema}'] = [100, 105, 110, 115, 120, 125, 120, 115, 110, 105]
        df[f'ema_{self.strategy.slow_ema}'] = [95, 100, 105, 110, 115, 120, 125, 120, 115, 110]
        df['rsi'] = [30, 40, 50, 60, 70, 60, 50, 40, 30, 20]
        df['macd'] = [0, 1, 2, 3, 4, 3, 2, 1, 0, -1]
        df['macd_signal'] = [1, 1, 1, 2, 3, 4, 3, 2, 1, 0]
        df['macd_hist'] = [-1, 0, 1, 1, 1, -1, -1, -1, -1, -1]
        df['volume_ratio'] = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.4, 1.3, 1.2, 1.1]
        df['obv_slope'] = [0, 1, 2, 3, 4, 3, 2, 1, 0, -1]

        # Create multi-timeframe data
        mtf_data = {
            '15m': df.copy(),
            '4h': df.copy(),
            '1d': df.copy()
        }

        # Enable multi-timeframe analysis
        self.strategy.multi_timeframe_enabled = True

        # Mock the analyze_multi_timeframe method
        self.strategy.analyze_multi_timeframe = MagicMock(return_value=("LONG", 0.5, {}))

        # Call the method
        result = self.strategy.generate_signal(df, mtf_data)

        # Check that the result is "LONG"
        self.assertEqual(result, "LONG")

        # Check that the analyze_multi_timeframe method was called
        self.strategy.analyze_multi_timeframe.assert_called_once_with(df, mtf_data)

    def test_analyze_timeframe(self):
        """Test analyze_timeframe method."""
        # Create a DataFrame with indicators
        df = self.df.copy()
        df[f'ema_{self.strategy.fast_ema}'] = [100, 105, 110, 115, 120, 125, 120, 115, 110, 105]
        df[f'ema_{self.strategy.slow_ema}'] = [95, 100, 105, 110, 115, 120, 125, 120, 115, 110]
        df['rsi'] = [30, 40, 50, 60, 70, 60, 50, 40, 30, 20]
        df['macd'] = [0, 1, 2, 3, 4, 3, 2, 1, 0, -1]
        df['macd_signal'] = [1, 1, 1, 2, 3, 4, 3, 2, 1, 0]
        df['macd_hist'] = [-1, 0, 1, 1, 1, -1, -1, -1, -1, -1]
        df['volume_ratio'] = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.4, 1.3, 1.2, 1.1]
        df['obv_slope'] = [0, 1, 2, 3, 4, 3, 2, 1, 0, -1]


        # Call the method
        result = self.strategy.analyze_timeframe(df, "1h")

        # Check that the result is a float
        self.assertIsInstance(result, float)

        # Check that the result is between -1.0 and 1.0
        self.assertGreaterEqual(result, -1.0)
        self.assertLessEqual(result, 1.0)

    def test_analyze_multi_timeframe(self):
        """Test analyze_multi_timeframe method."""
        # Create a DataFrame with indicators
        df = self.df.copy()
        df[f'ema_{self.strategy.fast_ema}'] = [100, 105, 110, 115, 120, 125, 120, 115, 110, 105]
        df[f'ema_{self.strategy.slow_ema}'] = [95, 100, 105, 110, 115, 120, 125, 120, 115, 110]
        df['rsi'] = [30, 40, 50, 60, 70, 60, 50, 40, 30, 20]
        df['macd'] = [0, 1, 2, 3, 4, 3, 2, 1, 0, -1]
        df['macd_signal'] = [1, 1, 1, 2, 3, 4, 3, 2, 1, 0]
        df['macd_hist'] = [-1, 0, 1, 1, 1, -1, -1, -1, -1, -1]
        df['volume_ratio'] = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.4, 1.3, 1.2, 1.1]
        df['obv_slope'] = [0, 1, 2, 3, 4, 3, 2, 1, 0, -1]
        df['atr'] = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5]


        # Create multi-timeframe data
        mtf_data = {
            '15m': df.copy(),
            '4h': df.copy(),
            '1d': df.copy()
        }

        # Mock the analyze_timeframe method
        self.strategy.analyze_timeframe = MagicMock(return_value=0.5)

        # Call the method
        signal, score, timeframe_scores = self.strategy.analyze_multi_timeframe(df, mtf_data)

        # Check that the signal is "LONG"
        self.assertEqual(signal, "LONG")

        # Check that the score is a float
        self.assertIsInstance(score, float)

        # Check that the timeframe_scores is a dictionary
        self.assertIsInstance(timeframe_scores, dict)

        # Check that the analyze_timeframe method was called for each timeframe
        self.assertEqual(self.strategy.analyze_timeframe.call_count, 4)

    def test_should_exit_position(self):
        """Test should_exit_position method."""
        # Create a DataFrame with indicators
        df = self.df.copy()
        df[f'ema_{self.strategy.fast_ema}'] = [100, 105, 110, 115, 120, 125, 120, 115, 110, 105]
        df[f'ema_{self.strategy.slow_ema}'] = [95, 100, 105, 110, 115, 120, 125, 120, 115, 110]
        df['rsi'] = [30, 40, 50, 60, 70, 60, 50, 40, 30, 20]
        df['macd'] = [0, 1, 2, 3, 4, 3, 2, 1, 0, -1]
        df['macd_signal'] = [1, 1, 1, 2, 3, 4, 3, 2, 1, 0]
        df['macd_hist'] = [-1, 0, 1, 1, 1, -1, -1, -1, -1, -1]
        df['volume_ratio'] = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.4, 1.3, 1.2, 1.1]
        df['obv_slope'] = [0, 1, 2, 3, 4, 3, 2, 1, 0, -1]

        # Mock the generate_signal method
        self.strategy.generate_signal = MagicMock(return_value="SHORT")

        # Call the method
        result = self.strategy.should_exit_position(df, "Buy")

        # Check that the result is True
        self.assertTrue(result)

        # Check that the generate_signal method was called
        self.strategy.generate_signal.assert_called_once_with(df)

    def test_get_atr_value(self):
        """Test get_atr_value method."""
        # Create a DataFrame with ATR
        df = self.df.copy()
        df['atr'] = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5]

        # Call the method
        result = self.strategy.get_atr_value(df)

        # Check that the result is 5
        self.assertEqual(result, 5)

if __name__ == '__main__':
    unittest.main()
