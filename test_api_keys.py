"""
Test script for verifying Bybit API keys.
This script tests if your API keys are correctly configured and have the necessary permissions.
"""

import os
import time
import dotenv
from pybit.unified_trading import HTTP
import traceback

# Load environment variables from .env file
dotenv.load_dotenv()

# Get API keys from environment variables
API_KEY = os.getenv("BYBIT_API_KEY")
API_SECRET = os.getenv("BYBIT_API_SECRET")
print("Using API keys from .env file")

# Always use mainnet
TESTNET = False

def print_header(text):
    """Print a header with the given text."""
    print("\n" + "=" * 50)
    print(text)
    print("=" * 50)

def test_api_keys():
    """Test if the API keys are valid and have the necessary permissions."""
    print_header("TESTING BYBIT API KEYS")

    # Print API key information (partially masked for security)
    print(f"API Key: {API_KEY[:5]}...{API_KEY[-5:] if len(API_KEY) > 10 else ''}")
    print(f"API Secret: {API_SECRET[:5]}...{API_SECRET[-5:] if len(API_SECRET) > 10 else ''}")
    print("Using Bybit Mainnet")

    # Check if API keys are set
    if not API_KEY or not API_SECRET or API_KEY == "your_new_api_key_here" or API_SECRET == "your_new_api_secret_here":
        print("\n❌ ERROR: API keys are not set or are using default values.")
        print("Please update your .env file with valid API keys.")
        return False

    try:
        # Initialize client
        print("\nInitializing Bybit client...")
        client = HTTP(
            testnet=TESTNET,
            api_key=API_KEY,
            api_secret=API_SECRET
        )

        # Test 1: Get server time (doesn't require authentication)
        print("\nTest 1: Get server time (no authentication required)")
        try:
            server_time = client.get_server_time()
            print(f"✅ Success: Server time: {server_time}")
        except Exception as e:
            print(f"❌ Error: {e}")
            print(f"Detailed error: {traceback.format_exc()}")
            return False

        # Test 2: Get account information (requires authentication)
        print("\nTest 2: Get account information (authentication required)")
        try:
            account_info = client.get_account_info()
            print(f"✅ Success: Account info retrieved")
            print(f"Account type: {account_info.get('result', {}).get('unifiedMarginStatus')}")
            print(f"Account mode: {account_info.get('result', {}).get('marginMode')}")
        except Exception as e:
            print(f"❌ Error: {e}")
            print(f"Detailed error: {traceback.format_exc()}")
            print("\nThis error suggests your API keys may be invalid or don't have the necessary permissions.")
            return False

        # Test 3: Get wallet balance (requires authentication)
        print("\nTest 3: Get wallet balance (authentication required)")
        try:
            wallet_balance = client.get_wallet_balance(
                accountType="UNIFIED",
                coin="USDT"
            )
            print(f"✅ Success: Wallet balance retrieved")

            # Try to extract balance from different possible response structures
            balance = None
            result = wallet_balance.get('result', {})
            balance_list = result.get('list', [])

            if balance_list:
                for coin_data in balance_list:
                    # Check direct structure
                    if coin_data.get('coin') == 'USDT':
                        balance = coin_data.get('walletBalance')
                        break

                    # Check nested structure
                    coin_list = coin_data.get('coin', [])
                    if isinstance(coin_list, list) and coin_list:
                        for asset in coin_list:
                            if asset.get('coin') == 'USDT':
                                balance = asset.get('walletBalance')
                                break
                        if balance:
                            break

            if balance is None:
                print("⚠️ Warning: USDT balance not found in response. Response structure may have changed.")
                print(f"Response: {wallet_balance}")
                balance = "Unknown"

            print(f"USDT Balance: {balance}")
        except Exception as e:
            print(f"❌ Error: {e}")
            print(f"Detailed error: {traceback.format_exc()}")
            print("\nThis error suggests your API keys may be invalid or don't have the necessary permissions.")
            return False

        # Test 4: Get positions (requires authentication)
        print("\nTest 4: Get positions (authentication required)")
        try:
            positions = client.get_positions(
                category="linear",
                symbol="BTCUSDT"
            )
            print(f"✅ Success: Positions retrieved")
            position_list = positions.get('result', {}).get('list', [])
            if position_list:
                print(f"You have {len(position_list)} positions for BTCUSDT")
            else:
                print("No positions found for BTCUSDT")
        except Exception as e:
            print(f"❌ Error: {e}")
            print(f"Detailed error: {traceback.format_exc()}")
            print("\nThis error suggests your API keys may be invalid or don't have the necessary permissions.")
            return False

        print("\n✅ All tests passed! Your API keys are valid and have the necessary permissions.")
        return True

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print(f"Detailed error: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    test_api_keys()
