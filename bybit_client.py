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
import numpy as np
from collections import defaultdict

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

        # MACD parameters
        self.macd_fast = config.MACD_FAST
        self.macd_slow = config.MACD_SLOW
        self.macd_signal = config.MACD_SIGNAL

        # Additional MACD parameters
        self.macd_adjust = False  # Whether to adjust EMA calculation
        self.macd_price_col = 'close'  # Column to use for MACD calculation

        # Store calculated MACD data with timestamp for cache invalidation
        self.macd_data = defaultdict(dict)
        self.macd_last_update = defaultdict(int)  # Timestamp of last update
        self.macd_cache_ttl = 60  # Cache TTL in seconds

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
        self.ws_reconnect_attempts = 0
        self.ws_max_reconnect_attempts = 5
        self.ws_reconnect_delay = 5  # Initial delay in seconds
        self.ws_last_reconnect_time = 0
        self.ws_subscribed_topics = set()  # Track subscribed topics for reconnection

        if self.logger:
            self.logger.info(f"Bybit API client initialized")

    def _log_error(self, error, message, include_traceback=True, log_level="error"):
        """
        Log error with traceback and additional context.

        Args:
            error (Exception): The exception object.
            message (str): Error message prefix.
            include_traceback (bool, optional): Whether to include traceback. Defaults to True.
            log_level (str, optional): Log level to use. Defaults to "error".
        """
        if not self.logger:
            return

        # Format the error message
        error_msg = f"{message}: {error}"

        # Get the calling function name for better context
        import inspect
        caller_frame = inspect.currentframe().f_back
        caller_function = caller_frame.f_code.co_name if caller_frame else "unknown"
        caller_line = caller_frame.f_lineno if caller_frame else 0

        # Add context information
        context_msg = f"[{caller_function}:{caller_line}] {error_msg}"

        # Log at the appropriate level
        if log_level == "debug":
            self.logger.debug(context_msg)
        elif log_level == "info":
            self.logger.info(context_msg)
        elif log_level == "warning":
            self.logger.warning(context_msg)
        else:  # Default to error
            self.logger.error(context_msg)

        # Include traceback if requested
        if include_traceback:
            self.logger.error(f"Detailed error: {self.traceback.format_exc()}")

        # For critical errors, log additional system information
        if log_level == "critical":
            import platform
            import sys

            # Try to get memory info if psutil is available
            memory_info = "N/A"
            try:
                import psutil
                memory_info = f"{psutil.virtual_memory().percent}% used"
            except ImportError:
                pass

            system_info = {
                "python_version": sys.version,
                "platform": platform.platform(),
                "memory": memory_info
            }
            self.logger.critical(f"System information: {system_info}")

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
                # Log more details about the response for debugging
                self.logger.debug(f"Full response: {response}")
                # Check if it's an authentication error
                if response.get("retCode") == 401 or response.get("retCode") == 10003:
                    self.logger.error(f"Authentication error detected. Please check your API keys.")
                elif response.get("retCode") == -1 and "Authentication error" in str(response.get("retMsg", "")):
                    self.logger.error(f"Authentication error detected. Please check your API keys.")
            return None

    def _retry_api_call(self, func, *args, **kwargs):
        """
        Retry API call with exponential backoff.

        Args:
            func (callable): Function to call.
            *args: Function arguments.
            **kwargs: Function keyword arguments.

        Returns:
            dict: API response or error response dict on error.
        """
        max_retries = config.MAX_RETRIES
        retry_delay = config.RETRY_DELAY
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)

        # Check if we're in dry run mode and API keys are invalid
        if config.DRY_RUN and is_invalid_api_key(self.api_key, self.api_secret):
            if self.logger:
                self.logger.error("API keys are invalid. Please set valid API keys in .env file.")
            return {"retCode": -1, "retMsg": "Invalid API keys"}

        # Define retryable error patterns
        retryable_errors = [
            "timeout", "timed out", "connection", "socket", "reset", "broken pipe",
            "too many requests", "rate limit", "429", "503", "502", "500", "504",
            "server error", "maintenance", "overloaded", "unavailable", "busy"
        ]

        # Define non-retryable error patterns
        non_retryable_errors = [
            "invalid api key", "api key expired", "api key not found", "invalid signature",
            "permission denied", "unauthorized", "auth failed", "authentication failed",
            "not authorized", "access denied", "forbidden", "403", "401",
            "invalid parameter", "parameter error", "invalid argument", "bad request", "400"
        ]

        for attempt in range(max_retries):
            try:
                if self.logger and attempt > 0:
                    self.logger.debug(f"Retry attempt {attempt+1}/{max_retries} for {func_name}")

                response = func(*args, **kwargs)

                # Check if the response indicates an error
                if response and isinstance(response, dict):
                    ret_code = response.get("retCode")
                    ret_msg = response.get("retMsg", "Unknown error")

                    # Check for authentication errors
                    if ret_code in [401, 10003, 10004, 10005, 10006, 10007, 10008, 10009]:
                        if self.logger:
                            self.logger.error(f"Authentication error: {ret_msg}")
                            self.logger.error(f"Please check your API keys in config.py")
                        # Don't retry on authentication errors
                        return {"retCode": -1, "retMsg": f"Authentication error: {ret_msg}. Please check your API keys."}

                    # Check for rate limit errors
                    if ret_code in [10018, 10019, 10020, 10021, 429]:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            if self.logger:
                                self.logger.warning(f"Rate limit hit, waiting {wait_time}s before retry: {ret_msg}")
                            time.sleep(wait_time)
                            continue

                    # Check for server errors
                    if ret_code in [500, 502, 503, 504, 10002, 10010, 10011, 10012, 10013, 10014, 10015, 10016, 10017]:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            if self.logger:
                                self.logger.warning(f"Server error, waiting {wait_time}s before retry: {ret_msg}")
                            time.sleep(wait_time)
                            continue

                # Return the response if we get here
                return response

            except Exception as e:
                error_str = str(e).lower()
                is_retryable = any(err in error_str for err in retryable_errors)
                is_non_retryable = any(err in error_str for err in non_retryable_errors)

                if is_non_retryable:
                    if self.logger:
                        self.logger.error(f"Non-retryable error in {func_name}: {e}")
                        self.logger.error(f"Please check your API keys and parameters")
                    # Don't retry on non-retryable errors
                    return {"retCode": -1, "retMsg": f"API error: {e}"}

                if attempt < max_retries - 1 and is_retryable:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    if self.logger:
                        self.logger.warning(f"API call failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    if self.logger:
                        self.logger.error(f"API call to {func_name} failed after {attempt+1} attempts: {e}")
                        # Log more detailed error information
                        self.logger.error(f"Detailed error: {self.traceback.format_exc()}")
                        self.logger.error(f"Args: {args}, Kwargs: {kwargs}")

                    # Check if it's an authentication error - use more specific checks
                    if ("401" in error_str and "status code" in error_str) or \
                       "api key is invalid" in error_str or \
                       "errcode: 401" in error_str or \
                       ("http status code is not 200" in error_str and "authentication" in error_str):
                        if self.logger:
                            self.logger.error(f"Authentication error: {e}")
                            self.logger.error(f"Please check your API keys in config.py")
                        return {"retCode": -1, "retMsg": f"Authentication error: {e}. Please check your API keys."}

                    # Return error response for other errors
                    return {"retCode": -1, "retMsg": f"API error: {e}"}

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

    def calculate_macd(self, df, start_idx=None, end_idx=None, force_recalculate=False):
        """
        Calculate MACD for the given DataFrame with optimized performance.

        Args:
            df (pandas.DataFrame): DataFrame with price column (default: 'close').
            start_idx (int, optional): Start index for calculation. Defaults to None (calculate for all data).
            end_idx (int, optional): End index for calculation. Defaults to None (calculate until the end).
            force_recalculate (bool, optional): Force recalculation even if MACD columns exist. Defaults to False.

        Returns:
            pandas.DataFrame: DataFrame with MACD columns added.
        """
        if self.logger:
            self.logger.debug(f"Calculating MACD with parameters: fast={self.macd_fast}, slow={self.macd_slow}, signal={self.macd_signal}")

        # Check if we already have MACD columns and don't need to recalculate
        if not force_recalculate and 'macd' in df.columns and 'macd_signal' in df.columns and 'macd_hist' in df.columns:
            if start_idx is None and end_idx is None:
                if self.logger:
                    self.logger.debug("MACD columns already exist, skipping calculation")
                return df

        try:
            # Make sure we have enough data for MACD calculation
            min_periods = max(self.macd_slow, self.macd_fast, self.macd_signal)

            # Set default indices if not provided
            if start_idx is None:
                start_idx = 0
            if end_idx is None:
                end_idx = len(df)

            # Validate indices
            start_idx = max(0, start_idx)
            end_idx = min(len(df), end_idx)

            # Check if we have enough data
            if len(df) < min_periods:
                if self.logger:
                    self.logger.warning(f"Not enough data for MACD calculation. Need at least {min_periods} rows, got {len(df)}. Using default values.")
                    self.logger.warning(f"This may be due to insufficient historical data available for the selected timeframe.")
                    self.logger.warning(f"Try using a shorter timeframe or waiting for more data to accumulate.")

                # Initialize columns with default values if they don't exist
                if 'macd' not in df.columns:
                    df['macd'] = 0.0
                if 'macd_signal' not in df.columns:
                    df['macd_signal'] = 0.0
                if 'macd_hist' not in df.columns:
                    df['macd_hist'] = 0.0
                return df

            # Make sure the price column exists and has no NaN values
            if self.macd_price_col not in df.columns:
                if self.logger:
                    self.logger.warning(f"Price column '{self.macd_price_col}' not found, using 'close' instead")
                self.macd_price_col = 'close'

            # Check for NaN values in the price column
            if df[self.macd_price_col].isna().any():
                if self.logger:
                    self.logger.warning(f"Price column '{self.macd_price_col}' contains NaN values, filling with forward fill")
                # Fill NaN values with forward fill, then backward fill for any remaining NaNs
                df[self.macd_price_col] = df[self.macd_price_col].fillna(method='ffill').fillna(method='bfill')

            # Use pandas_ta for MACD calculation if available (much faster and more accurate)
            try:
                import pandas_ta as ta

                # If we're calculating for a subset, we need to include some history for accurate calculation
                if start_idx > 0:
                    # Include enough history for accurate calculation
                    calc_start_idx = max(0, start_idx - min_periods * 2)

                    # Calculate MACD for the subset plus history
                    macd_result = ta.macd(
                        df[self.macd_price_col].iloc[calc_start_idx:end_idx],
                        fast=self.macd_fast,
                        slow=self.macd_slow,
                        signal=self.macd_signal
                    )

                    # Extract the columns we need
                    macd_line = macd_result['MACD_' + str(self.macd_fast) + '_' + str(self.macd_slow) + '_' + str(self.macd_signal)]
                    macd_signal = macd_result['MACDs_' + str(self.macd_fast) + '_' + str(self.macd_slow) + '_' + str(self.macd_signal)]
                    macd_hist = macd_result['MACDh_' + str(self.macd_fast) + '_' + str(self.macd_slow) + '_' + str(self.macd_signal)]

                    # Assign to the original dataframe, but only for the requested range
                    # We need to account for the offset in indices
                    offset = start_idx - calc_start_idx

                    # If we already have MACD columns, update only the requested range
                    if 'macd' in df.columns and 'macd_signal' in df.columns and 'macd_hist' in df.columns:
                        df.loc[df.index[start_idx:end_idx], 'macd'] = macd_line.iloc[offset:offset + (end_idx - start_idx)].values
                        df.loc[df.index[start_idx:end_idx], 'macd_signal'] = macd_signal.iloc[offset:offset + (end_idx - start_idx)].values
                        df.loc[df.index[start_idx:end_idx], 'macd_hist'] = macd_hist.iloc[offset:offset + (end_idx - start_idx)].values
                    else:
                        # Initialize columns with NaN
                        df['macd'] = np.nan
                        df['macd_signal'] = np.nan
                        df['macd_hist'] = np.nan

                        # Update only the requested range
                        df.loc[df.index[start_idx:end_idx], 'macd'] = macd_line.iloc[offset:offset + (end_idx - start_idx)].values
                        df.loc[df.index[start_idx:end_idx], 'macd_signal'] = macd_signal.iloc[offset:offset + (end_idx - start_idx)].values
                        df.loc[df.index[start_idx:end_idx], 'macd_hist'] = macd_hist.iloc[offset:offset + (end_idx - start_idx)].values
                else:
                    # Calculate MACD for the entire dataframe or requested range
                    macd_result = ta.macd(
                        df[self.macd_price_col].iloc[start_idx:end_idx],
                        fast=self.macd_fast,
                        slow=self.macd_slow,
                        signal=self.macd_signal
                    )

                    # Extract the columns we need
                    macd_line = macd_result['MACD_' + str(self.macd_fast) + '_' + str(self.macd_slow) + '_' + str(self.macd_signal)]
                    macd_signal = macd_result['MACDs_' + str(self.macd_fast) + '_' + str(self.macd_slow) + '_' + str(self.macd_signal)]
                    macd_hist = macd_result['MACDh_' + str(self.macd_fast) + '_' + str(self.macd_slow) + '_' + str(self.macd_signal)]

                    # Assign to the original dataframe
                    if 'macd' in df.columns and 'macd_signal' in df.columns and 'macd_hist' in df.columns:
                        df.loc[df.index[start_idx:end_idx], 'macd'] = macd_line.values
                        df.loc[df.index[start_idx:end_idx], 'macd_signal'] = macd_signal.values
                        df.loc[df.index[start_idx:end_idx], 'macd_hist'] = macd_hist.values
                    else:
                        # Initialize columns with NaN
                        df['macd'] = np.nan
                        df['macd_signal'] = np.nan
                        df['macd_hist'] = np.nan

                        # Update only the requested range
                        df.loc[df.index[start_idx:end_idx], 'macd'] = macd_line.values
                        df.loc[df.index[start_idx:end_idx], 'macd_signal'] = macd_signal.values
                        df.loc[df.index[start_idx:end_idx], 'macd_hist'] = macd_hist.values

                if self.logger:
                    self.logger.debug("MACD calculated successfully using pandas_ta library")
            except (ImportError, Exception) as e:
                if self.logger:
                    self.logger.warning(f"Failed to calculate MACD using pandas_ta: {e}. Falling back to manual calculation.")

                # Fall back to manual calculation
                # Convert to numpy array for faster calculation
                price_array = df[self.macd_price_col].values

                # Calculate EMAs for MACD using vectorized operations
                # For EMA calculation: EMA_today = price_today * k + EMA_yesterday * (1 - k)
                # where k = 2 / (span + 1)
                fast_k = 2.0 / (self.macd_fast + 1)
                slow_k = 2.0 / (self.macd_slow + 1)
                signal_k = 2.0 / (self.macd_signal + 1)

                # Initialize arrays for EMA calculation
                fast_ema = np.zeros_like(price_array)
                slow_ema = np.zeros_like(price_array)

                # Calculate initial SMA values for the first points
                fast_ema[0:self.macd_fast] = np.mean(price_array[0:self.macd_fast])
                slow_ema[0:self.macd_slow] = np.mean(price_array[0:self.macd_slow])

                # Calculate EMAs using vectorized operations
                for i in range(self.macd_fast, len(price_array)):
                    fast_ema[i] = price_array[i] * fast_k + fast_ema[i-1] * (1 - fast_k)

                for i in range(self.macd_slow, len(price_array)):
                    slow_ema[i] = price_array[i] * slow_k + slow_ema[i-1] * (1 - slow_k)

                # Calculate MACD line
                macd_line = fast_ema - slow_ema

                # Calculate signal line
                signal_line = np.zeros_like(macd_line)
                signal_line[0:self.macd_signal] = np.mean(macd_line[0:self.macd_signal])

                for i in range(self.macd_signal, len(macd_line)):
                    signal_line[i] = macd_line[i] * signal_k + signal_line[i-1] * (1 - signal_k)

                # Calculate histogram
                histogram = macd_line - signal_line

                # Assign to dataframe
                df['macd'] = macd_line
                df['macd_signal'] = signal_line
                df['macd_hist'] = histogram

                if self.logger:
                    self.logger.debug("MACD calculated successfully using manual calculation")

            # Fill any remaining NaN values with 0
            df['macd'] = df['macd'].fillna(0.0)
            df['macd_signal'] = df['macd_signal'].fillna(0.0)
            df['macd_hist'] = df['macd_hist'].fillna(0.0)

        except Exception as e:
            self._log_error(e, "Failed to calculate MACD")
            # Initialize columns with default values if they don't exist
            if 'macd' not in df.columns:
                df['macd'] = 0.0
            if 'macd_signal' not in df.columns:
                df['macd_signal'] = 0.0
            if 'macd_hist' not in df.columns:
                df['macd_hist'] = 0.0

        return df

    def get_klines(self, symbol=None, interval=None, limit=None):
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

        # Calculate minimum required data points for MACD calculation
        min_periods = max(self.macd_slow, self.macd_fast, self.macd_signal)
        # Add buffer to ensure we have enough data (3x the minimum required)
        min_required = min_periods * 3

        # If limit is not provided or less than minimum required, use minimum required
        if limit is None or limit < min_required:
            limit = min_required

        if self.logger:
            self.logger.debug(f"Getting {limit} klines for {symbol} ({interval}). Minimum required for MACD: {min_required}")

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

                # Log the parameters being sent
                params = {
                    "category": "linear",  # linear for USDT perpetual, can be spot, inverse, option
                    "symbol": symbol,
                    "interval": interval,
                    "start": start_time,
                    "end": end_time,
                    "limit": min(limit, 1000)  # Ensure we don't exceed API limit but get enough data for MACD
                }

                if self.logger:
                    self.logger.debug(f"Get klines parameters: {params}")

                # Get klines using PyBit V5 API
                response = self._retry_api_call(
                    self.client.get_kline,
                    **params
                )

                if self.logger:
                    self.logger.debug(f"API response status for klines: {response.get('retCode') if response else 'No response'}")

                # Check response
                if not response or not response.get("result"):
                    if self.logger:
                        self.logger.warning(f"No klines data returned for {symbol} ({interval}). Response: {response}")
                    continue  # Try next time range

                # Handle the case where retCode is not 0 but it's not an authentication error
                if response.get("retCode") != 0:
                    # If it's a -1 retCode with "Authentication error" message but the retMsg is "OK",
                    # it's likely a false positive, so we can continue
                    if response.get("retCode") == -1 and \
                       "Authentication error" in str(response.get("retMsg", "")) and \
                       "OK" in str(response):
                        if self.logger:
                            self.logger.warning(f"Ignoring false authentication error for {symbol} ({interval}). Response: {response}")
                    else:
                        if self.logger:
                            self.logger.warning(f"API returned non-zero retCode for {symbol} ({interval}). Response: {response}")
                        continue  # Try next time range

                # Extract data
                klines_data = response.get("result", {}).get("list", [])

                if not klines_data:
                    if self.logger:
                        self.logger.warning(f"Empty klines data for {symbol} ({interval}) from {days_ago} days ago.")
                    continue  # Try next time range

                # Convert to DataFrame - check the number of columns in the response
                if len(klines_data) > 0 and len(klines_data[0]) == 7:
                    # V5 API returns 7 columns: timestamp, open, high, low, close, volume, turnover
                    df = pd.DataFrame(klines_data, columns=[
                        "timestamp", "open", "high", "low", "close", "volume", "turnover"
                    ])
                    # Add confirm column with default value True
                    df["confirm"] = True
                else:
                    # Fallback to original 8 columns format
                    df = pd.DataFrame(klines_data, columns=[
                        "timestamp", "open", "high", "low", "close", "volume", "turnover", "confirm"
                    ])

                # Convert string values to appropriate types with error handling
                for col in ["open", "high", "low", "close", "volume", "turnover"]:
                    try:
                        df[col] = pd.to_numeric(df[col])
                    except Exception as e:
                        if self.logger:
                            self.logger.warning(f"Error converting column {col} to numeric: {e}. Using original values.")

                # Convert timestamp to datetime with error handling
                try:
                    df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error converting timestamp to datetime: {e}. Using original values.")

                # Convert confirm to boolean with error handling
                try:
                    df["confirm"] = df["confirm"] == "1"
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error converting confirm to boolean: {e}. Using original values.")

                # Sort by timestamp (oldest first)
                try:
                    df = df.sort_values("timestamp").reset_index(drop=True)
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error sorting by timestamp: {e}. Using original order.")

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

            # Log the parameters being sent
            params = {
                "category": "linear",
                "symbol": symbol,
                "interval": interval,
                "limit": min(limit, 1000)  # Use a higher limit to ensure enough data for MACD
            }

            if self.logger:
                self.logger.debug(f"Final attempt get klines parameters: {params}")

            response = self._retry_api_call(
                self.client.get_kline,
                **params
            )

            if not response or not response.get("result"):
                if self.logger:
                    self.logger.error(f"Final attempt failed for {symbol} ({interval}). Response: {response}")
                if self.logger:
                    self.logger.error(f"Failed to get real data for {symbol} ({interval}) after multiple attempts")
                return None

            # Handle the case where retCode is not 0 but it's not an authentication error
            if response.get("retCode") != 0:
                # If it's a -1 retCode with "Authentication error" message but the retMsg is "OK",
                # it's likely a false positive, so we can continue
                if response.get("retCode") == -1 and \
                   "Authentication error" in str(response.get("retMsg", "")) and \
                   "OK" in str(response):
                    if self.logger:
                        self.logger.warning(f"Ignoring false authentication error in final attempt for {symbol} ({interval}). Response: {response}")
                else:
                    if self.logger:
                        self.logger.error(f"Final attempt returned non-zero retCode for {symbol} ({interval}). Response: {response}")
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

            # Process data as before with error handling - check the number of columns in the response
            if len(klines_data) > 0 and len(klines_data[0]) == 7:
                # V5 API returns 7 columns: timestamp, open, high, low, close, volume, turnover
                df = pd.DataFrame(klines_data, columns=[
                    "timestamp", "open", "high", "low", "close", "volume", "turnover"
                ])
                # Add confirm column with default value True
                df["confirm"] = True
            else:
                # Fallback to original 8 columns format
                df = pd.DataFrame(klines_data, columns=[
                    "timestamp", "open", "high", "low", "close", "volume", "turnover", "confirm"
                ])

            # Convert string values to appropriate types with error handling
            for col in ["open", "high", "low", "close", "volume", "turnover"]:
                try:
                    df[col] = pd.to_numeric(df[col])
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error converting column {col} to numeric: {e}. Using original values.")

            # Convert timestamp to datetime with error handling
            try:
                df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error converting timestamp to datetime: {e}. Using original values.")

            # Convert confirm to boolean with error handling
            try:
                df["confirm"] = df["confirm"] == "1"
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error converting confirm to boolean: {e}. Using original values.")

            # Sort by timestamp (oldest first)
            try:
                df = df.sort_values("timestamp").reset_index(drop=True)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error sorting by timestamp: {e}. Using original order.")

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
                # Get wallet balance first since we might need it for available balance
                wallet_balance = self._safe_float_conversion(usdt_balance.get("walletBalance"), "walletBalance", 0)

                # Get available balance with special handling
                available_to_withdraw = usdt_balance.get("availableToWithdraw")

                # Handle different cases for availableToWithdraw
                if available_to_withdraw is None or (isinstance(available_to_withdraw, str) and not available_to_withdraw.strip()):
                    # If it's None or empty string, use wallet balance
                    if self.logger:
                        self.logger.debug(f"Field 'availableToWithdraw' is {available_to_withdraw}, using walletBalance value {wallet_balance}")
                    available_balance = wallet_balance
                else:
                    try:
                        # Try to convert to float
                        available_balance = float(available_to_withdraw)
                    except (ValueError, TypeError):
                        # If conversion fails, use wallet balance
                        if self.logger:
                            self.logger.debug(f"Could not convert 'availableToWithdraw' value '{available_to_withdraw}' to float. Using walletBalance {wallet_balance}")
                        available_balance = wallet_balance

                # Get unrealized PnL
                unrealized_pnl = self._safe_float_conversion(usdt_balance.get("unrealisedPnl"), "unrealisedPnl", 0)

                # Create final response
                result = {
                    "available_balance": available_balance,
                    "wallet_balance": wallet_balance,
                    "unrealized_pnl": unrealized_pnl
                }

                # Log the final values for debugging
                if self.logger:
                    self.logger.debug(f"Wallet balance values: {result}")

                return result
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
                # Check if position size is greater than 0
                size = float(pos.get('size', 0))
                if size > 0:
                    result.append({
                        "symbol": symbol,
                        "side": pos.get('side', ''),  # 'Buy' or 'Sell'
                        "size": size,
                        "entryPrice": float(pos.get('avgPrice', 0)),
                        "liqPrice": float(pos.get('liqPrice', 0)),
                        "unrealisedPnl": float(pos.get('unrealisedPnl', 0))
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

        # Try to get real-time ticker data from WebSocket first
        if self.ws_enabled and self.ws_client is not None:
            realtime_ticker = self.get_realtime_ticker(symbol)
            if realtime_ticker is not None:
                return realtime_ticker

        # Fall back to REST API if WebSocket data is not available
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

            # Convert to the format expected by the bot with safe conversion to float
            return {
                "symbol": symbol,
                "lastPrice": self._safe_float_conversion(ticker.get("lastPrice"), "lastPrice", 0.0),
                "indexPrice": self._safe_float_conversion(ticker.get("indexPrice"), "indexPrice", 0.0),
                "markPrice": self._safe_float_conversion(ticker.get("markPrice"), "markPrice", 0.0),
                "prevPrice24h": self._safe_float_conversion(ticker.get("prevPrice24h"), "prevPrice24h", 0.0),
                "price24hPcnt": self._safe_float_conversion(ticker.get("price24hPcnt"), "price24hPcnt", 0.0),
                "highPrice24h": self._safe_float_conversion(ticker.get("highPrice24h"), "highPrice24h", 0.0),
                "lowPrice24h": self._safe_float_conversion(ticker.get("lowPrice24h"), "lowPrice24h", 0.0),
                "volume24h": self._safe_float_conversion(ticker.get("volume24h"), "volume24h", 0.0),
                "turnover24h": self._safe_float_conversion(ticker.get("turnover24h"), "turnover24h", 0.0)
            }

        except Exception as e:
            self._log_error(e, "Failed to get ticker")
            return None

    def get_realtime_ticker(self, symbol=None):
        """
        Get real-time ticker data from WebSocket.

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.

        Returns:
            dict: Ticker information or None on error.
        """
        symbol = symbol or config.SYMBOL

        if self.logger:
            self.logger.debug(f"Getting real-time ticker data for {symbol}")

        # If WebSocket is not enabled or client is not initialized, return None
        if not self.ws_enabled or self.ws_client is None:
            return None

        # Format topic
        topic = f"tickers.{symbol}"

        # Check if we're subscribed to this topic
        is_subscribed = topic in self.ws_callbacks

        # Subscribe if not subscribed
        if not is_subscribed:
            if self.logger:
                self.logger.debug(f"Not subscribed to {topic}, attempting to subscribe")
            try:
                # Check if PyBit already has this subscription
                # This is a workaround for PyBit not providing a way to check subscriptions
                if hasattr(self.ws_client, '_callback_directory'):
                    callback_directory = self.ws_client._callback_directory
                    if topic in callback_directory:
                        if self.logger:
                            self.logger.debug(f"PyBit already subscribed to {topic}, adding to local tracking")
                        # Add to our local tracking
                        self.ws_callbacks[topic] = None
                        is_subscribed = True

                # Only try to subscribe if we're not already subscribed
                if not is_subscribed:
                    if not self.subscribe_ticker(symbol):
                        if self.logger:
                            self.logger.warning(f"Failed to subscribe to ticker data for {symbol}")
                        return None
            except Exception as e:
                # If we get an error about already being subscribed, just continue
                if "You have already subscribed to this topic" in str(e):
                    if self.logger:
                        self.logger.debug(f"Already subscribed to {topic} (from exception)")
                    # Add to our local tracking
                    self.ws_callbacks[topic] = None
                else:
                    # For other errors, log and return None
                    self._log_error(e, f"Failed to subscribe to ticker data for {symbol}")
                    return None

        # Get data from WebSocket
        with self.ws_lock:
            data = self.ws_data.get(topic)

        if not data:
            if self.logger:
                self.logger.debug(f"No real-time ticker data available for {symbol}")
            return None

        try:
            # Parse data
            ticker_data = data.get("data", {})
            if not ticker_data:
                if self.logger:
                    self.logger.warning(f"Empty ticker data received from WebSocket for {symbol}")
                return None

            # Check if ticker_data is a list (new format) or a dict (old format)
            if isinstance(ticker_data, list) and len(ticker_data) > 0:
                ticker_data = ticker_data[0]  # Take the first item if it's a list

            if not isinstance(ticker_data, dict):
                if self.logger:
                    self.logger.warning(f"Unexpected ticker data format: {type(ticker_data)}")
                return None

            if self.logger:
                self.logger.debug(f"Received WebSocket ticker data for {symbol}")

            # Convert to the format expected by the bot with safe conversion to float
            return {
                "symbol": symbol,
                "lastPrice": self._safe_float_conversion(ticker_data.get("lastPrice"), "lastPrice", 0.0),
                "indexPrice": self._safe_float_conversion(ticker_data.get("indexPrice"), "indexPrice", 0.0),
                "markPrice": self._safe_float_conversion(ticker_data.get("markPrice"), "markPrice", 0.0),
                "prevPrice24h": self._safe_float_conversion(ticker_data.get("prevPrice24h"), "prevPrice24h", 0.0),
                "price24hPcnt": self._safe_float_conversion(ticker_data.get("price24hPcnt"), "price24hPcnt", 0.0),
                "highPrice24h": self._safe_float_conversion(ticker_data.get("highPrice24h"), "highPrice24h", 0.0),
                "lowPrice24h": self._safe_float_conversion(ticker_data.get("lowPrice24h"), "lowPrice24h", 0.0),
                "volume24h": self._safe_float_conversion(ticker_data.get("volume24h"), "volume24h", 0.0),
                "turnover24h": self._safe_float_conversion(ticker_data.get("turnover24h"), "turnover24h", 0.0)
            }

        except Exception as e:
            self._log_error(e, "Failed to parse real-time ticker data")
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
                "qty": str(qty),      # Order quantity must be string
                "reduceOnly": reduce_only,  # True to reduce position only
                "positionIdx": 0      # 0 for one-way mode
            }

            # Add take profit and stop loss if provided
            if take_profit:
                params["takeProfit"] = str(take_profit)
                params["tpTriggerBy"] = "LastPrice"
                params["tpslMode"] = "Full"
                params["tpOrderType"] = "Market"

            if stop_loss:
                params["stopLoss"] = str(stop_loss)
                params["slTriggerBy"] = "LastPrice"
                params["tpslMode"] = "Full"
                params["slOrderType"] = "Market"

            # Log the parameters being sent
            if self.logger:
                self.logger.debug(f"Order parameters: {params}")

            response = self._retry_api_call(
                self.client.place_order,
                **params
            )

            # Log the response
            if self.logger:
                self.logger.debug(f"Order response: {response}")

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
            # Log the parameters being sent
            if self.logger:
                self.logger.debug(f"Setting leverage parameters: symbol={symbol}, leverage={leverage}")

            response = self._retry_api_call(
                self.client.set_leverage,
                category="linear",
                symbol=symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )

            # Log the response
            if self.logger:
                self.logger.debug(f"Set leverage response: {response}")

            result = self._handle_response(response, "set_leverage")
            if result is not None:
                if self.logger:
                    self.logger.info(f"Successfully set leverage to {leverage}x for {symbol}")
                return True
            else:
                if self.logger:
                    self.logger.error(f"Failed to set leverage for {symbol}")
                return False

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
            # Log the parameters being sent
            if self.logger:
                self.logger.debug(f"Cancel all orders parameters: category=linear, symbol={symbol}")

            response = self._retry_api_call(
                self.client.cancel_all_orders,
                category="linear",
                symbol=symbol
            )

            # Log the response
            if self.logger:
                self.logger.debug(f"Cancel all orders response: {response}")

            result = self._handle_response(response, "cancel_all_orders")
            if result is not None:
                if self.logger:
                    self.logger.info(f"Successfully cancelled all orders for {symbol}")
                return True
            else:
                if self.logger:
                    self.logger.error(f"Failed to cancel all orders for {symbol}")
                return False

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

            # Determine the opposite side for closing
            side = "Sell" if position.get("side") == "Buy" else "Buy"

            if self.logger:
                self.logger.info(f"Closing {position.get('side')} position for {symbol} with size {size}")

            try:
                # Log the parameters being sent
                params = {
                    "category": "linear",
                    "symbol": symbol,
                    "side": side,
                    "orderType": "Market",
                    "qty": str(abs(size)),
                    "reduceOnly": True,
                    "positionIdx": 0  # 0 for one-way mode
                }

                if self.logger:
                    self.logger.debug(f"Close position parameters: {params}")

                response = self._retry_api_call(
                    self.client.place_order,
                    **params
                )

                # Log the response
                if self.logger:
                    self.logger.debug(f"Close position response: {response}")

                result = self._handle_response(response, "close_position")
                if not result:
                    if self.logger:
                        self.logger.error(f"Failed to close {position.get('side')} position for {symbol}")
                    return False
                else:
                    if self.logger:
                        self.logger.info(f"Successfully closed {position.get('side')} position for {symbol}")

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
            # Reset reconnect attempts if this is a manual start
            self.ws_reconnect_attempts = 0

            # Log the parameters being used
            if self.logger:
                self.logger.debug(f"Starting WebSocket with parameters: testnet=False, domain=bybit, channel_type=linear")

            # Initialize WebSocket client with V5 API
            self.ws_client = WebSocket(
                testnet=False,  # Always use mainnet
                api_key=self.api_key,
                api_secret=self.api_secret,
                domain="bybit",       # Use bybit for V5 API (not unified)
                channel_type="linear" # linear for USDT perpetual
            )

            # Set WebSocket as enabled
            self.ws_enabled = True
            self.ws_last_reconnect_time = int(time.time())

            # Resubscribe to previously subscribed topics
            self._resubscribe_to_topics()

            if self.logger:
                self.logger.info("WebSocket started successfully")

            return True
        except Exception as e:
            self._log_error(e, "Failed to start WebSocket")
            if self.logger:
                self.logger.error(f"WebSocket initialization parameters: testnet=False, domain=bybit, channel_type=linear")
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
            try:
                # Try to close the WebSocket connection if the client has a close method
                if hasattr(self.ws_client, 'close') and callable(getattr(self.ws_client, 'close')):
                    self.ws_client.close()
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error closing WebSocket connection: {e}")

            # Clear references
            self.ws_client = None
            self.ws_enabled = False
            self.ws_callbacks = {}
            with self.ws_lock:
                self.ws_data = {}

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
        # Check if WebSocket is still enabled
        if not self.ws_enabled or self.ws_client is None:
            return

        try:
            # Parse message
            if not isinstance(message, dict):
                message = json.loads(message)

            # Get topic
            topic = message.get("topic", "")
            if not topic:
                return

            # Check if we're still subscribed to this topic
            if topic not in self.ws_callbacks:
                # If we receive a message for a topic we're not tracking, but it's a valid topic format,
                # add it to our tracking to avoid subscription errors in the future
                if topic.startswith("kline.") or topic.startswith("tickers."):
                    if self.logger:
                        self.logger.debug(f"Received message for untracked topic {topic}, adding to tracking")
                    self.ws_callbacks[topic] = None
                else:
                    return

            # Log the received message for debugging
            if self.logger:
                self.logger.debug(f"Received WebSocket message for topic {topic}")

            # Store data
            with self.ws_lock:
                self.ws_data[topic] = message

            # Process kline data for MACD calculation if it's a kline topic
            if topic.startswith("kline."):
                self.calculate_macd_callback(topic, message)

            # Call callback function if registered
            if topic in self.ws_callbacks and callable(self.ws_callbacks[topic]):
                self.ws_callbacks[topic](message)

        except Exception as e:
            self._log_error(e, "WebSocket callback error")
            if self.logger:
                self.logger.error(f"Error processing WebSocket message: {message if 'message' in locals() else 'Unknown message'}")

    def calculate_macd_callback(self, topic, message):
        """
        Calculate MACD for real-time kline data received from WebSocket.
        Uses optimized calculation and caching for better performance.

        Args:
            topic (str): WebSocket topic.
            message (dict): WebSocket message.
        """
        try:
            # Extract symbol and interval from topic
            # Topic format: kline.{interval}.{symbol}
            parts = topic.split('.')
            if len(parts) != 3:
                if self.logger:
                    self.logger.warning(f"Invalid kline topic format: {topic}")
                return

            interval = parts[1]
            symbol = parts[2]

            # Create a unique key for this symbol and interval
            macd_key = f"{symbol}_{interval}"

            # Check if we need to recalculate MACD based on cache TTL
            current_time = int(time.time())
            last_update_time = self.macd_last_update.get(macd_key, 0)
            cache_valid = (current_time - last_update_time) < self.macd_cache_ttl

            # If cache is still valid, skip calculation
            if cache_valid and macd_key in self.macd_data and self.macd_data[macd_key] is not None:
                if self.logger:
                    self.logger.debug(f"Using cached MACD data for {symbol} ({interval}), last updated {current_time - last_update_time}s ago")
                return

            # Get kline data from message
            kline_data = message.get("data", {})
            if not kline_data:
                if self.logger:
                    self.logger.warning("Empty kline data received from WebSocket")
                return

            # Check if kline_data is a list (new format) or a dict (old format)
            if isinstance(kline_data, list) and len(kline_data) > 0:
                kline_data = kline_data[0]  # Take the first item if it's a list

            if not isinstance(kline_data, dict):
                if self.logger:
                    self.logger.warning(f"Unexpected kline data format: {type(kline_data)}")
                return

            # Use incremental update for better performance
            updated_df = self.update_macd_with_new_data(symbol, interval)

            if updated_df is None or updated_df.empty:
                if self.logger:
                    self.logger.warning("Failed to update MACD incrementally, falling back to full calculation")

                # Fall back to full calculation
                historical_df = self.get_klines(symbol, interval)
                if historical_df is None or historical_df.empty:
                    if self.logger:
                        self.logger.warning("Failed to get historical data for MACD calculation")
                    return

                # Calculate MACD for historical data using optimized method
                historical_df = self.calculate_macd(historical_df, force_recalculate=True)

                # Store the calculated MACD data and update timestamp
                self.macd_data[macd_key] = historical_df
                self.macd_last_update[macd_key] = current_time

            if self.logger:
                self.logger.debug(f"MACD calculated for {symbol} ({interval}) after receiving new data")

        except Exception as e:
            self._log_error(e, "Failed to calculate MACD from WebSocket data")

    def get_macd_data(self, symbol=None, interval=None, force_recalculate=False):
        """
        Get pre-calculated MACD data for the given symbol and interval.
        Uses caching for better performance.

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.
            interval (str, optional): Kline interval. Defaults to config.TIMEFRAME.
            force_recalculate (bool, optional): Force recalculation even if cached data exists. Defaults to False.

        Returns:
            pandas.DataFrame: DataFrame with MACD data or None if not available.
        """
        symbol = symbol or config.SYMBOL
        interval = interval or config.TIMEFRAME

        macd_key = f"{symbol}_{interval}"
        current_time = int(time.time())

        # Check if we have valid cached data
        cache_valid = False
        if macd_key in self.macd_data and self.macd_data[macd_key] is not None and not self.macd_data[macd_key].empty:
            last_update_time = self.macd_last_update.get(macd_key, 0)
            cache_valid = (current_time - last_update_time) < self.macd_cache_ttl

        # Return cached data if valid and not forcing recalculation
        if cache_valid and not force_recalculate:
            if self.logger:
                self.logger.debug(f"Returning cached MACD data for {symbol} ({interval}), last updated {current_time - self.macd_last_update[macd_key]}s ago")
            return self.macd_data[macd_key]
        else:
            if self.logger:
                if force_recalculate:
                    self.logger.debug(f"Forcing recalculation of MACD data for {symbol} ({interval})")
                else:
                    self.logger.debug(f"No valid cached MACD data available for {symbol} ({interval}), calculating now")

            # Calculate minimum required data points for MACD calculation
            min_periods = max(self.macd_slow, self.macd_fast, self.macd_signal)
            # Add buffer to ensure we have enough data (3x the minimum required)
            min_required = min_periods * 3

            # Get historical data and calculate MACD with enough data for MACD calculation
            historical_df = self.get_klines(symbol, interval, limit=min_required)
            if historical_df is None or historical_df.empty:
                if self.logger:
                    self.logger.warning(f"Failed to get historical data for {symbol} ({interval})")
                return None

            # Check if we have enough data
            if len(historical_df) < min_periods:
                if self.logger:
                    self.logger.warning(f"Not enough historical data for MACD calculation. Need at least {min_periods} rows, got {len(historical_df)}.")
                    self.logger.warning(f"This may be due to insufficient historical data available for the selected timeframe.")
                    self.logger.warning(f"Try using a shorter timeframe or waiting for more data to accumulate.")

            # Calculate MACD for historical data using optimized method
            historical_df = self.calculate_macd(historical_df, force_recalculate=force_recalculate)

            # Store the calculated MACD data and update timestamp
            self.macd_data[macd_key] = historical_df
            self.macd_last_update[macd_key] = current_time

            if self.logger:
                self.logger.debug(f"MACD calculation completed for {symbol} ({interval})")

            return historical_df

    def update_macd_with_new_data(self, symbol=None, interval=None, new_candle=None):
        """
        Update MACD calculation with new candle data without recalculating the entire dataset.
        This is an optimized method for incremental updates.

        Args:
            symbol (str, optional): Trading symbol. Defaults to config.SYMBOL.
            interval (str, optional): Kline interval. Defaults to config.TIMEFRAME.
            new_candle (dict, optional): New candle data. If None, will get the latest candle from WebSocket.

        Returns:
            pandas.DataFrame: Updated DataFrame with MACD data or None if update failed.
        """
        symbol = symbol or config.SYMBOL
        interval = interval or config.TIMEFRAME
        macd_key = f"{symbol}_{interval}"

        # Check if we have existing MACD data
        if macd_key not in self.macd_data or self.macd_data[macd_key] is None or self.macd_data[macd_key].empty:
            if self.logger:
                self.logger.debug(f"No existing MACD data for {symbol} ({interval}), calculating from scratch")
            return self.get_macd_data(symbol, interval, force_recalculate=True)

        try:
            # Get existing data
            df = self.macd_data[macd_key].copy()

            # If no new candle provided, try to get it from WebSocket
            if new_candle is None:
                topic = f"kline.{interval}.{symbol}"
                with self.ws_lock:
                    data = self.ws_data.get(topic)

                if not data or not data.get("data"):
                    if self.logger:
                        self.logger.warning(f"No real-time data available for {symbol} ({interval})")
                    return df

                kline_data = data.get("data", {})
                if isinstance(kline_data, list) and len(kline_data) > 0:
                    kline_data = kline_data[0]

                if not isinstance(kline_data, dict):
                    if self.logger:
                        self.logger.warning(f"Unexpected kline data format: {type(kline_data)}")
                    return df

                # Create new candle data
                new_candle = {
                    "timestamp": pd.to_datetime(int(kline_data.get("start", 0)), unit="ms"),
                    "open": float(kline_data.get("open", 0)),
                    "high": float(kline_data.get("high", 0)),
                    "low": float(kline_data.get("low", 0)),
                    "close": float(kline_data.get("close", 0)),
                    "volume": float(kline_data.get("volume", 0)),
                    "turnover": float(kline_data.get("turnover", 0)),
                    "confirm": kline_data.get("confirm", "1") == "1"
                }

            # Check if the new candle is already in our data
            new_timestamp = new_candle["timestamp"] if isinstance(new_candle["timestamp"], pd.Timestamp) else pd.to_datetime(new_candle["timestamp"])

            # Find if we already have this candle
            existing_idx = df[df["timestamp"] == new_timestamp].index

            if len(existing_idx) > 0:
                # Update existing candle
                idx = existing_idx[0]
                for key, value in new_candle.items():
                    if key in df.columns:
                        df.at[idx, key] = value
            else:
                # Append new candle
                new_row = pd.DataFrame([new_candle])
                df = pd.concat([df, new_row]).reset_index(drop=True)

            # Calculate MACD only for the new/updated candle
            # We need some history for accurate calculation, so we'll use the last N candles
            min_periods = max(self.macd_slow, self.macd_fast, self.macd_signal)
            history_size = max(min_periods * 3, 50)  # Use at least 3x minimum required or 50 candles
            start_idx = max(0, len(df) - history_size)

            # Check if we have enough data
            if len(df) < min_periods:
                if self.logger:
                    self.logger.warning(f"Not enough data for incremental MACD update. Need at least {min_periods} rows, got {len(df)}.")
                    self.logger.warning(f"Falling back to full MACD calculation.")
                return self.get_macd_data(symbol, interval, force_recalculate=True)

            # Calculate MACD for the subset
            df = self.calculate_macd(df, start_idx=start_idx, end_idx=len(df), force_recalculate=True)

            # Update stored data and timestamp
            self.macd_data[macd_key] = df
            self.macd_last_update[macd_key] = int(time.time())

            if self.logger:
                self.logger.debug(f"MACD incrementally updated for {symbol} ({interval})")

            return df

        except Exception as e:
            self._log_error(e, f"Failed to update MACD incrementally for {symbol} ({interval})")
            # Fall back to full recalculation
            if self.logger:
                self.logger.warning(f"Falling back to full MACD recalculation for {symbol} ({interval})")
            return self.get_macd_data(symbol, interval, force_recalculate=True)

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

            # Check if already subscribed in our local tracking
            if topic in self.ws_callbacks:
                if self.logger:
                    self.logger.debug(f"Already subscribed to {topic} (local tracking)")
                return True

            # Check if PyBit already has this subscription
            # This is a workaround for PyBit not providing a way to check subscriptions
            try:
                # Try to get the callback directory from PyBit
                if hasattr(self.ws_client, '_callback_directory'):
                    callback_directory = self.ws_client._callback_directory
                    if topic in callback_directory:
                        if self.logger:
                            self.logger.debug(f"PyBit already subscribed to {topic}, adding to local tracking")
                        # Add to our local tracking
                        self.ws_callbacks[topic] = None
                        # Add to subscribed topics for reconnection
                        self.ws_subscribed_topics.add(("kline", symbol, interval))
                        return True
            except Exception as e:
                # Ignore errors in this check
                if self.logger:
                    self.logger.debug(f"Error checking PyBit subscriptions: {e}")

            # Register callback in our local tracking before attempting to subscribe
            # This helps prevent race conditions where multiple subscribe attempts happen simultaneously
            self.ws_callbacks[topic] = callback if callback is not None and callable(callback) else None

            # Log the parameters being sent
            if self.logger:
                self.logger.debug(f"Subscribing to kline stream with parameters: interval={interval}, symbol={symbol}")

            try:
                # Subscribe to topic
                self.ws_client.kline_stream(
                    interval=interval,
                    symbol=symbol,
                    callback=self._ws_callback
                )

                # Add to subscribed topics for reconnection
                self.ws_subscribed_topics.add(("kline", symbol, interval))

                if self.logger:
                    self.logger.info(f"Subscribed to kline data for {symbol} ({interval})")

                return True
            except Exception as sub_error:
                # If we get an error about already being subscribed, consider it a success
                if "You have already subscribed to this topic" in str(sub_error):
                    if self.logger:
                        self.logger.debug(f"Already subscribed to {topic} (from PyBit exception)")
                    # Add to subscribed topics for reconnection
                    self.ws_subscribed_topics.add(("kline", symbol, interval))
                    return True
                else:
                    # For other errors, remove from our tracking and re-raise
                    if topic in self.ws_callbacks:
                        del self.ws_callbacks[topic]
                    raise sub_error
        except Exception as e:
            self._log_error(e, "Failed to subscribe to kline data")
            if self.logger:
                self.logger.debug(f"Subscription parameters: interval={interval}, symbol={symbol}")
            # Check if we need to reconnect the WebSocket
            if "Connection is closed" in str(e) or "Not connected" in str(e):
                self._reconnect_websocket()
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

            # Check if already subscribed in our local tracking
            if topic in self.ws_callbacks:
                if self.logger:
                    self.logger.debug(f"Already subscribed to {topic} (local tracking)")
                return True

            # Check if PyBit already has this subscription
            # This is a workaround for PyBit not providing a way to check subscriptions
            try:
                # Try to get the callback directory from PyBit
                if hasattr(self.ws_client, '_callback_directory'):
                    callback_directory = self.ws_client._callback_directory
                    if topic in callback_directory:
                        if self.logger:
                            self.logger.debug(f"PyBit already subscribed to {topic}, adding to local tracking")
                        # Add to our local tracking
                        self.ws_callbacks[topic] = None
                        # Add to subscribed topics for reconnection
                        self.ws_subscribed_topics.add(("ticker", symbol, None))
                        return True
            except Exception as e:
                # Ignore errors in this check
                if self.logger:
                    self.logger.debug(f"Error checking PyBit subscriptions: {e}")

            # Register callback in our local tracking before attempting to subscribe
            # This helps prevent race conditions where multiple subscribe attempts happen simultaneously
            self.ws_callbacks[topic] = callback if callback is not None and callable(callback) else None

            # Log the parameters being sent
            if self.logger:
                self.logger.debug(f"Subscribing to ticker stream with parameters: symbol={symbol}")

            try:
                # Subscribe to topic
                self.ws_client.ticker_stream(
                    symbol=symbol,
                    callback=self._ws_callback
                )

                # Add to subscribed topics for reconnection
                self.ws_subscribed_topics.add(("ticker", symbol, None))

                if self.logger:
                    self.logger.info(f"Subscribed to ticker data for {symbol}")

                return True
            except Exception as sub_error:
                # If we get an error about already being subscribed, consider it a success
                if "You have already subscribed to this topic" in str(sub_error):
                    if self.logger:
                        self.logger.debug(f"Already subscribed to {topic} (from PyBit exception)")
                    # Add to subscribed topics for reconnection
                    self.ws_subscribed_topics.add(("ticker", symbol, None))
                    return True
                else:
                    # For other errors, remove from our tracking and re-raise
                    if topic in self.ws_callbacks:
                        del self.ws_callbacks[topic]
                    raise sub_error
        except Exception as e:
            self._log_error(e, "Failed to subscribe to ticker data")
            if self.logger:
                self.logger.debug(f"Subscription parameters: symbol={symbol}")
            # Check if we need to reconnect the WebSocket
            if "Connection is closed" in str(e) or "Not connected" in str(e):
                self._reconnect_websocket()
            return False

    def _reconnect_websocket(self):
        """
        Reconnect WebSocket connection with exponential backoff.

        Returns:
            bool: True if reconnected successfully, False otherwise.
        """
        # Check if we've exceeded the maximum number of reconnect attempts
        if self.ws_reconnect_attempts >= self.ws_max_reconnect_attempts:
            if self.logger:
                self.logger.error(f"Failed to reconnect WebSocket after {self.ws_reconnect_attempts} attempts")
            return False

        # Check if we need to wait before reconnecting (to avoid hammering the server)
        current_time = int(time.time())
        time_since_last_reconnect = current_time - self.ws_last_reconnect_time
        reconnect_delay = min(300, self.ws_reconnect_delay * (2 ** self.ws_reconnect_attempts))  # Exponential backoff with 5 minute cap

        if time_since_last_reconnect < reconnect_delay:
            if self.logger:
                self.logger.debug(f"Waiting {reconnect_delay - time_since_last_reconnect}s before reconnecting WebSocket")
            time.sleep(reconnect_delay - time_since_last_reconnect)

        # Increment reconnect attempts
        self.ws_reconnect_attempts += 1

        if self.logger:
            self.logger.info(f"Reconnecting WebSocket (attempt {self.ws_reconnect_attempts}/{self.ws_max_reconnect_attempts})")

        # Stop the WebSocket first
        self.stop_websocket()

        # Start the WebSocket again
        if self.start_websocket():
            if self.logger:
                self.logger.info("WebSocket reconnected successfully")
            return True
        else:
            if self.logger:
                self.logger.error("Failed to reconnect WebSocket")
            return False

    def _resubscribe_to_topics(self):
        """
        Resubscribe to all previously subscribed topics after reconnection.

        Returns:
            bool: True if all resubscriptions were successful, False otherwise.
        """
        if not self.ws_enabled or self.ws_client is None:
            if self.logger:
                self.logger.warning("WebSocket not started, cannot resubscribe")
            return False

        if not self.ws_subscribed_topics:
            if self.logger:
                self.logger.debug("No topics to resubscribe to")
            return True

        success = True
        for topic_type, symbol, interval in self.ws_subscribed_topics:
            try:
                if self.logger:
                    self.logger.debug(f"Resubscribing to {topic_type} for {symbol} {interval if interval else ''}")

                if topic_type == "kline":
                    if not self.subscribe_kline(symbol, interval):
                        if self.logger:
                            self.logger.warning(f"Failed to resubscribe to kline data for {symbol} ({interval})")
                        success = False
                elif topic_type == "ticker":
                    if not self.subscribe_ticker(symbol):
                        if self.logger:
                            self.logger.warning(f"Failed to resubscribe to ticker data for {symbol}")
                        success = False
            except Exception as e:
                self._log_error(e, f"Failed to resubscribe to {topic_type} for {symbol} {interval if interval else ''}")
                success = False

        if self.logger:
            if success:
                self.logger.info("Successfully resubscribed to all topics")
            else:
                self.logger.warning("Some topics failed to resubscribe")

        return success

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
            # In PyBit V5 API, we can't directly unsubscribe from a topic
            # So we just remove our local references to it

            # Remove from subscribed topics for reconnection
            if topic.startswith("kline."):
                # Topic format: kline.{interval}.{symbol}
                parts = topic.split('.')
                if len(parts) == 3:
                    interval = parts[1]
                    symbol = parts[2]
                    self.ws_subscribed_topics.discard(("kline", symbol, interval))
            elif topic.startswith("tickers."):
                # Topic format: tickers.{symbol}
                parts = topic.split('.')
                if len(parts) == 2:
                    symbol = parts[1]
                    self.ws_subscribed_topics.discard(("ticker", symbol, None))

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

        # Check if we're subscribed to this topic
        # In PyBit V5 API, we can't directly check if we're subscribed to a topic
        # So we use our local ws_callbacks dictionary to track subscriptions
        is_subscribed = topic in self.ws_callbacks

        # Subscribe if not subscribed
        if not is_subscribed:
            if self.logger:
                self.logger.debug(f"Not subscribed to {topic}, attempting to subscribe")
            try:
                # Check if PyBit already has this subscription
                # This is a workaround for PyBit not providing a way to check subscriptions
                if hasattr(self.ws_client, '_callback_directory'):
                    callback_directory = self.ws_client._callback_directory
                    if topic in callback_directory:
                        if self.logger:
                            self.logger.debug(f"PyBit already subscribed to {topic}, adding to local tracking")
                        # Add to our local tracking
                        self.ws_callbacks[topic] = None
                        is_subscribed = True

                # Only try to subscribe if we're not already subscribed
                if not is_subscribed:
                    # The subscribe_kline method now handles the "already subscribed" error internally
                    if not self.subscribe_kline(symbol, interval):
                        if self.logger:
                            self.logger.warning("Failed to subscribe to kline data, falling back to REST API")
                        return self.get_klines(symbol, interval)
            except Exception as e:
                # For errors, log and return None
                self._log_error(e, f"Failed to subscribe to kline data for {symbol} ({interval})")
                if self.logger:
                    self.logger.warning("Falling back to REST API after subscription error")
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

            # Check if kline_data is a list (new format) or a dict (old format)
            if isinstance(kline_data, list) and len(kline_data) > 0:
                kline_data = kline_data[0]  # Take the first item if it's a list

            if not isinstance(kline_data, dict):
                if self.logger:
                    self.logger.warning(f"Unexpected kline data format: {type(kline_data)}, falling back to REST API")
                return self.get_klines(symbol, interval)

            if self.logger:
                self.logger.debug(f"Received WebSocket data for {symbol} ({interval}): {kline_data}")

            # Create DataFrame for the real-time candle
            try:
                # Create a dictionary with the data
                candle_data = {
                    "timestamp": pd.to_datetime(int(kline_data.get("start", 0)), unit="ms"),
                    "open": float(kline_data.get("open", 0)),
                    "high": float(kline_data.get("high", 0)),
                    "low": float(kline_data.get("low", 0)),
                    "close": float(kline_data.get("close", 0)),
                    "volume": float(kline_data.get("volume", 0)),
                    "turnover": float(kline_data.get("turnover", 0))
                }

                # Add confirm column with default value True if not present in the data
                if "confirm" in kline_data:
                    candle_data["confirm"] = kline_data.get("confirm", "1") == "1"
                else:
                    candle_data["confirm"] = True

                # Create DataFrame
                df = pd.DataFrame([candle_data])
            except (ValueError, TypeError) as e:
                if self.logger:
                    self.logger.error(f"Error creating DataFrame from WebSocket data: {e}")
                    self.logger.error(f"Raw WebSocket data: {kline_data}")
                return self.get_klines(symbol, interval)

            # Get historical data to combine with real-time data
            # Use get_macd_data method which handles caching and calculation
            historical_df = self.get_macd_data(symbol, interval)
            if historical_df is None or historical_df.empty:
                if self.logger:
                    self.logger.warning("Failed to get historical data with MACD to combine with real-time data")
                # Try to get just the historical data without MACD
                historical_df = self.get_klines(symbol, interval)
                if historical_df is None or historical_df.empty:
                    if self.logger:
                        self.logger.warning("Failed to get any historical data to combine with real-time data")
                    return df  # Return just the real-time candle if we can't get historical data

                # Calculate MACD for the real-time candle
                df = self.calculate_macd(df)

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
