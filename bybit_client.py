"""
Bybit API client for the Trading Bot.
Handles all interactions with the Bybit API using PyBit library.

This client implements the Bybit V5 API which unifies Spot, Derivatives, and Options
trading under a single API specification. For more information, see:
https://bybit-exchange.github.io/docs/v5/intro
"""

import time
import pandas as pd
from pybit.unified_trading import HTTP, WebSocket
import config
import os
import pickle
import threading
import json
from utils import is_invalid_api_key

class BybitAPIClient:
    """
    Bybit API client for the Trading Bot.
    Handles all interactions with the Bybit API using PyBit library.
    """
    def __init__(self, api_key=None, api_secret=None, logger=None):
        """
        Initialize the Bybit API client.

        Args:
            api_key (str, optional): API key. Defaults to config.API_KEY.
            api_secret (str, optional): API secret. Defaults to config.API_SECRET.
            logger (Logger, optional): Logger instance.
        """
        self.api_key = api_key or config.API_KEY
        self.api_secret = api_secret or config.API_SECRET
        self.logger = logger

        # Initialize pybit client with V5 API - always use mainnet
        self.client = HTTP(
            testnet=False,  # Always use mainnet
            api_key=self.api_key,
            api_secret=self.api_secret,
            recv_window=5000  # Default receive window as per Bybit docs
        )

        # Import traceback here for use in _log_error method
        import traceback
        self.traceback = traceback

        # Test API connection
        if self.logger:
            self.logger.info(f"Подключение к Bybit")
            self.logger.info(f"API Key: {self.api_key[:5]}...{self.api_key[-5:] if len(self.api_key) > 10 else ''}")

        # Test the API connection
        self.test_connection()

        # Initialize cache
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        # Initialize WebSocket variables
        self.ws_client = None
        self.ws_enabled = False
        self.ws_callbacks = {}
        self.ws_data = {}
        self.ws_lock = threading.Lock()

        # Cache settings
        self.cache_enabled = True
        self.cache_expiry = 60 * 60  # 1 hour in seconds

        # WebSocket settings
        self.ws_enabled = False
        self.ws_client = None
        self.ws_callbacks = {}
        self.ws_data = {}
        self.ws_lock = threading.Lock()
        self.ws_thread = None

        if self.logger:
            self.logger.info(f"Bybit API client initialized")

    def _log_error(self, error, message):
        """
        Log error with traceback.

        Args:
            error (Exception): The exception object.
            message (str): Error message prefix.
        """
        if self.logger:
            self.logger.error(f"{message}: {error}")
            self.logger.error(f"Detailed error: {self.traceback.format_exc()}")

    def _safe_float_conversion(self, value, field_name, default=0.0):
        """
        Safely convert a value to float with proper error handling.

        Args:
            value: The value to convert to float.
            field_name (str): The name of the field (for logging).
            default (float, optional): Default value if conversion fails. Defaults to 0.0.

        Returns:
            float: The converted value or default if conversion fails.
        """
        if value is None:
            if self.logger:
                self.logger.debug(f"Field '{field_name}' is None, using default value {default}")
            return default

        try:
            # Handle empty strings
            if isinstance(value, str) and not value.strip():
                if self.logger:
                    self.logger.debug(f"Field '{field_name}' is empty string, using default value {default}")
                return default

            # Try to convert to float
            result = float(value)
            return result
        except (ValueError, TypeError) as e:
            if self.logger:
                self.logger.warning(f"Could not convert '{field_name}' value '{value}' to float: {e}. Using default value {default}")
            return default

    def _handle_response(self, response, action):
        """
        Handle API response.

        Args:
            response (dict): API response.
            action (str): Action description.

        Returns:
            dict: Response result or None on error.
        """
        if not response:
            if self.logger:
                self.logger.warning(f"Empty response from {action}")
            return None

        if response.get("retCode") == 0:
            if self.logger:
                self.logger.debug(f"API {action} successful")
            return response.get("result")
        else:
            error_msg = f"API {action} failed: {response.get('retMsg')}"
            if self.logger:
                self.logger.error(error_msg)
            return None

    def _retry_api_call(self, func, *args, **kwargs):
        """
        Retry API call with exponential backoff.

        Args:
            func (callable): Function to call.
            *args: Function arguments.
            **kwargs: Function keyword arguments.

        Returns:
            dict: API response or empty dict on error.
        """
        max_retries = config.MAX_RETRIES
        retry_delay = config.RETRY_DELAY

        # Check if we're in dry run mode and API keys are invalid
        if config.DRY_RUN and is_invalid_api_key(self.api_key, self.api_secret):
            if self.logger:
                self.logger.error("API keys are invalid. Please set valid API keys in .env file.")
            return {"retCode": -1, "retMsg": "Invalid API keys"}

        for attempt in range(max_retries):
            try:
                response = func(*args, **kwargs)

                # Check if the response indicates an authentication error
                if response and (response.get("retCode") == 401 or response.get("retCode") == 10003 or
                               "401" in str(response) or "ErrCode: 401" in str(response)):
                    if self.logger:
                        self.logger.error(f"Authentication error: {response.get('retMsg', 'Unknown error')}")
                        self.logger.error(f"Please check your API keys in config.py")
                    # Don't retry on authentication errors
                    return {"retCode": -1, "retMsg": "Authentication error. Please check your API keys."}

                return response
            except Exception as e:
                if attempt < max_retries - 1:
                    if self.logger:
                        self.logger.warning(f"API call failed, retrying in {retry_delay}s: {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    if self.logger:
                        self.logger.error(f"API call failed after {max_retries} attempts: {e}")
                        # Log more detailed error information
                        import traceback
                        self.logger.error(f"Detailed error: {traceback.format_exc()}")
                        self.logger.error(f"Function: {func.__name__}, Args: {args}, Kwargs: {kwargs}")
                    # Check if it's an authentication error
                    if "401" in str(e) or "API key is invalid" in str(e) or "ErrCode: 401" in str(e) or "Http status code is not 200" in str(e):
                        if self.logger:
                            self.logger.error(f"Authentication error: {e}")
                            self.logger.error(f"Please check your API keys in config.py")
                        return {"retCode": -1, "retMsg": "Authentication error. Please check your API keys."}
                    # Return empty dict for other errors
                    return {"retCode": -1, "retMsg": str(e)}

    def get_server_time(self):
        """
        Get the server time from Bybit.

        Returns:
            int: Server time in milliseconds or None on error.
        """
        try:
            response = self.client.get_server_time()

            if response and response.get("retCode") == 0:
                server_time = response.get("result", {}).get("timeNano")
                if server_time:
                    # Convert nanoseconds to milliseconds
                    server_time_ms = int(server_time) // 1000000
                    if self.logger:
                        self.logger.debug(f"Server time: {server_time_ms} ms")
                    return server_time_ms

            if self.logger:
                self.logger.warning(f"Failed to get server time: {response.get('retMsg', 'Unknown error')}")
            return None
        except Exception as e:
            self._log_error(e, "Error getting server time")
            return None

    def test_connection(self):
        """
        Test the API connection to Bybit.

        Returns:
            bool: True if connection is successful, False otherwise.
        """
        # If we're in dry run mode with invalid API keys, don't actually test the connection
        if config.DRY_RUN and is_invalid_api_key(self.api_key, self.api_secret):
            if self.logger:
                self.logger.info("Пропуск проверки API подключения в демо-режиме с недействительными API ключами")
            return True

        try:
            # Use a simple API call that doesn't require authentication
            server_time = self.get_server_time()

            # Try to get wallet balance to check if we have funds
            try:
                wallet_balance = self.get_wallet_balance()
                if wallet_balance:
                    balance = wallet_balance.get('wallet_balance', 0)
                    self.logger.info(f"Баланс счета: {balance} USDT")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Не удалось получить баланс счета: {str(e)}")

            if server_time is not None:
                if self.logger:
                    self.logger.info(f"API connection test successful. Server time: {server_time} ms")
                    # Check time difference between local and server time
                    local_time = int(time.time() * 1000)
                    time_diff = abs(local_time - server_time)
                    if time_diff > 1000:  # More than 1 second difference
                        self.logger.warning(f"Time difference between local and server: {time_diff} ms")
                        self.logger.warning("Large time difference may cause API authentication issues")
                return True
            else:
                if self.logger:
                    self.logger.error("API connection test failed: Could not get server time")
                    if is_invalid_api_key(self.api_key, self.api_secret):
                        self.logger.error("API keys appear to be invalid. Please set valid API keys in .env file.")
                        return False
                return False
        except Exception as e:
            self._log_error(e, "API connection test failed")

            if is_invalid_api_key(self.api_key, self.api_secret):
                if self.logger:
                    self.logger.error("API keys appear to be invalid. Please set valid API keys in .env file.")
                return False
            return False

    def _get_cache_key(self, symbol, interval, limit):
        """
        Generate a cache key for klines data.

        Args:
            symbol (str): Trading symbol.
            interval (str): Kline interval.
            limit (int): Number of klines.

        Returns:
            str: Cache key.
        """
        return f"{symbol}_{interval}_{limit}"

    def _get_cache_path(self, cache_key):
        """
        Generate a cache file path.

        Args:
            cache_key (str): Cache key.

        Returns:
            str: Cache file path.
        """
        return os.path.join(self.cache_dir, f"{cache_key}.pkl")

    def _is_cache_valid(self, cache_path):
        """
        Check if cache is valid (exists and not expired).

        Args:
            cache_path (str): Cache file path.

        Returns:
            bool: True if cache is valid, False otherwise.
        """
        if not os.path.exists(cache_path):
            return False

        # Check if cache is expired
        cache_time = os.path.getmtime(cache_path)
        current_time = time.time()
        return (current_time - cache_time) < self.cache_expiry

    def _load_from_cache(self, cache_path):
        """
        Load klines data from cache.

        Args:
            cache_path (str): Cache file path.

        Returns:
            pandas.DataFrame: Klines data or None on error.
        """
        try:
            with open(cache_path, 'rb') as f:
                df = pickle.load(f)

            if self.logger:
                self.logger.debug(f"Loaded klines data from cache: {cache_path}")

            return df
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to load from cache: {e}")
            return None

    def _save_to_cache(self, df, cache_path):
        """
        Save klines data to cache.

        Args:
            df (pandas.DataFrame): Klines data.
            cache_path (str): Cache file path.
        """
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(df, f)

            if self.logger:
                self.logger.debug(f"Saved klines data to cache: {cache_path}")
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to save to cache: {e}")

    def get_klines(self, symbol=None, interval=None, limit=200):
        """
        Get historical klines (candlestick data).

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.
            interval (str, optional): Kline interval. Defaults to config.TIMEFRAME.
            limit (int, optional): Number of klines to get. Defaults to 200.

        Returns:
            pandas.DataFrame: Klines data or None on error.
        """
        symbol = symbol or config.SYMBOL
        interval = interval or config.TIMEFRAME

        if self.logger:
            self.logger.debug(f"Getting {limit} klines for {symbol} ({interval})")

        # Check cache if enabled
        if self.cache_enabled:
            cache_key = self._get_cache_key(symbol, interval, limit)
            cache_path = self._get_cache_path(cache_key)

            if self._is_cache_valid(cache_path):
                df = self._load_from_cache(cache_path)
                if df is not None and not df.empty:
                    if self.logger:
                        self.logger.debug(f"Using cached data for {symbol} ({interval})")
                    return df

        # Try different time ranges if the first attempt fails
        for attempt, days_ago in enumerate([7, 30, 3, 1]):
            try:
                # Calculate time range
                end_time = int(time.time() * 1000)  # Current time in milliseconds
                start_time = end_time - (days_ago * 24 * 60 * 60 * 1000)  # X days ago

                if self.logger:
                    self.logger.debug(f"Attempt {attempt+1}: Fetching klines for {symbol} ({interval}) from {days_ago} days ago")

                # Get klines using PyBit V5 API
                response = self._retry_api_call(
                    self.client.get_kline,
                    category="linear",  # linear for USDT perpetual, can be spot, inverse, option
                    symbol=symbol,
                    interval=interval,
                    start=start_time,
                    end=end_time,
                    limit=min(limit, 1000)  # Ensure we don't exceed API limit
                )

                if self.logger:
                    self.logger.debug(f"API response for klines: {response}")

                # Check response
                if not response or response.get("retCode") != 0 or not response.get("result"):
                    if self.logger:
                        self.logger.warning(f"No klines data returned for {symbol} ({interval}). Response: {response}")
                    continue  # Try next time range

                # Extract data
                klines_data = response.get("result", {}).get("list", [])

                if not klines_data:
                    if self.logger:
                        self.logger.warning(f"Empty klines data for {symbol} ({interval}) from {days_ago} days ago.")
                    continue  # Try next time range

                # Convert to DataFrame
                df = pd.DataFrame(klines_data, columns=[
                    "timestamp", "open", "high", "low", "close", "volume", "turnover", "confirm"
                ])

                # Convert string values to appropriate types
                for col in ["open", "high", "low", "close", "volume", "turnover"]:
                    df[col] = pd.to_numeric(df[col])

                # Convert timestamp to datetime
                df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")

                # Convert confirm to boolean
                df["confirm"] = df["confirm"] == "1"

                # Sort by timestamp (oldest first)
                df = df.sort_values("timestamp").reset_index(drop=True)

                if self.logger:
                    self.logger.info(f"Successfully retrieved {len(df)} klines for {symbol} ({interval}) from {days_ago} days ago")

                # Save to cache if enabled
                if self.cache_enabled and df is not None and not df.empty:
                    cache_key = self._get_cache_key(symbol, interval, limit)
                    cache_path = self._get_cache_path(cache_key)
                    self._save_to_cache(df, cache_path)

                return df

            except Exception as e:
                self._log_error(e, f"Failed to get klines on attempt {attempt+1} for {days_ago} days ago")
                # Continue to next attempt

        # If we get here, all attempts failed
        if self.logger:
            self.logger.error(f"All attempts to get klines for {symbol} ({interval}) failed")

        # Try one last attempt with no start/end time (let the API use defaults)
        try:
            if self.logger:
                self.logger.debug(f"Final attempt: Fetching klines for {symbol} ({interval}) with default time range")

            response = self._retry_api_call(
                self.client.get_kline,
                category="linear",
                symbol=symbol,
                interval=interval,
                limit=min(limit, 200)  # Use a smaller limit for better chance of success
            )

            if not response or response.get("retCode") != 0 or not response.get("result"):
                if self.logger:
                    self.logger.error(f"Final attempt failed for {symbol} ({interval}). Response: {response}")
                if self.logger:
                    self.logger.error(f"Failed to get real data for {symbol} ({interval}) after multiple attempts")
                return None

            klines_data = response.get("result", {}).get("list", [])

            if not klines_data:
                if self.logger:
                    self.logger.error(f"Final attempt returned empty data for {symbol} ({interval})")
                if self.logger:
                    self.logger.error(f"Empty data returned for {symbol} ({interval}) from Bybit API")
                return None

            # Process data as before
            df = pd.DataFrame(klines_data, columns=[
                "timestamp", "open", "high", "low", "close", "volume", "turnover", "confirm"
            ])

            for col in ["open", "high", "low", "close", "volume", "turnover"]:
                df[col] = pd.to_numeric(df[col])

            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
            df["confirm"] = df["confirm"] == "1"
            df = df.sort_values("timestamp").reset_index(drop=True)

            if self.logger:
                self.logger.info(f"Final attempt succeeded: Retrieved {len(df)} klines for {symbol} ({interval})")

            # Save to cache
            if self.cache_enabled and df is not None and not df.empty:
                cache_key = self._get_cache_key(symbol, interval, limit)
                cache_path = self._get_cache_path(cache_key)
                self._save_to_cache(df, cache_path)

            return df

        except Exception as e:
            self._log_error(e, "Final attempt to get klines failed")
            if self.logger:
                self.logger.error(f"Exception occurred while getting data for {symbol} ({interval}): {e}")
            return None

    def get_account_info(self):
        """
        Get account information including account type and status.

        Returns:
            dict: Account information or None on error.
        """
        if self.logger:
            self.logger.debug("Getting account information")

        try:
            # Get account info using PyBit V5 API
            response = self._retry_api_call(
                self.client.get_account_info
            )

            # Check response
            if not response or response.get("retCode") != 0 or not response.get("result"):
                if self.logger:
                    self.logger.warning("No account information returned")
                return None

            # Extract account info
            account_info = response.get("result", {})

            if self.logger:
                self.logger.info(f"Account type: {account_info.get('unifiedMarginStatus')}")
                self.logger.info(f"Account mode: {account_info.get('marginMode')}")

            return account_info

        except Exception as e:
            self._log_error(e, "Failed to get account information")
            return None

    def get_wallet_balance(self):
        """
        Get wallet balance.

        Returns:
            dict: Wallet balance or None on error.
        """
        if self.logger:
            self.logger.debug("Getting wallet balance")

        try:
            # Get balance using PyBit V5 API
            response = self._retry_api_call(
                self.client.get_wallet_balance,
                accountType="UNIFIED",  # UNIFIED for Unified Account, CONTRACT for Contract Account
                coin="USDT"  # Optional: filter by specific coin
            )

            # Check response
            if not response or response.get("retCode") != 0 or not response.get("result"):
                if self.logger:
                    self.logger.warning("No wallet balance data returned.")
                return None

            # Extract balance data
            balance_data = response.get("result", {}).get("list", [])

            if not balance_data:
                if self.logger:
                    self.logger.warning("Empty wallet balance data.")
                return None

            # Find USDT balance
            usdt_balance = None
            for coin_balance in balance_data:
                # Check if the coin is directly USDT
                if coin_balance.get("coin") == "USDT":
                    usdt_balance = coin_balance
                    break

                # Check if there's a 'coin' list inside (nested structure)
                coin_list = coin_balance.get("coin", [])
                if isinstance(coin_list, list) and len(coin_list) > 0:
                    for asset in coin_list:
                        if asset.get("coin") == "USDT":
                            usdt_balance = asset
                            break
                    if usdt_balance:
                        break

            if not usdt_balance:
                if self.logger:
                    self.logger.warning("No USDT balance found.")
                return None

            # Create response with proper fallbacks for each field
            try:
                # Safely convert values to float with better error handling
                available_balance = self._safe_float_conversion(usdt_balance.get("availableToWithdraw"), "availableToWithdraw", 0)
                wallet_balance = self._safe_float_conversion(usdt_balance.get("walletBalance"), "walletBalance", 0)
                unrealized_pnl = self._safe_float_conversion(usdt_balance.get("unrealisedPnl"), "unrealisedPnl", 0)

                return {
                    "available_balance": available_balance,
                    "wallet_balance": wallet_balance,
                    "unrealized_pnl": unrealized_pnl
                }
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error converting balance values to float: {e}")
                    self.logger.debug(f"Raw balance data: {usdt_balance}")
                return None

        except Exception as e:
            self._log_error(e, "Failed to get wallet balance")
            return None

    def get_positions(self, symbol=None):
        """
        Get open positions.

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.

        Returns:
            list: Open positions or None on error.
        """
        symbol = symbol or config.SYMBOL

        if self.logger:
            self.logger.debug(f"Getting positions for {symbol}")

        try:
            # Get positions using PyBit V5 API
            response = self._retry_api_call(
                self.client.get_positions,
                category="linear",  # linear for USDT perpetual
                symbol=symbol,     # Optional: filter by specific symbol
                settleCoin="USDT"  # Optional: filter by settlement currency
            )

            # Check response
            if not response or response.get("retCode") != 0:
                if self.logger:
                    self.logger.warning(f"Failed to get positions: {response.get('retMsg', 'Unknown error')}.")
                return None

            # Extract positions data
            positions = response.get("result", {}).get("list", [])

            if not positions:
                if self.logger:
                    self.logger.debug(f"No positions found for {symbol}")
                return []

            # Convert to the format expected by the bot
            result = []
            for pos in positions:
                if float(pos.get('contracts', 0)) > 0:
                    result.append({
                        "symbol": symbol,
                        "side": "Buy" if pos.get('side') == 'long' else "Sell",
                        "size": pos.get('contracts', 0),
                        "entryPrice": pos.get('entryPrice', 0),
                        "liqPrice": pos.get('liquidationPrice', 0),
                        "unrealisedPnl": pos.get('unrealizedPnl', 0)
                    })

            return result

        except Exception as e:
            self._log_error(e, "Failed to get positions")
            return None

    def get_ticker(self, symbol=None):
        """
        Get ticker information.

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.

        Returns:
            dict: Ticker information or None on error.
        """
        symbol = symbol or config.SYMBOL

        if self.logger:
            self.logger.debug(f"Getting ticker for {symbol}")

        try:
            # Get ticker using PyBit V5 API
            response = self._retry_api_call(
                self.client.get_tickers,
                category="linear",  # linear for USDT perpetual, can be spot, inverse, option
                symbol=symbol      # Optional: filter by specific symbol
            )

            # Check response
            if not response or response.get("retCode") != 0 or not response.get("result"):
                if self.logger:
                    self.logger.warning(f"No ticker data found for {symbol}.")
                return None

            # Extract ticker data
            tickers = response.get("result", {}).get("list", [])

            if not tickers:
                if self.logger:
                    self.logger.warning(f"Empty ticker data for {symbol}.")
                return None

            ticker = tickers[0]

            # Convert to the format expected by the bot
            return {
                "symbol": symbol,
                "lastPrice": ticker.get("lastPrice", "0"),
                "indexPrice": ticker.get("indexPrice", "0"),
                "markPrice": ticker.get("markPrice", "0"),
                "prevPrice24h": ticker.get("prevPrice24h", "0"),
                "price24hPcnt": ticker.get("price24hPcnt", "0"),
                "highPrice24h": ticker.get("highPrice24h", "0"),
                "lowPrice24h": ticker.get("lowPrice24h", "0"),
                "volume24h": ticker.get("volume24h", "0"),
                "turnover24h": ticker.get("turnover24h", "0")
            }

        except Exception as e:
            self._log_error(e, "Failed to get ticker")
            return None

    def place_market_order(self, symbol=None, side=None, qty=None, reduce_only=False,
                          take_profit=None, stop_loss=None):
        """
        Place market order.

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.
            side (str): Order side (Buy or Sell).
            qty (float): Order quantity.
            reduce_only (bool, optional): Reduce only. Defaults to False.
            take_profit (float, optional): Take profit price.
            stop_loss (float, optional): Stop loss price.

        Returns:
            dict: Order information or None on error.
        """
        symbol = symbol or config.SYMBOL

        if not side or not qty:
            if self.logger:
                self.logger.error("Missing required parameters for market order")
            return None

        if config.DRY_RUN:
            if self.logger:
                self.logger.info(f"DRY RUN: Would place {side} market order for {qty} {symbol}")
                if take_profit:
                    self.logger.info(f"DRY RUN: With take profit at {take_profit}")
                if stop_loss:
                    self.logger.info(f"DRY RUN: With stop loss at {stop_loss}")
            return {"dry_run": True, "symbol": symbol, "side": side, "qty": qty}

        if self.logger:
            self.logger.info(f"Placing {side} market order for {qty} {symbol}")

        try:
            # Prepare parameters for V5 API order placement
            params = {
                "category": "linear",  # linear for USDT perpetual
                "symbol": symbol,
                "side": side,         # Buy or Sell
                "orderType": "Market", # Market, Limit, etc.
                "qty": str(qty),      # Order quantity
                "reduceOnly": reduce_only  # True to reduce position only
            }

            if take_profit:
                params["takeProfit"] = str(take_profit)
                params["tpTriggerBy"] = "LastPrice"
                params["tpslMode"] = "Full"

            if stop_loss:
                params["stopLoss"] = str(stop_loss)
                params["slTriggerBy"] = "LastPrice"
                params["tpslMode"] = "Full"

            response = self._retry_api_call(
                self.client.place_order,
                **params
            )

            return self._handle_response(response, "place_market_order")

        except Exception as e:
            self._log_error(e, "Failed to place market order")
            return None

    def set_leverage(self, symbol=None, leverage=None):
        """
        Set leverage for symbol.

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.
            leverage (int, optional): Leverage. Defaults to config.LEVERAGE.

        Returns:
            bool: Success or failure.
        """
        symbol = symbol or config.SYMBOL
        leverage = leverage or config.LEVERAGE

        if config.DRY_RUN:
            if self.logger:
                self.logger.info(f"DRY RUN: Would set leverage to {leverage}x for {symbol}")
            return True

        if self.logger:
            self.logger.info(f"Setting leverage to {leverage}x for {symbol}")

        try:
            response = self._retry_api_call(
                self.client.set_leverage,
                category="linear",
                symbol=symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )

            result = self._handle_response(response, "set_leverage")
            return result is not None

        except Exception as e:
            self._log_error(e, "Failed to set leverage")
            return False

    def cancel_all_orders(self, symbol=None):
        """
        Cancel all active orders.

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.

        Returns:
            bool: Success or failure.
        """
        symbol = symbol or config.SYMBOL

        if config.DRY_RUN:
            if self.logger:
                self.logger.info(f"DRY RUN: Would cancel all orders for {symbol}")
            return True

        if self.logger:
            self.logger.info(f"Cancelling all orders for {symbol}")

        try:
            response = self._retry_api_call(
                self.client.cancel_all_orders,
                category="linear",
                symbol=symbol
            )

            result = self._handle_response(response, "cancel_all_orders")
            return result is not None

        except Exception as e:
            self._log_error(e, "Failed to cancel all orders")
            return False

    def close_position(self, symbol=None):
        """
        Close position.

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.

        Returns:
            bool: Success or failure.
        """
        symbol = symbol or config.SYMBOL

        if config.DRY_RUN:
            if self.logger:
                self.logger.info(f"DRY RUN: Would close position for {symbol}")
            return True

        # Get current position
        positions = self.get_positions(symbol)
        if not positions:
            if self.logger:
                self.logger.info(f"No position to close for {symbol}")
            return True

        for position in positions:
            size = float(position.get("size", 0))
            if size == 0:
                continue

            side = "Sell" if position.get("side") == "Buy" else "Buy"

            if self.logger:
                self.logger.info(f"Closing {position.get('side')} position for {symbol} with size {size}")

            try:
                response = self._retry_api_call(
                    self.client.place_order,
                    category="linear",
                    symbol=symbol,
                    side=side,
                    orderType="Market",
                    qty=str(abs(size)),
                    reduceOnly=True
                )

                result = self._handle_response(response, "close_position")
                if not result:
                    return False

            except Exception as e:
                self._log_error(e, "Failed to close position")
                return False

        return True

    def start_websocket(self):
        """
        Start WebSocket connection for real-time data.

        Returns:
            bool: True if WebSocket started successfully, False otherwise.
        """
        if self.ws_enabled and self.ws_client is not None:
            if self.logger:
                self.logger.warning("WebSocket already started")
            return True

        try:
            # Initialize WebSocket client with V5 API
            self.ws_client = WebSocket(
                testnet=False,  # Always use mainnet
                api_key=self.api_key,
                api_secret=self.api_secret,
                domain="unified",     # Use unified for V5 API
                channel_type="linear" # linear for USDT perpetual
            )

            # Set WebSocket as enabled
            self.ws_enabled = True

            if self.logger:
                self.logger.info("WebSocket started successfully")

            return True
        except Exception as e:
            self._log_error(e, "Failed to start WebSocket")
            return False

    def stop_websocket(self):
        """
        Stop WebSocket connection.

        Returns:
            bool: True if WebSocket stopped successfully, False otherwise.
        """
        if not self.ws_enabled or self.ws_client is None:
            if self.logger:
                self.logger.warning("WebSocket not started")
            return True

        try:
            # Unsubscribe from all topics
            for topic in list(self.ws_callbacks.keys()):
                self.unsubscribe_topic(topic)

            # Close WebSocket connection
            self.ws_client = None
            self.ws_enabled = False

            if self.logger:
                self.logger.info("WebSocket stopped successfully")

            return True
        except Exception as e:
            self._log_error(e, "Failed to stop WebSocket")
            return False

    def _ws_callback(self, message):
        """
        WebSocket callback function.

        Args:
            message (dict): WebSocket message.
        """
        try:
            # Parse message
            if not isinstance(message, dict):
                message = json.loads(message)

            # Get topic
            topic = message.get("topic", "")
            if not topic:
                return

            # Store data
            with self.ws_lock:
                self.ws_data[topic] = message

            # Call callback function if registered
            if topic in self.ws_callbacks and callable(self.ws_callbacks[topic]):
                self.ws_callbacks[topic](message)

        except Exception as e:
            self._log_error(e, "WebSocket callback error")

    def subscribe_kline(self, symbol=None, interval=None, callback=None):
        """
        Subscribe to kline (candlestick) data.

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.
            interval (str, optional): Kline interval. Defaults to config.TIMEFRAME.
            callback (callable, optional): Callback function. Defaults to None.

        Returns:
            bool: True if subscribed successfully, False otherwise.
        """
        symbol = symbol or config.SYMBOL
        interval = interval or config.TIMEFRAME

        # Start WebSocket if not started
        if not self.ws_enabled or self.ws_client is None:
            if not self.start_websocket():
                return False

        try:
            # Format topic
            topic = f"kline.{interval}.{symbol}"

            # Register callback
            if callback is not None and callable(callback):
                self.ws_callbacks[topic] = callback

            # Subscribe to topic
            self.ws_client.kline_stream(
                interval=interval,
                symbol=symbol,
                callback=self._ws_callback
            )

            if self.logger:
                self.logger.info(f"Subscribed to kline data for {symbol} ({interval})")

            return True
        except Exception as e:
            self._log_error(e, "Failed to subscribe to kline data")
            return False

    def subscribe_ticker(self, symbol=None, callback=None):
        """
        Subscribe to ticker data.

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.
            callback (callable, optional): Callback function. Defaults to None.

        Returns:
            bool: True if subscribed successfully, False otherwise.
        """
        symbol = symbol or config.SYMBOL

        # Start WebSocket if not started
        if not self.ws_enabled or self.ws_client is None:
            if not self.start_websocket():
                return False

        try:
            # Format topic
            topic = f"tickers.{symbol}"

            # Register callback
            if callback is not None and callable(callback):
                self.ws_callbacks[topic] = callback

            # Subscribe to topic
            self.ws_client.ticker_stream(
                symbol=symbol,
                callback=self._ws_callback
            )

            if self.logger:
                self.logger.info(f"Subscribed to ticker data for {symbol}")

            return True
        except Exception as e:
            self._log_error(e, "Failed to subscribe to ticker data")
            return False

    def unsubscribe_topic(self, topic):
        """
        Unsubscribe from a topic.

        Args:
            topic (str): Topic to unsubscribe from.

        Returns:
            bool: True if unsubscribed successfully, False otherwise.
        """
        if not self.ws_enabled or self.ws_client is None:
            if self.logger:
                self.logger.warning("WebSocket not started")
            return True

        try:
            # Unsubscribe from topic
            self.ws_client.unsubscribe(topic)

            # Remove callback
            if topic in self.ws_callbacks:
                del self.ws_callbacks[topic]

            # Remove data
            with self.ws_lock:
                if topic in self.ws_data:
                    del self.ws_data[topic]

            if self.logger:
                self.logger.info(f"Unsubscribed from {topic}")

            return True
        except Exception as e:
            self._log_error(e, f"Failed to unsubscribe from {topic}")
            return False



    def get_realtime_kline(self, symbol=None, interval=None):
        """
        Get real-time kline data from WebSocket.

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.
            interval (str, optional): Kline interval. Defaults to config.TIMEFRAME.

        Returns:
            pandas.DataFrame: Kline data or None on error.
        """
        symbol = symbol or config.SYMBOL
        interval = interval or config.TIMEFRAME

        if self.logger:
            self.logger.debug(f"Getting real-time kline data for {symbol} ({interval})")

        # If WebSocket is not enabled or client is not initialized, fall back to REST API
        if not self.ws_enabled or self.ws_client is None:
            if self.logger:
                self.logger.info("WebSocket not started, falling back to REST API")
            return self.get_klines(symbol, interval)

        # Format topic
        topic = f"kline.{interval}.{symbol}"

        # Subscribe if not subscribed
        if topic not in self.ws_callbacks:
            if self.logger:
                self.logger.debug(f"Not subscribed to {topic}, attempting to subscribe")
            if not self.subscribe_kline(symbol, interval):
                if self.logger:
                    self.logger.warning("Failed to subscribe to kline data, falling back to REST API")
                return self.get_klines(symbol, interval)

        # Get data from WebSocket
        with self.ws_lock:
            data = self.ws_data.get(topic)

        if not data:
            if self.logger:
                self.logger.info("No real-time kline data available, falling back to REST API")
            # Get data from REST API
            return self.get_klines(symbol, interval)

        try:
            # Parse data
            kline_data = data.get("data", {})
            if not kline_data:
                if self.logger:
                    self.logger.warning("Empty kline data received from WebSocket, falling back to REST API")
                return self.get_klines(symbol, interval)

            if self.logger:
                self.logger.debug(f"Received WebSocket data for {symbol} ({interval}): {kline_data}")

            # Create DataFrame for the real-time candle
            try:
                df = pd.DataFrame([{
                    "timestamp": pd.to_datetime(int(kline_data.get("start", 0)), unit="ms"),
                    "open": float(kline_data.get("open", 0)),
                    "high": float(kline_data.get("high", 0)),
                    "low": float(kline_data.get("low", 0)),
                    "close": float(kline_data.get("close", 0)),
                    "volume": float(kline_data.get("volume", 0)),
                    "turnover": float(kline_data.get("turnover", 0)),
                    "confirm": kline_data.get("confirm", "1") == "1"
                }])
            except (ValueError, TypeError) as e:
                if self.logger:
                    self.logger.error(f"Error creating DataFrame from WebSocket data: {e}")
                    self.logger.error(f"Raw WebSocket data: {kline_data}")
                return self.get_klines(symbol, interval)

            # Get historical data to combine with real-time data
            historical_df = self.get_klines(symbol, interval)
            if historical_df is None or historical_df.empty:
                if self.logger:
                    self.logger.warning("Failed to get historical data to combine with real-time data")
                return df  # Return just the real-time candle if we can't get historical data

            # Remove the last candle from historical data if it's the same as real-time data
            try:
                if historical_df.iloc[-1]["timestamp"] == df.iloc[0]["timestamp"]:
                    historical_df = historical_df.iloc[:-1]

                # Combine historical and real-time data
                combined_df = pd.concat([historical_df, df]).reset_index(drop=True)

                if self.logger:
                    self.logger.debug(f"Successfully combined historical ({len(historical_df)} candles) and real-time data")

                return combined_df
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error combining historical and real-time data: {e}")
                # If combining fails, return just the historical data
                return historical_df

        except Exception as e:
            self._log_error(e, "Failed to parse real-time kline data")
            if self.logger:
                self.logger.info("Falling back to REST API after WebSocket error")
            return self.get_klines(symbol, interval)
