"""
Unit tests for the Pattern Recognition module.
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from pattern_recognition import PatternRecognition

class TestPatternRecognition(unittest.TestCase):
    """
    Test cases for the Pattern Recognition module.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock logger
        self.mock_logger = MagicMock()
        
        # Create a pattern recognition instance with the mock logger
        self.pattern_recognition = PatternRecognition(logger=self.mock_logger)
        
        # Create a sample DataFrame with OHLCV data
        self.df = pd.DataFrame({
            'timestamp': pd.date_range(start='2023-01-01', periods=10, freq='1h'),
            'open': [100, 105, 110, 115, 120, 125, 120, 115, 110, 105],
            'high': [110, 115, 120, 125, 130, 135, 130, 125, 120, 115],
            'low': [95, 100, 105, 110, 115, 120, 115, 110, 105, 100],
            'close': [105, 110, 115, 120, 125, 120, 115, 110, 105, 100],
            'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1400, 1300, 1200, 1100]
        })
    
    def test_detect_patterns_empty_df(self):
        """Test detect_patterns method with empty DataFrame."""
        # Call the method with an empty DataFrame
        result = self.pattern_recognition.detect_patterns(pd.DataFrame())
        
        # Check that the logger.error method was called
        self.mock_logger.error.assert_called_once_with("Cannot detect patterns: No data provided")
        
        # Check that the result is an empty DataFrame
        self.assertTrue(result.empty)
    
    def test_detect_patterns(self):
        """Test detect_patterns method."""
        # Call the method
        result = self.pattern_recognition.detect_patterns(self.df)
        
        # Check that the result is a DataFrame
        self.assertIsInstance(result, pd.DataFrame)
        
        # Check that the result has the same number of rows as the input
        self.assertEqual(len(result), len(self.df))
        
        # Check that the result has the pattern columns
        pattern_columns = [
            'doji', 'hammer', 'inverted_hammer', 'shooting_star',
            'bullish_marubozu', 'bearish_marubozu', 'bullish_engulfing',
            'bearish_engulfing', 'bullish_harami', 'bearish_harami',
            'tweezer_top', 'tweezer_bottom', 'morning_star', 'evening_star',
            'three_white_soldiers', 'three_black_crows', 'head_and_shoulders',
            'inverse_head_and_shoulders', 'double_top', 'double_bottom',
            'bullish_pattern_strength', 'bearish_pattern_strength'
        ]
        for column in pattern_columns:
            self.assertIn(column, result.columns)
    
    def test_detect_doji(self):
        """Test detect_doji method."""
        # Create a DataFrame with a doji pattern
        df = pd.DataFrame({
            'open': [100],
            'high': [110],
            'low': [90],
            'close': [100.5]
        })
        
        # Call the method
        result = self.pattern_recognition.detect_doji(df)
        
        # Check that the result has the doji column
        self.assertIn('doji', result.columns)
        
        # Check that the doji pattern was detected
        self.assertTrue(result['doji'].iloc[0])
    
    def test_detect_hammer(self):
        """Test detect_hammer method."""
        # Create a DataFrame with a hammer pattern
        df = pd.DataFrame({
            'open': [100],
            'high': [105],
            'low': [80],
            'close': [102]
        })
        
        # Call the method
        result = self.pattern_recognition.detect_hammer(df)
        
        # Check that the result has the hammer column
        self.assertIn('hammer', result.columns)
        self.assertIn('inverted_hammer', result.columns)
    
    def test_detect_engulfing(self):
        """Test detect_engulfing method."""
        # Create a DataFrame with a bullish engulfing pattern
        df = pd.DataFrame({
            'open': [100, 95],
            'high': [105, 105],
            'low': [95, 90],
            'close': [98, 105]
        })
        
        # Call the method
        result = self.pattern_recognition.detect_engulfing(df)
        
        # Check that the result has the engulfing columns
        self.assertIn('bullish_engulfing', result.columns)
        self.assertIn('bearish_engulfing', result.columns)
        
        # Check that the bullish engulfing pattern was detected
        self.assertTrue(result['bullish_engulfing'].iloc[1])
    
    def test_calculate_pattern_strength(self):
        """Test calculate_pattern_strength method."""
        # Create a DataFrame with some patterns
        df = pd.DataFrame({
            'bullish_engulfing': [False, True, False],
            'bearish_engulfing': [True, False, False],
            'hammer': [False, False, True],
            'shooting_star': [False, True, False]
        })
        
        # Call the method
        result = self.pattern_recognition.calculate_pattern_strength(df)
        
        # Check that the result has the pattern strength columns
        self.assertIn('bullish_pattern_strength', result.columns)
        self.assertIn('bearish_pattern_strength', result.columns)
        
        # Check the pattern strength values
        self.assertEqual(result['bullish_pattern_strength'].iloc[0], 0)
        self.assertEqual(result['bearish_pattern_strength'].iloc[0], 2)
        self.assertEqual(result['bullish_pattern_strength'].iloc[1], 2)
        self.assertEqual(result['bearish_pattern_strength'].iloc[1], 1)
        self.assertEqual(result['bullish_pattern_strength'].iloc[2], 1)
        self.assertEqual(result['bearish_pattern_strength'].iloc[2], 0)
    
    def test_error_handling(self):
        """Test error handling in detect_patterns method."""
        # Create a mock DataFrame that will cause an error
        df = pd.DataFrame({
            'open': [100],
            'high': [110],
            'low': [90],
            'close': [105]
        })
        
        # Mock the detect_doji method to raise an exception
        self.pattern_recognition.detect_doji = MagicMock(side_effect=Exception("Test error"))
        
        # Call the method
        result = self.pattern_recognition.detect_patterns(df)
        
        # Check that the logger.error method was called
        self.mock_logger.error.assert_called_with("Failed to detect patterns: Test error")
        
        # Check that the result is the original DataFrame
        self.assertEqual(len(result), len(df))
        
        # Check that the pattern strength columns were initialized
        self.assertIn('bullish_pattern_strength', result.columns)
        self.assertIn('bearish_pattern_strength', result.columns)
        self.assertEqual(result['bullish_pattern_strength'].iloc[0], 0)
        self.assertEqual(result['bearish_pattern_strength'].iloc[0], 0)

if __name__ == '__main__':
    unittest.main()
