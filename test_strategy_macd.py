"""
Test script for the updated MACD calculation in the Strategy class.
"""

import time
import pandas as pd
import traceback
import config
from bybit_client import BybitAPIClient
from strategy import Strategy
from logger import Logger

def test_strategy_macd():
    """Test MACD calculation in the Strategy class."""
    print("\nTesting MACD calculation in Strategy class...")
    
    try:
        # Initialize logger
        logger = Logger(log_file="logs/test_strategy_macd.log", log_level="DEBUG")
        
        # Initialize Bybit client
        bybit_client = BybitAPIClient(logger=logger)
        
        # Initialize strategy
        strategy = Strategy(logger=logger, bybit_client=bybit_client)
        
        # Get historical data
        symbol = config.SYMBOL
        interval = config.TIMEFRAME
        
        # Get klines data
        klines = bybit_client.get_klines(symbol, interval)
        if klines is None or klines.empty:
            print("✗ Failed to get historical data")
            return
            
        print(f"✓ Successfully retrieved {len(klines)} klines")
        
        # Calculate indicators using the strategy
        start_time = time.time()
        df_with_indicators = strategy.calculate_indicators(klines)
        calculation_time = time.time() - start_time
        
        if df_with_indicators is None or df_with_indicators.empty:
            print("✗ Failed to calculate indicators")
            return
            
        print(f"✓ Successfully calculated indicators in {calculation_time:.4f} seconds")
        
        # Check if MACD columns exist
        if 'macd' in df_with_indicators.columns and 'macd_signal' in df_with_indicators.columns and 'macd_hist' in df_with_indicators.columns:
            print("✓ MACD columns exist in the data")
            
            # Print last row of MACD data
            print("\nLast row of MACD data:")
            last_row = df_with_indicators.iloc[-1]
            print(f"Time: {last_row['timestamp'] if 'timestamp' in last_row else 'N/A'}")
            print(f"Close: {last_row['close']}")
            print(f"MACD: {last_row['macd']}")
            print(f"MACD Signal: {last_row['macd_signal']}")
            print(f"MACD Hist: {last_row['macd_hist']}")
            
            # Generate signal
            signal = strategy.generate_signal(df_with_indicators)
            print(f"\nGenerated signal: {signal}")
        else:
            print("✗ MACD columns do not exist in the data")
            print(f"Available columns: {df_with_indicators.columns.tolist()}")
        
    except Exception as e:
        print(f"✗ Error testing MACD calculation in Strategy class: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

if __name__ == "__main__":
    print("=" * 50)
    print("STRATEGY MACD CALCULATION TEST")
    print("=" * 50)
    
    # Test MACD calculation in Strategy class
    test_strategy_macd()
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED")
    print("=" * 50)
