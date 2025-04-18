"""
Test script for the updated Bybit API client.
This script tests the updated methods in the BybitAPIClient class.
"""

import time
import pandas as pd
import traceback
import config
from bybit_client import BybitAPIClient
from logger import Logger

def test_client_initialization():
    """Test client initialization."""
    print("Testing client initialization...")
    
    try:
        # Initialize logger
        logger = Logger(log_file="logs/test_client.log", log_level="DEBUG")
        
        # Initialize client
        client = BybitAPIClient(logger=logger)
        
        print("✓ Client initialized successfully")
        return client, logger
    except Exception as e:
        print(f"✗ Error initializing client: {e}")
        print(f"Detailed error: {traceback.format_exc()}")
        return None, None

def test_get_klines(client, logger):
    """Test get_klines method."""
    print("\nTesting get_klines method...")
    
    try:
        # Get klines
        klines = client.get_klines(
            symbol=config.SYMBOL,
            interval=config.TIMEFRAME,
            limit=100
        )
        
        if klines is not None and not klines.empty:
            print(f"✓ Successfully retrieved {len(klines)} klines")
            print(f"First timestamp: {klines.iloc[0]['timestamp']}")
            print(f"Last timestamp: {klines.iloc[-1]['timestamp']}")
            
            # Print first few rows
            print("\nFirst 3 rows:")
            for i in range(min(3, len(klines))):
                row = klines.iloc[i]
                print(f"Time: {row['timestamp']}, Open: {row['open']}, Close: {row['close']}")
        else:
            print("✗ Failed to get klines")
    except Exception as e:
        print(f"✗ Error testing get_klines: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

def test_get_ticker(client, logger):
    """Test get_ticker method."""
    print("\nTesting get_ticker method...")
    
    try:
        # Get ticker
        ticker = client.get_ticker(config.SYMBOL)
        
        if ticker is not None:
            print("✓ Successfully retrieved ticker")
            print(f"Symbol: {ticker['symbol']}")
            print(f"Last price: {ticker['lastPrice']}")
            print(f"Mark price: {ticker['markPrice']}")
            print(f"24h high: {ticker['highPrice24h']}")
            print(f"24h low: {ticker['lowPrice24h']}")
            print(f"24h volume: {ticker['volume24h']}")
        else:
            print("✗ Failed to get ticker")
    except Exception as e:
        print(f"✗ Error testing get_ticker: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

def test_get_positions(client, logger):
    """Test get_positions method."""
    print("\nTesting get_positions method...")
    
    try:
        # Get positions
        positions = client.get_positions(config.SYMBOL)
        
        if positions is not None:
            print("✓ Successfully retrieved positions")
            if positions:
                print(f"Found {len(positions)} positions")
                for pos in positions:
                    print(f"Symbol: {pos['symbol']}, Side: {pos['side']}, Size: {pos['size']}")
            else:
                print("No open positions found")
        else:
            print("✗ Failed to get positions")
    except Exception as e:
        print(f"✗ Error testing get_positions: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

def test_get_wallet_balance(client, logger):
    """Test get_wallet_balance method."""
    print("\nTesting get_wallet_balance method...")
    
    try:
        # Get wallet balance
        balance = client.get_wallet_balance()
        
        if balance is not None:
            print("✓ Successfully retrieved wallet balance")
            print(f"Available balance: {balance['available_balance']}")
            print(f"Wallet balance: {balance['wallet_balance']}")
            print(f"Unrealized PnL: {balance['unrealized_pnl']}")
        else:
            print("✗ Failed to get wallet balance")
    except Exception as e:
        print(f"✗ Error testing get_wallet_balance: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

def test_get_account_info(client, logger):
    """Test get_account_info method."""
    print("\nTesting get_account_info method...")
    
    try:
        # Get account info
        account_info = client.get_account_info()
        
        if account_info is not None:
            print("✓ Successfully retrieved account info")
            print(f"Account type: {account_info.get('unifiedMarginStatus')}")
            print(f"Account mode: {account_info.get('marginMode')}")
        else:
            print("✗ Failed to get account info")
    except Exception as e:
        print(f"✗ Error testing get_account_info: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

if __name__ == "__main__":
    print("=" * 50)
    print("UPDATED BYBIT API CLIENT TEST")
    print("=" * 50)
    
    # Test client initialization
    client, logger = test_client_initialization()
    
    if client and logger:
        # Test methods
        test_get_klines(client, logger)
        test_get_ticker(client, logger)
        test_get_positions(client, logger)
        test_get_wallet_balance(client, logger)
        test_get_account_info(client, logger)
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED")
    print("=" * 50)
