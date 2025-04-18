"""
Test script for WebSocket functionality in the Bybit API client.
This script tests the WebSocket methods for real-time data streaming.
"""

import time
import pandas as pd
import traceback
import config
from bybit_client import BybitAPIClient
from logger import Logger

def test_websocket_initialization():
    """Test WebSocket initialization."""
    print("Testing WebSocket initialization...")
    
    try:
        # Initialize logger
        logger = Logger(log_file="logs/test_websocket.log", log_level="DEBUG")
        
        # Initialize client
        client = BybitAPIClient(logger=logger)
        
        # Start WebSocket
        if client.start_websocket():
            print("✓ WebSocket initialized successfully")
        else:
            print("✗ Failed to initialize WebSocket")
            return None, None
        
        return client, logger
    except Exception as e:
        print(f"✗ Error initializing WebSocket: {e}")
        print(f"Detailed error: {traceback.format_exc()}")
        return None, None

def test_kline_subscription(client, logger):
    """Test kline subscription."""
    print("\nTesting kline subscription...")
    
    try:
        # Subscribe to kline data
        if client.subscribe_kline(symbol=config.SYMBOL, interval=config.TIMEFRAME):
            print(f"✓ Successfully subscribed to kline data for {config.SYMBOL} ({config.TIMEFRAME})")
        else:
            print(f"✗ Failed to subscribe to kline data for {config.SYMBOL} ({config.TIMEFRAME})")
            return
        
        # Wait for data to be received
        print("Waiting for data to be received (5 seconds)...")
        time.sleep(5)
        
        # Get real-time kline data
        klines = client.get_realtime_kline(symbol=config.SYMBOL, interval=config.TIMEFRAME)
        
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
    except Exception as e:
        print(f"✗ Error testing kline subscription: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

def test_ticker_subscription(client, logger):
    """Test ticker subscription."""
    print("\nTesting ticker subscription...")
    
    try:
        # Subscribe to ticker data
        if client.subscribe_ticker(symbol=config.SYMBOL):
            print(f"✓ Successfully subscribed to ticker data for {config.SYMBOL}")
        else:
            print(f"✗ Failed to subscribe to ticker data for {config.SYMBOL}")
            return
        
        # Wait for data to be received
        print("Waiting for data to be received (5 seconds)...")
        time.sleep(5)
        
        # Get ticker data
        ticker = client.get_ticker(config.SYMBOL)
        
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
    except Exception as e:
        print(f"✗ Error testing ticker subscription: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

def test_unsubscribe(client, logger):
    """Test unsubscribe functionality."""
    print("\nTesting unsubscribe functionality...")
    
    try:
        # Unsubscribe from kline data
        topic = f"kline.{config.TIMEFRAME}.{config.SYMBOL}"
        if client.unsubscribe_topic(topic):
            print(f"✓ Successfully unsubscribed from {topic}")
        else:
            print(f"✗ Failed to unsubscribe from {topic}")
        
        # Unsubscribe from ticker data
        topic = f"tickers.{config.SYMBOL}"
        if client.unsubscribe_topic(topic):
            print(f"✓ Successfully unsubscribed from {topic}")
        else:
            print(f"✗ Failed to unsubscribe from {topic}")
    except Exception as e:
        print(f"✗ Error testing unsubscribe functionality: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

def test_stop_websocket(client, logger):
    """Test stopping WebSocket."""
    print("\nTesting stopping WebSocket...")
    
    try:
        # Stop WebSocket
        if client.stop_websocket():
            print("✓ Successfully stopped WebSocket")
        else:
            print("✗ Failed to stop WebSocket")
    except Exception as e:
        print(f"✗ Error stopping WebSocket: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

if __name__ == "__main__":
    print("=" * 50)
    print("WEBSOCKET FUNCTIONALITY TEST")
    print("=" * 50)
    
    # Test WebSocket initialization
    client, logger = test_websocket_initialization()
    
    if client and logger:
        # Test kline subscription
        test_kline_subscription(client, logger)
        
        # Test ticker subscription
        test_ticker_subscription(client, logger)
        
        # Test unsubscribe functionality
        test_unsubscribe(client, logger)
        
        # Test stopping WebSocket
        test_stop_websocket(client, logger)
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED")
    print("=" * 50)
