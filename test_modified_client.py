"""
Test script for the modified Bybit API client.
This script tests the get_klines method of the modified BybitAPIClient.
"""

import pandas as pd
from bybit_client import BybitAPIClient
import config

def main():
    """Test the modified BybitAPIClient."""
    print("=" * 50)
    print("TESTING MODIFIED BYBIT API CLIENT")
    print("=" * 50)

    # Print configuration
    print(f"Symbol: {config.SYMBOL}")
    print(f"Timeframe: {config.TIMEFRAME}")
    print(f"API Key: {config.API_KEY[:5]}...{config.API_KEY[-5:] if len(config.API_KEY) > 10 else ''}")
    print(f"Dry Run: {config.DRY_RUN}")

    # Setup logging
    import logging
    logging.basicConfig(level=logging.DEBUG,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('test_client')

    # Initialize client with logger
    client = BybitAPIClient(logger=logger)
    print("Initialized client (using mainnet)")

    # Test get_klines
    print("\nTesting get_klines for main timeframe...")
    klines = client.get_klines(
        symbol=config.SYMBOL,
        interval=config.TIMEFRAME,
        limit=100
    )

    if klines is not None and not klines.empty:
        print(f"Successfully retrieved {len(klines)} klines")
        print(f"First timestamp: {klines.iloc[0]['timestamp']}")
        print(f"Last timestamp: {klines.iloc[-1]['timestamp']}")

        # Print first few rows
        print("\nFirst 3 rows:")
        for i in range(min(3, len(klines))):
            row = klines.iloc[i]
            print(f"Time: {row['timestamp']}, Open: {row['open']}, Close: {row['close']}")
    else:
        print("Failed to retrieve klines")

    # Test get_klines for confirmation timeframes
    if config.MULTI_TIMEFRAME_ENABLED:
        print("\nTesting get_klines for confirmation timeframes...")
        for tf in config.CONFIRMATION_TIMEFRAMES:
            print(f"\nTimeframe: {tf}")
            tf_klines = client.get_klines(
                symbol=config.SYMBOL,
                interval=tf,
                limit=100
            )

            if tf_klines is not None and not tf_klines.empty:
                print(f"Successfully retrieved {len(tf_klines)} klines")
                print(f"First timestamp: {tf_klines.iloc[0]['timestamp']}")
                print(f"Last timestamp: {tf_klines.iloc[-1]['timestamp']}")
            else:
                print("Failed to retrieve klines")

    print("\n" + "=" * 50)
    print("TEST COMPLETED")
    print("=" * 50)

if __name__ == "__main__":
    main()
