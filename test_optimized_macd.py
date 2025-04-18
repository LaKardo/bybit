"""
Test script for optimized MACD calculation.
This script tests the performance and accuracy of the optimized MACD calculation.
"""

import time
import pandas as pd
import numpy as np
import traceback
import config
from bybit_client import BybitAPIClient
from logger import Logger

def test_macd_performance():
    """Test MACD calculation performance."""
    print("\nTesting MACD calculation performance...")
    
    try:
        # Initialize logger
        logger = Logger(log_file="logs/test_optimized_macd.log", log_level="DEBUG")
        
        # Initialize client
        client = BybitAPIClient(logger=logger)
        
        # Get historical data
        symbol = config.SYMBOL
        interval = config.TIMEFRAME
        
        # Get klines data
        klines = client.get_klines(symbol, interval)
        if klines is None or klines.empty:
            print("✗ Failed to get historical data")
            return
            
        print(f"✓ Successfully retrieved {len(klines)} klines")
        
        # Test standard MACD calculation
        start_time = time.time()
        standard_df = client.calculate_macd(klines.copy())
        standard_time = time.time() - start_time
        
        print(f"✓ Standard MACD calculation completed in {standard_time:.4f} seconds")
        
        # Test optimized MACD calculation with force_recalculate=True
        start_time = time.time()
        optimized_df = client.calculate_macd(klines.copy(), force_recalculate=True)
        optimized_time = time.time() - start_time
        
        print(f"✓ Optimized MACD calculation completed in {optimized_time:.4f} seconds")
        print(f"  Performance improvement: {(standard_time - optimized_time) / standard_time * 100:.2f}%")
        
        # Verify results are the same
        macd_diff = np.abs(standard_df['macd'] - optimized_df['macd']).mean()
        signal_diff = np.abs(standard_df['macd_signal'] - optimized_df['macd_signal']).mean()
        hist_diff = np.abs(standard_df['macd_hist'] - optimized_df['macd_hist']).mean()
        
        print(f"✓ Average difference in MACD values: {macd_diff:.8f}")
        print(f"✓ Average difference in Signal values: {signal_diff:.8f}")
        print(f"✓ Average difference in Histogram values: {hist_diff:.8f}")
        
        # Test incremental update
        # First, get MACD data
        client.get_macd_data(symbol, interval, force_recalculate=True)
        
        # Now test incremental update with the last candle
        last_candle = klines.iloc[-1].to_dict()
        
        start_time = time.time()
        updated_df = client.update_macd_with_new_data(symbol, interval, last_candle)
        incremental_time = time.time() - start_time
        
        print(f"✓ Incremental MACD update completed in {incremental_time:.4f} seconds")
        print(f"  Performance improvement vs standard: {(standard_time - incremental_time) / standard_time * 100:.2f}%")
        
        # Verify incremental update results
        if updated_df is not None and not updated_df.empty:
            inc_macd_diff = np.abs(standard_df['macd'].iloc[-1] - updated_df['macd'].iloc[-1])
            inc_signal_diff = np.abs(standard_df['macd_signal'].iloc[-1] - updated_df['macd_signal'].iloc[-1])
            inc_hist_diff = np.abs(standard_df['macd_hist'].iloc[-1] - updated_df['macd_hist'].iloc[-1])
            
            print(f"✓ Difference in last MACD value: {inc_macd_diff:.8f}")
            print(f"✓ Difference in last Signal value: {inc_signal_diff:.8f}")
            print(f"✓ Difference in last Histogram value: {inc_hist_diff:.8f}")
        else:
            print("✗ Failed to get incremental update results")
        
    except Exception as e:
        print(f"✗ Error testing MACD performance: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

def test_realtime_macd_calculation():
    """Test real-time MACD calculation with WebSocket data."""
    print("\nTesting real-time MACD calculation...")
    
    try:
        # Initialize logger
        logger = Logger(log_file="logs/test_optimized_macd.log", log_level="DEBUG")
        
        # Initialize client
        client = BybitAPIClient(logger=logger)
        
        # Start WebSocket
        if not client.start_websocket():
            print("✗ Failed to start WebSocket")
            return
            
        print("✓ WebSocket started successfully")
        
        # Subscribe to kline data
        symbol = config.SYMBOL
        interval = config.TIMEFRAME
        
        if not client.subscribe_kline(symbol, interval):
            print(f"✗ Failed to subscribe to kline data for {symbol} ({interval})")
            return
            
        print(f"✓ Successfully subscribed to kline data for {symbol} ({interval})")
        
        # Wait for data to be received and MACD to be calculated
        print("Waiting for data to be received and MACD to be calculated (10 seconds)...")
        time.sleep(10)
        
        # Get MACD data
        start_time = time.time()
        macd_data = client.get_macd_data(symbol, interval)
        retrieval_time = time.time() - start_time
        
        if macd_data is not None and not macd_data.empty:
            print(f"✓ Successfully retrieved MACD data with {len(macd_data)} rows in {retrieval_time:.4f} seconds")
            
            # Check if MACD columns exist
            if 'macd' in macd_data.columns and 'macd_signal' in macd_data.columns and 'macd_hist' in macd_data.columns:
                print("✓ MACD columns exist in the data")
                
                # Print last row of MACD data
                print("\nLast row of MACD data:")
                last_row = macd_data.iloc[-1]
                print(f"Time: {last_row['timestamp']}")
                print(f"Close: {last_row['close']}")
                print(f"MACD: {last_row['macd']}")
                print(f"MACD Signal: {last_row['macd_signal']}")
                print(f"MACD Hist: {last_row['macd_hist']}")
            else:
                print("✗ MACD columns do not exist in the data")
                print(f"Available columns: {macd_data.columns.tolist()}")
        else:
            print("✗ Failed to get MACD data")
            
        # Test incremental update performance
        print("\nTesting incremental update performance...")
        
        # Wait for more data
        print("Waiting for more data (5 seconds)...")
        time.sleep(5)
        
        # Test incremental update
        start_time = time.time()
        updated_df = client.update_macd_with_new_data(symbol, interval)
        incremental_time = time.time() - start_time
        
        if updated_df is not None and not updated_df.empty:
            print(f"✓ Successfully updated MACD data incrementally in {incremental_time:.4f} seconds")
            
            # Print last row of updated MACD data
            print("\nLast row of updated MACD data:")
            last_row = updated_df.iloc[-1]
            print(f"Time: {last_row['timestamp']}")
            print(f"Close: {last_row['close']}")
            print(f"MACD: {last_row['macd']}")
            print(f"MACD Signal: {last_row['macd_signal']}")
            print(f"MACD Hist: {last_row['macd_hist']}")
        else:
            print("✗ Failed to update MACD data incrementally")
            
        # Stop WebSocket
        client.stop_websocket()
        print("✓ WebSocket stopped successfully")
        
    except Exception as e:
        print(f"✗ Error testing real-time MACD calculation: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

if __name__ == "__main__":
    print("=" * 50)
    print("OPTIMIZED MACD CALCULATION TEST")
    print("=" * 50)
    
    # Test MACD calculation performance
    test_macd_performance()
    
    # Test real-time MACD calculation
    test_realtime_macd_calculation()
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED")
    print("=" * 50)
