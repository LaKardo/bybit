"""
Test script for Bybit API connection.
This script tests the connection to Bybit API and fetches historical data.
"""

import time
import pandas as pd
from pybit.unified_trading import HTTP
import config
import traceback

def test_api_connection(use_auth=True):
    """Test the connection to Bybit API."""
    print(f"Testing connection to Bybit API (auth: {use_auth})")

    try:
        # Initialize client
        if use_auth:
            print(f"API Key: {config.API_KEY[:5]}...{config.API_KEY[-5:]}")
            client = HTTP(
                testnet=False,  # Always use mainnet
                api_key=config.API_KEY,
                api_secret=config.API_SECRET
            )
        else:
            print("Using public API (no authentication)")
            client = HTTP(
                testnet=False  # Always use mainnet
            )

        # Test server time
        server_time = client.get_server_time()
        print(f"Server time: {server_time}")
        print("Connection successful!")
        return client
    except Exception as e:
        print(f"Connection failed: {e}")
        print(f"Detailed error: {traceback.format_exc()}")
        return None

def test_get_klines(client):
    """Test fetching historical klines data."""
    if not client:
        print("Cannot test get_klines: No client connection")
        return

    print(f"\nTesting get_klines for {config.SYMBOL} on {config.TIMEFRAME} timeframe")

    try:
        # Calculate start and end time (last 30 days)
        import time
        end_time = int(time.time() * 1000)  # Current time in milliseconds
        start_time = end_time - (30 * 24 * 60 * 60 * 1000)  # 30 days ago

        print(f"Start time: {start_time}, End time: {end_time}")

        # Get klines
        response = client.get_kline(
            category="linear",
            symbol=config.SYMBOL,
            interval=config.TIMEFRAME,
            start=start_time,
            end=end_time,
            limit=100
        )

        # Check response
        if response.get("retCode") == 0:
            print("API call successful")
            print(f"Full response: {response}")
            result = response.get("result")

            if not result or "list" not in result:
                print("No data in response")
                return

            # Convert to DataFrame
            df = pd.DataFrame(result["list"], columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "turnover", "confirm"
            ])

            # Print data summary
            print(f"Received {len(df)} klines")

            if len(df) > 0:
                print(f"First timestamp: {pd.to_datetime(int(df.iloc[0]['timestamp']), unit='ms')}")
                print(f"Last timestamp: {pd.to_datetime(int(df.iloc[-1]['timestamp']), unit='ms')}")

                # Print first few rows
                print("\nFirst 3 rows:")
                for i in range(min(3, len(df))):
                    row = df.iloc[i]
                    print(f"Time: {pd.to_datetime(int(row['timestamp']), unit='ms')}, Open: {row['open']}, Close: {row['close']}")
            else:
                print("No data points received from API. Empty response.")
        else:
            print(f"API call failed: {response.get('retMsg')}")
            print(f"Full response: {response}")
    except Exception as e:
        print(f"Error fetching klines: {e}")
        print(f"Detailed error: {traceback.format_exc()}")

def test_alternative_timeframes(client):
    """Test fetching data with different timeframes."""
    if not client:
        print("Cannot test alternative timeframes: No client connection")
        return

    timeframes = ["5m", "15m", "30m", "1h", "4h", "1d"]

    print("\nTesting alternative timeframes")

    # Calculate start and end time (last 30 days)
    import time
    end_time = int(time.time() * 1000)  # Current time in milliseconds
    start_time = end_time - (30 * 24 * 60 * 60 * 1000)  # 30 days ago

    for tf in timeframes:
        print(f"\nTesting timeframe: {tf}")
        try:
            # Get klines
            response = client.get_kline(
                category="linear",
                symbol=config.SYMBOL,
                interval=tf,
                start=start_time,
                end=end_time,
                limit=10
            )

            # Check response
            if response.get("retCode") == 0:
                result = response.get("result")
                if result and "list" in result:
                    print(f"✓ Successfully fetched {len(result['list'])} klines for {tf}")
                else:
                    print(f"✗ No data in response for {tf}")
            else:
                print(f"✗ API call failed for {tf}: {response.get('retMsg')}")
        except Exception as e:
            print(f"✗ Error fetching {tf} klines: {e}")

def test_alternative_symbols(client):
    """Test fetching data with different symbols."""
    if not client:
        print("Cannot test alternative symbols: No client connection")
        return

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

    print("\nTesting alternative symbols")

    # Calculate start and end time (last 30 days)
    import time
    end_time = int(time.time() * 1000)  # Current time in milliseconds
    start_time = end_time - (30 * 24 * 60 * 60 * 1000)  # 30 days ago

    for symbol in symbols:
        print(f"\nTesting symbol: {symbol}")
        try:
            # Get klines
            response = client.get_kline(
                category="linear",
                symbol=symbol,
                interval=config.TIMEFRAME,
                start=start_time,
                end=end_time,
                limit=10
            )

            # Check response
            if response.get("retCode") == 0:
                result = response.get("result")
                if result and "list" in result:
                    print(f"✓ Successfully fetched {len(result['list'])} klines for {symbol}")
                else:
                    print(f"✗ No data in response for {symbol}")
            else:
                print(f"✗ API call failed for {symbol}: {response.get('retMsg')}")
        except Exception as e:
            print(f"✗ Error fetching {symbol} klines: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("BYBIT API CONNECTION TEST")
    print("=" * 50)

    # Test with public API (no authentication)
    print("\n" + "=" * 50)
    print("TESTING WITH PUBLIC API (MAINNET)")
    print("=" * 50)

    # Test API connection with public API
    public_client = test_api_connection(use_auth=False)

    if public_client:
        # Test get_klines
        test_get_klines(public_client)

    # Test with authenticated API
    print("\n" + "=" * 50)
    print("TESTING WITH AUTHENTICATED API (MAINNET)")
    print("=" * 50)

    # Test API connection with authentication
    mainnet_client = test_api_connection(use_auth=True)

    if mainnet_client:
        # Test get_klines
        test_get_klines(mainnet_client)

        # Test alternative timeframes
        test_alternative_timeframes(mainnet_client)

        # Test alternative symbols
        test_alternative_symbols(mainnet_client)

    print("\n" + "=" * 50)
    print("TEST COMPLETED")
    print("=" * 50)
