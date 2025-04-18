"""
Test script for real-time data functionality in the Bybit API client.
This script tests the real-time data methods for getting kline and ticker data.
"""

import time
import pandas as pd
import traceback
import config
from bybit_client import BybitAPIClient
from logger import Logger

def test_realtime_kline():
    """Test real-time kline data."""
    print("\nTesting real-time kline data...")
    
    try:
        # Initialize logger
        logger = Logger(log_file="logs/test_realtime_data.log", log_level="DEBUG")
        
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
        
        # Wait for data to be received
        print("Waiting for data to be received (5 seconds)...")
        time.sleep(5)
        
        # Get real-time kline data
        klines = client.get_realtime_kline(symbol, interval)
        
        if klines is not None and not klines.empty:
            print(f"✓ Successfully retrieved {len(klines)} klines")
            print(f"First timestamp: {klines.iloc[0]['timestamp']}")
            print(f"Last timestamp: {klines.iloc[-1]['timestamp']}")
            
            # Print last row (real-time candle)
            last_row = klines.iloc[-1]
            print(f"\nReal-time candle:")
            print(f"Time: {last_row['timestamp']}")
            print(f"Open: {last_row['open']}")
            print(f"High: {last_row['high']}")
            print(f"Low: {last_row['low']}")
            print(f"Close: {last_row['close']}")
            print(f"Volume: {last_row['volume']}")
            print(f"Turnover: {last_row['turnover']}")
            print(f"Confirm: {last_row['confirm']}")
        else:
            print("✗ Failed to get real-time kline data")
            
        # Stop WebSocket
        client.stop_websocket()
        print("✓ WebSocket stopped successfully")
        
    except Exception as e:
        print(f"✗ Error testing real-time kline data: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

def test_realtime_ticker():
    """Test real-time ticker data."""
    print("\nTesting real-time ticker data...")
    
    try:
        # Initialize logger
        logger = Logger(log_file="logs/test_realtime_data.log", log_level="DEBUG")
        
        # Initialize client
        client = BybitAPIClient(logger=logger)
        
        # Start WebSocket
        if not client.start_websocket():
            print("✗ Failed to start WebSocket")
            return None
            
        print("✓ WebSocket started successfully")
        
        # Subscribe to ticker data
        symbol = config.SYMBOL
        
        if not client.subscribe_ticker(symbol):
            print(f"✗ Failed to subscribe to ticker data for {symbol}")
            return None
            
        print(f"✓ Successfully subscribed to ticker data for {symbol}")
        
        # Wait for data to be received
        print("Waiting for data to be received (5 seconds)...")
        time.sleep(5)
        
        # Get ticker data
        ticker = client.get_ticker(symbol)
        
        if ticker is not None:
            print("✓ Successfully retrieved ticker data")
            print(f"Symbol: {ticker['symbol']}")
            print(f"Last price: {ticker['lastPrice']}")
            print(f"Mark price: {ticker['markPrice']}")
            print(f"24h high: {ticker['highPrice24h']}")
            print(f"24h low: {ticker['lowPrice24h']}")
            print(f"24h volume: {ticker['volume24h']}")
        else:
            print("✗ Failed to get ticker data")
            
        # Stop WebSocket
        client.stop_websocket()
        print("✓ WebSocket stopped successfully")
        
    except Exception as e:
        print(f"✗ Error testing real-time ticker data: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

if __name__ == "__main__":
    print("=" * 50)
    print("REAL-TIME DATA FUNCTIONALITY TEST")
    print("=" * 50)
    
    # Test real-time kline data
    test_realtime_kline()
    
    # Test real-time ticker data
    test_realtime_ticker()
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED")
    print("=" * 50)
