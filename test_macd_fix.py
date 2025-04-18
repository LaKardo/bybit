"""
Test script for MACD calculation fix.
This script tests the changes made to fix the "not enough data for MACD calculation" error.
"""

import time
import pandas as pd
import traceback
import config
from bybit_client import BybitAPIClient
from logger import Logger

def test_macd_fix():
    """Test MACD calculation fix."""
    print("\nTesting MACD calculation fix...")
    
    try:
        # Initialize logger
        logger = Logger(log_file="logs/test_macd_fix.log", log_level="DEBUG")
        
        # Initialize client
        client = BybitAPIClient(logger=logger)
        
        # Test connection
        if not client.test_connection():
            print("✗ Failed to connect to Bybit API")
            return None
            
        print("✓ Connected to Bybit API successfully")
        
        # Define test parameters
        symbol = config.SYMBOL
        timeframes = ["1", "5", "15", "60", "240", "D"]  # Test different timeframes
        
        # Test each timeframe
        for interval in timeframes:
            print(f"\nTesting timeframe: {interval}")
            
            # Get klines with default parameters (should automatically use enough data for MACD)
            print(f"Getting klines for {symbol} ({interval}) with default parameters...")
            klines = client.get_klines(symbol, interval)
            
            if klines is None or klines.empty:
                print(f"✗ Failed to get klines for {symbol} ({interval})")
                continue
                
            print(f"✓ Successfully retrieved {len(klines)} klines")
            
            # Calculate MACD
            print("Calculating MACD...")
            df_with_macd = client.calculate_macd(klines.copy())
            
            # Check if MACD columns exist
            if 'macd' in df_with_macd.columns and 'macd_signal' in df_with_macd.columns and 'macd_hist' in df_with_macd.columns:
                print("✓ MACD columns exist in the data")
                
                # Check if we have valid MACD values (not all zeros)
                if df_with_macd['macd'].abs().sum() > 0 and df_with_macd['macd_signal'].abs().sum() > 0:
                    print("✓ MACD values are valid (not all zeros)")
                else:
                    print("✗ MACD values are all zeros, which may indicate insufficient data")
                
                # Print last few rows of MACD data
                print("\nLast 3 rows of MACD data:")
                last_rows = df_with_macd.tail(3)
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
                print(f"Available columns: {df_with_macd.columns.tolist()}")
            
            # Test with limited data (should handle gracefully)
            print("\nTesting with limited data (only 10 rows)...")
            limited_klines = klines.head(10).copy()
            print(f"Limited data size: {len(limited_klines)} rows")
            
            # Calculate MACD on limited data
            limited_df_with_macd = client.calculate_macd(limited_klines)
            
            # Check if MACD columns exist
            if 'macd' in limited_df_with_macd.columns and 'macd_signal' in limited_df_with_macd.columns and 'macd_hist' in limited_df_with_macd.columns:
                print("✓ MACD columns exist in the limited data (default values should be used)")
                
                # Print last row of limited MACD data
                print("\nLast row of limited MACD data:")
                last_row = limited_df_with_macd.iloc[-1]
                print(f"MACD: {last_row['macd']}")
                print(f"MACD Signal: {last_row['macd_signal']}")
                print(f"MACD Hist: {last_row['macd_hist']}")
            else:
                print("✗ MACD columns do not exist in the limited data")
            
            # Test get_macd_data method
            print("\nTesting get_macd_data method...")
            macd_data = client.get_macd_data(symbol, interval)
            
            if macd_data is not None and not macd_data.empty:
                print(f"✓ Successfully retrieved MACD data with {len(macd_data)} rows")
                
                # Check if MACD columns exist
                if 'macd' in macd_data.columns and 'macd_signal' in macd_data.columns and 'macd_hist' in macd_data.columns:
                    print("✓ MACD columns exist in the data")
                    
                    # Check if we have valid MACD values (not all zeros)
                    if macd_data['macd'].abs().sum() > 0 and macd_data['macd_signal'].abs().sum() > 0:
                        print("✓ MACD values are valid (not all zeros)")
                    else:
                        print("✗ MACD values are all zeros, which may indicate insufficient data")
                else:
                    print("✗ MACD columns do not exist in the data")
            else:
                print("✗ Failed to get MACD data")
            
            # Test update_macd_with_new_data method
            print("\nTesting update_macd_with_new_data method...")
            updated_macd_data = client.update_macd_with_new_data(symbol, interval)
            
            if updated_macd_data is not None and not updated_macd_data.empty:
                print(f"✓ Successfully updated MACD data with {len(updated_macd_data)} rows")
                
                # Check if MACD columns exist
                if 'macd' in updated_macd_data.columns and 'macd_signal' in updated_macd_data.columns and 'macd_hist' in updated_macd_data.columns:
                    print("✓ MACD columns exist in the updated data")
                    
                    # Check if we have valid MACD values (not all zeros)
                    if updated_macd_data['macd'].abs().sum() > 0 and updated_macd_data['macd_signal'].abs().sum() > 0:
                        print("✓ MACD values are valid (not all zeros)")
                    else:
                        print("✗ MACD values are all zeros, which may indicate insufficient data")
                else:
                    print("✗ MACD columns do not exist in the updated data")
            else:
                print("✗ Failed to update MACD data")
        
    except Exception as e:
        print(f"✗ Error testing MACD calculation fix: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

if __name__ == "__main__":
    print("=" * 50)
    print("MACD CALCULATION FIX TEST")
    print("=" * 50)
    
    # Test MACD calculation fix
    test_macd_fix()
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED")
    print("=" * 50)
