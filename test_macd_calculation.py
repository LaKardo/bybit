"""
Test script for automatic MACD calculation after receiving new data from Bybit.
"""

import time
import pandas as pd
import traceback
import config
from bybit_client import BybitAPIClient
from logger import Logger

def test_macd_calculation():
    """Test automatic MACD calculation."""
    print("\nTesting automatic MACD calculation...")
    
    try:
        # Initialize logger
        logger = Logger(log_file="logs/test_macd_calculation.log", log_level="DEBUG")
        
        # Initialize client
        client = BybitAPIClient(logger=logger)
        
        # Start WebSocket
        if not client.start_websocket():
            print("✗ Failed to start WebSocket")
            return None
            
        print("✓ WebSocket started successfully")
        
        # Subscribe to kline data
        symbol = config.SYMBOL
        interval = config.TIMEFRAME
        
        if not client.subscribe_kline(symbol, interval):
            print(f"✗ Failed to subscribe to kline data for {symbol} ({interval})")
            return None
            
        print(f"✓ Successfully subscribed to kline data for {symbol} ({interval})")
        
        # Wait for data to be received and MACD to be calculated
        print("Waiting for data to be received and MACD to be calculated (10 seconds)...")
        time.sleep(10)
        
        # Get MACD data
        macd_data = client.get_macd_data(symbol, interval)
        
        if macd_data is not None and not macd_data.empty:
            print(f"✓ Successfully retrieved MACD data with {len(macd_data)} rows")
            
            # Check if MACD columns exist
            if 'macd' in macd_data.columns and 'macd_signal' in macd_data.columns and 'macd_hist' in macd_data.columns:
                print("✓ MACD columns exist in the data")
                
                # Print last few rows of MACD data
                print("\nLast 3 rows of MACD data:")
                last_rows = macd_data.tail(3)
                for i in range(len(last_rows)):
                    row = last_rows.iloc[i]
                    print(f"Time: {row['timestamp']}")
                    print(f"Close: {row['close']}")
                    print(f"MACD: {row['macd']}")
                    print(f"MACD Signal: {row['macd_signal']}")
                    print(f"MACD Hist: {row['macd_hist']}")
                    print("---")
            else:
                print("✗ MACD columns do not exist in the data")
                print(f"Available columns: {macd_data.columns.tolist()}")
        else:
            print("✗ Failed to get MACD data")
            
        # Wait for more data to be received
        print("\nWaiting for more data to be received (10 seconds)...")
        time.sleep(10)
        
        # Get updated MACD data
        updated_macd_data = client.get_macd_data(symbol, interval)
        
        if updated_macd_data is not None and not updated_macd_data.empty:
            print(f"✓ Successfully retrieved updated MACD data with {len(updated_macd_data)} rows")
            
            # Check if data has been updated
            if len(updated_macd_data) >= len(macd_data):
                print("✓ MACD data has been updated")
                
                # Print last row of updated MACD data
                print("\nLast row of updated MACD data:")
                last_row = updated_macd_data.iloc[-1]
                print(f"Time: {last_row['timestamp']}")
                print(f"Close: {last_row['close']}")
                print(f"MACD: {last_row['macd']}")
                print(f"MACD Signal: {last_row['macd_signal']}")
                print(f"MACD Hist: {last_row['macd_hist']}")
            else:
                print("✗ MACD data has not been updated")
        else:
            print("✗ Failed to get updated MACD data")
            
        # Stop WebSocket
        client.stop_websocket()
        print("✓ WebSocket stopped successfully")
        
    except Exception as e:
        print(f"✗ Error testing automatic MACD calculation: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

if __name__ == "__main__":
    print("=" * 50)
    print("AUTOMATIC MACD CALCULATION TEST")
    print("=" * 50)
    
    # Test automatic MACD calculation
    test_macd_calculation()
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED")
    print("=" * 50)
