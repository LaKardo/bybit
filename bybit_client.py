import time
import pandas as pd
from pybit.unified_trading import HTTP, WebSocket
import config
import os
import pickle
import threading
import json
import functools
from utils import is_invalid_api_key
from collections import defaultdict
from rate_limiter import RateLimiter
from circuit_breaker import CircuitBreakerRegistry


class BybitAPIClient:
    def __init__(self, api_key=None, api_secret=None, logger=None):
        self.api_key = api_key or config.API_KEY
        self.api_secret = api_secret or config.API_SECRET
        self.logger = logger
        self.client = HTTP(
            testnet=False,
            api_key=self.api_key,
            api_secret=self.api_secret,
            recv_window=5000
        )
        self.macd_fast = config.MACD_FAST
        self.macd_slow = config.MACD_SLOW
        self.macd_signal = config.MACD_SIGNAL
        self.macd_adjust = False
        self.macd_price_col = 'close'
        self.macd_data = defaultdict(dict)
        self.macd_last_update = defaultdict(int)
        self.macd_cache_ttl = 60
        import traceback
        self.traceback = traceback
        if self.logger:
            self.logger.info("Подключение к Bybit")
            self.logger.info(
                f"API Key: {self.api_key[:5]}...{self.api_key[-5:] if len(self.api_key) > 10 else ''}"
            )
        self.test_connection()
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.ws_client = None
        self.ws_enabled = False
        self.ws_callbacks = {}
        self.ws_data = {}
        self.ws_lock = threading.Lock()
        self.cache_enabled = True
        self.cache_expiry = 60 * 60
        self.ws_enabled = False
        self.ws_client = None
        self.ws_callbacks = {}
        self.ws_data = {}
        self.ws_lock = threading.Lock()
        self.ws_thread = None
        self.ws_reconnect_attempts = 0
        self.ws_max_reconnect_attempts = 5
        self.ws_reconnect_delay = 5
        self.ws_last_reconnect_time = 0
        self.ws_subscribed_topics = set()
        self.rate_limiter = None
        try:
            if getattr(config, 'RATE_LIMITING_ENABLED', False):
                self.rate_limiter = RateLimiter(logger=self.logger)
                if hasattr(config, 'RATE_LIMITS') and isinstance(config.RATE_LIMITS, dict):
                    for key, (max_tokens, interval) in config.RATE_LIMITS.items():
                        self.rate_limiter.add_limit(key, max_tokens, interval)
                if self.logger:
                    self.logger.info(f"Rate limiter initialized with limits: {self.rate_limiter.get_limits()}")
            else:
                if self.logger:
                    self.logger.info("Rate limiting is disabled in config")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize rate limiter: {e}")
                self.logger.error("Rate limiting will be disabled")
            self.rate_limiter = None
        self.circuit_breaker_registry = None
        try:
            if getattr(config, 'CIRCUIT_BREAKER_ENABLED', False):
                self.circuit_breaker_registry = CircuitBreakerRegistry(logger=self.logger)
                if self.logger:
                    self.logger.info("Circuit breaker registry initialized")
            else:
                if self.logger:
                    self.logger.info("Circuit breaker is disabled in config")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize circuit breaker: {e}")
                self.logger.error("Circuit breaker will be disabled")
            self.circuit_breaker_registry = None
        if self.logger:
            self.logger.info("Bybit API client initialized")

    def rate_limited(rate_limit_key="default", tokens=1):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                if hasattr(self, 'rate_limiter') and self.rate_limiter is not None:
                    timeout = kwargs.pop('rate_limit_timeout', None)
                    if not self.rate_limiter.limit(rate_limit_key, tokens, block=True, timeout=timeout):
                        if self.logger:
                            self.logger.warning(f"Rate limit exceeded for {rate_limit_key}, request blocked")
                        return {"retCode": -1, "retMsg": f"Rate limit exceeded for {rate_limit_key}"}
                return func(self, *args, **kwargs)
            return wrapper
        return decorator
    def circuit_protected(circuit_name=None):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                _circuit_name = circuit_name or func.__name__
                if hasattr(self, 'circuit_breaker_registry') and self.circuit_breaker_registry is not None:
                    circuit_breaker = self.circuit_breaker_registry.get_circuit_breaker(_circuit_name)
                    if not circuit_breaker.allow_request():
                        if self.logger:
                            self.logger.warning(f"Circuit '{_circuit_name}' is open, request blocked")
                        return {"retCode": -1, "retMsg": f"Circuit '{_circuit_name}' is open, request blocked"}
                    try:
                        result = func(self, *args, **kwargs)
                        if isinstance(result, dict) and result.get("retCode", 0) == 0:
                            circuit_breaker.record_success()
                        else:
                            circuit_breaker.record_error()
                        return result
                    except Exception as e:
                        circuit_breaker.record_error()
                        raise
                else:
                    return func(self, *args, **kwargs)
            return wrapper
        return decorator
    def _log_error(self, error, message, include_traceback=True, log_level="error"):
        """
        Enhanced error logging method using Python 3.11's improved exception handling.

        Python 3.11 provides more detailed exception information including better error messages,
        more precise error locations, and exception notes.
        """
        if not self.logger:
            return

        # Get enhanced error information for Python 3.11+
        import sys
        if isinstance(error, Exception) and sys.version_info >= (3, 11):
            # Get exception notes if available (Python 3.11+)
            notes = getattr(error, "__notes__", [])
            note_str = f" | Notes: {'; '.join(notes)}" if notes else ""

            # Check for exception cause
            cause_str = ""
            if hasattr(error, "__cause__") and error.__cause__:
                cause_str = f" | Caused by: {error.__cause__.__class__.__name__}: {error.__cause__}"

            error_msg = f"{message}: {error}{note_str}{cause_str}"
        else:
            error_msg = f"{message}: {error}"

        # Get caller information for better context
        import inspect
        caller_frame = inspect.currentframe().f_back
        caller_function = caller_frame.f_code.co_name if caller_frame else "unknown"
        caller_line = caller_frame.f_lineno if caller_frame else 0
        context_msg = f"[{caller_function}:{caller_line}] {error_msg}"

        # Log at appropriate level
        if log_level == "debug":
            self.logger.debug(context_msg)
        elif log_level == "info":
            self.logger.info(context_msg)
        elif log_level == "warning":
            self.logger.warning(context_msg)
        else:
            self.logger.error(context_msg)

        # Include detailed traceback if requested
        if include_traceback:
            if sys.version_info >= (3, 11) and isinstance(error, Exception):
                # Python 3.11+ provides more detailed traceback with better formatting
                try:
                    tb_str = "".join(self.traceback.format_exception(type(error), error, error.__traceback__))
                    self.logger.error(f"Detailed error: {tb_str}")
                except Exception:
                    self.logger.error(f"Detailed error: {self.traceback.format_exc()}")
            else:
                self.logger.error(f"Detailed error: {self.traceback.format_exc()}")

        # Include system information for critical errors
        if log_level == "critical":
            import platform
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
        if value is None:
            if self.logger:
                self.logger.debug(f"Field '{field_name}' is None, using default value {default}")
            return default
        try:
            if isinstance(value, str) and not value.strip():
                if self.logger:
                    self.logger.debug(f"Field '{field_name}' is empty string, using default value {default}")
                return default
            result = float(value)
            return result
        except (ValueError, TypeError) as e:
            if self.logger:
                self.logger.warning(f"Could not convert '{field_name}' value '{value}' to float: {e}. Using default value {default}")
            return default
    def _handle_response(self, response, action):
        if not response:
            if self.logger:
                self.logger.warning(f"Empty response from {action}")
            return None
        ret_code = response.get("retCode")
        ret_msg = response.get("retMsg", "Unknown error")
        if ret_code == 0:
            if self.logger:
                self.logger.debug(f"API {action} successful")
            return response.get("result")
        error_msg = f"API {action} failed: {ret_msg} (code: {ret_code})"
        if self.logger:
            self.logger.error(error_msg)
            self.logger.debug(f"Full response: {response}")
            if ret_code in [401, 10003, 10004, 10005, 10006]:
                self.logger.error(f"Authentication error detected (code: {ret_code}). Please check your API keys.")
                self.logger.error(f"This may be due to invalid API keys, expired keys, or insufficient permissions.")
            elif ret_code in [10018, 10019, 10020, 10021, 429]:
                self.logger.error(f"Rate limit exceeded (code: {ret_code}). Please reduce request frequency.")
                self.logger.error(f"Consider implementing rate limiting in your application.")
            elif ret_code in [500, 502, 503, 504, 10002]:
                self.logger.error(f"Server error detected (code: {ret_code}). This is likely a temporary issue.")
                self.logger.error(f"Please try again later or check Bybit status page.")
            elif ret_code in [10001, 10007, 10010, 10011, 10012, 10013, 10014, 10015, 10016, 10017]:
                self.logger.error(f"Parameter error detected (code: {ret_code}). Please check your request parameters.")
                self.logger.error(f"Error details: {ret_msg}")
            elif ret_code == -1 and "Authentication error" in str(ret_msg):
                self.logger.error(f"Authentication error detected. Please check your API keys.")
        return None
    def _retry_api_call(self, func, *args, **kwargs):
        max_retries = config.MAX_RETRIES
        retry_delay = config.RETRY_DELAY
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)
        perf_tracking_id = None
        if self.logger and hasattr(self.logger, 'start_performance_tracking'):
            perf_tracking_id = self.logger.start_performance_tracking(f"api_call_{func_name}")
        if config.DRY_RUN and is_invalid_api_key(self.api_key, self.api_secret):
            if self.logger:
                self.logger.error("API keys are invalid. Please set valid API keys in .env file.")
            return {"retCode": -1, "retMsg": "Invalid API keys"}
        retryable_errors = [
            "timeout", "timed out", "connection", "socket", "reset", "broken pipe",
            "too many requests", "rate limit", "429", "503", "502", "500", "504",
            "server error", "maintenance", "overloaded", "unavailable", "busy"
        ]
        non_retryable_errors = [
            "invalid api key", "api key expired", "api key not found", "invalid signature",
            "permission denied", "unauthorized", "auth failed", "authentication failed",
            "not authorized", "access denied", "forbidden", "403", "401",
            "invalid parameter", "parameter error", "invalid argument", "bad request", "400"
        ]
        context = {
            "function": func_name,
            "args": str(args),
            "kwargs": str(kwargs),
            "max_retries": max_retries,
            "retry_delay": retry_delay
        }
        for attempt in range(max_retries):
            start_time = time.time()
            try:
                if self.logger and attempt > 0:
                    self.logger.debug(f"Retry attempt {attempt+1}/{max_retries} for {func_name}", extra={"retry_attempt": attempt+1})
                    if hasattr(self.logger, 'add_performance_checkpoint') and perf_tracking_id:
                        self.logger.add_performance_checkpoint(perf_tracking_id, f"retry_attempt_{attempt+1}")
                response = func(*args, **kwargs)
                if hasattr(self.logger, 'add_performance_checkpoint') and perf_tracking_id:
                    self.logger.add_performance_checkpoint(perf_tracking_id, "api_call_completed")
                duration = time.time() - start_time
                if hasattr(self.logger, 'log_api_call'):
                    status_code = response.get("retCode") if isinstance(response, dict) else None
                    error = response.get("retMsg") if isinstance(response, dict) and response.get("retCode") != 0 else None
                    self.logger.log_api_call(
                        method="CALL",
                        endpoint=func_name,
                        params=kwargs,
                        response=response,
                        status_code=status_code,
                        error=error,
                        duration=duration
                    )
                if response and isinstance(response, dict):
                    ret_code = response.get("retCode")
                    ret_msg = response.get("retMsg", "Unknown error")
                    if ret_code in [401, 10003, 10004, 10005, 10006, 10007, 10008, 10009]:
                        error_context = {**context, "error_type": "authentication", "ret_code": ret_code, "ret_msg": ret_msg}
                        if self.logger:
                            if hasattr(self.logger, 'log_error_with_context'):
                                self.logger.log_error_with_context(f"Authentication error: {ret_msg}", error_context)
                            else:
                                self.logger.error(f"Authentication error: {ret_msg}")
                                self.logger.error(f"Please check your API keys in config.py")
                        return {"retCode": -1, "retMsg": f"Authentication error: {ret_msg}. Please check your API keys."}
                    if ret_code in [10018, 10019, 10020, 10021, 429]:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            if self.logger:
                                self.logger.warning(f"Rate limit hit, waiting {wait_time}s before retry: {ret_msg}",
                                                  extra={"rate_limit_error": True, "wait_time": wait_time})
                            time.sleep(wait_time)
                            continue
                    if ret_code in [500, 502, 503, 504, 10002, 10010, 10011, 10012, 10013, 10014, 10015, 10016, 10017]:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            if self.logger:
                                self.logger.warning(f"Server error, waiting {wait_time}s before retry: {ret_msg}",
                                                  extra={"server_error": True, "wait_time": wait_time})
                            time.sleep(wait_time)
                            continue
                if hasattr(self.logger, 'end_performance_tracking') and perf_tracking_id:
                    self.logger.end_performance_tracking(perf_tracking_id, {
                        "success": True,
                        "duration": duration,
                        "attempts": attempt + 1
                    })
                return response
            except Exception as e:
                error_str = str(e).lower()
                is_retryable = any(err in error_str for err in retryable_errors)
                is_non_retryable = any(err in error_str for err in non_retryable_errors)
                duration = time.time() - start_time
                if hasattr(self.logger, 'add_performance_checkpoint') and perf_tracking_id:
                    self.logger.add_performance_checkpoint(perf_tracking_id, f"error_attempt_{attempt+1}")
                if hasattr(self.logger, 'log_api_call'):
                    self.logger.log_api_call(
                        method="CALL",
                        endpoint=func_name,
                        params=kwargs,
                        response=None,
                        status_code=None,
                        error=str(e),
                        duration=duration
                    )
                if is_non_retryable:
                    error_context = {**context, "error_type": "non_retryable", "error": str(e)}
                    if self.logger:
                        if hasattr(self.logger, 'log_error_with_context'):
                            self.logger.log_error_with_context(f"Non-retryable error in {func_name}", error_context)
                        else:
                            self.logger.error(f"Non-retryable error in {func_name}: {e}")
                            self.logger.error(f"Please check your API keys and parameters")
                    if hasattr(self.logger, 'end_performance_tracking') and perf_tracking_id:
                        self.logger.end_performance_tracking(perf_tracking_id, {
                            "success": False,
                            "error_type": "non_retryable",
                            "duration": duration,
                            "attempts": attempt + 1
                        })
                    return {"retCode": -1, "retMsg": f"API error: {e}"}
                if attempt < max_retries - 1 and is_retryable:
                    wait_time = retry_delay * (2 ** attempt)
                    if self.logger:
                        self.logger.warning(f"API call failed, retrying in {wait_time}s: {e}",
                                          extra={"retryable_error": True, "wait_time": wait_time, "attempt": attempt+1})
                    time.sleep(wait_time)
                else:
                    error_context = {**context, "error_type": "max_retries_exceeded", "error": str(e), "attempts": attempt+1}
                    if self.logger:
                        if hasattr(self.logger, 'log_error_with_context'):
                            self.logger.log_error_with_context(f"API call to {func_name} failed after {attempt+1} attempts", error_context)
                        else:
                            self.logger.error(f"API call to {func_name} failed after {attempt+1} attempts: {e}")
                            import traceback
                            self.logger.error(f"Detailed error: {traceback.format_exc()}")
                            self.logger.error(f"Args: {args}, Kwargs: {kwargs}")
                    if hasattr(self.logger, 'end_performance_tracking') and perf_tracking_id:
                        self.logger.end_performance_tracking(perf_tracking_id, {
                            "success": False,
                            "error_type": "max_retries_exceeded",
                            "duration": duration,
                            "attempts": attempt + 1
                        })
                    if ("401" in error_str and "status code" in error_str) or \
                       "api key is invalid" in error_str or \
                       "errcode: 401" in error_str or \
                       ("http status code is not 200" in error_str and "authentication" in error_str):
                        auth_error_context = {**context, "error_type": "authentication", "error": str(e)}
                        if self.logger:
                            if hasattr(self.logger, 'log_error_with_context'):
                                self.logger.log_error_with_context(f"Authentication error", auth_error_context)
                            else:
                                self.logger.error(f"Authentication error: {e}")
                                self.logger.error(f"Please check your API keys in config.py")
                        return {"retCode": -1, "retMsg": f"Authentication error: {e}. Please check your API keys."}
                    return {"retCode": -1, "retMsg": f"API error: {e}"}
    def get_server_time(self):
        try:
            response = self.client.get_server_time()
            if response and response.get("retCode") == 0:
                server_time = response.get("result", {}).get("timeNano")
                if server_time:
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
        if config.DRY_RUN and is_invalid_api_key(self.api_key, self.api_secret):
            if self.logger:
                self.logger.info("Пропуск проверки API подключения в демо-режиме с недействительными API ключами")
            return True
        try:
            server_time = self.get_server_time()
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
                    local_time = int(time.time() * 1000)
                    time_diff = abs(local_time - server_time)
                    if time_diff > 1000:
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
        return f"{symbol}_{interval}_{limit}"
    def _get_cache_path(self, cache_key):
        return os.path.join(self.cache_dir, f"{cache_key}.pkl")
    def _is_cache_valid(self, cache_path):
        if not os.path.exists(cache_path):
            return False
        cache_time = os.path.getmtime(cache_path)
        current_time = time.time()
        return (current_time - cache_time) < self.cache_expiry
    def _load_from_cache(self, cache_path):
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
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(df, f)
            if self.logger:
                self.logger.debug(f"Saved klines data to cache: {cache_path}")
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to save to cache: {e}")
    def calculate_macd(self, df, start_idx=None, end_idx=None, force_recalculate=False):
        if self.logger:
            self.logger.debug(f"Calculating MACD with parameters: fast={self.macd_fast}, slow={self.macd_slow}, signal={self.macd_signal}")
        if not force_recalculate and 'macd' in df.columns and 'macd_signal' in df.columns and 'macd_hist' in df.columns:
            if start_idx is None and end_idx is None:
                if self.logger:
                    self.logger.debug("MACD columns already exist, skipping calculation")
                return df
        try:
            min_periods = max(self.macd_slow, self.macd_fast, self.macd_signal)
            if start_idx is None:
                start_idx = 0
            if end_idx is None:
                end_idx = len(df)
            start_idx = max(0, start_idx)
            end_idx = min(len(df), end_idx)
            if len(df) < min_periods:
                if self.logger:
                    self.logger.warning(f"Not enough data for MACD calculation. Need at least {min_periods} rows, got {len(df)}. Using default values.")
                    self.logger.warning(f"This may be due to insufficient historical data available for the selected timeframe.")
                    self.logger.warning(f"Try using a shorter timeframe or waiting for more data to accumulate.")
                if 'macd' not in df.columns:
                    df['macd'] = 0.0
                if 'macd_signal' not in df.columns:
                    df['macd_signal'] = 0.0
                if 'macd_hist' not in df.columns:
                    df['macd_hist'] = 0.0
                return df
            if self.macd_price_col not in df.columns:
                if self.logger:
                    self.logger.warning(f"Price column '{self.macd_price_col}' not found, using 'close' instead")
                self.macd_price_col = 'close'
            if df[self.macd_price_col].isna().any():
                if self.logger:
                    self.logger.warning(f"Price column '{self.macd_price_col}' contains NaN values, filling with forward fill")
                df[self.macd_price_col] = df[self.macd_price_col].fillna(method='ffill').fillna(method='bfill')
            import pandas_ta as ta
            macd_result = ta.macd(
                df[self.macd_price_col],
                fast=self.macd_fast,
                slow=self.macd_slow,
                signal=self.macd_signal
            )
            macd_col = f'MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'
            signal_col = f'MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'
            hist_col = f'MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'
            df['macd'] = macd_result[macd_col]
            df['macd_signal'] = macd_result[signal_col]
            df['macd_hist'] = macd_result[hist_col]
            if self.logger:
                self.logger.debug("MACD calculated successfully using pandas_ta")
            df['macd'] = df['macd'].fillna(0.0)
            df['macd_signal'] = df['macd_signal'].fillna(0.0)
            df['macd_hist'] = df['macd_hist'].fillna(0.0)
        except Exception as e:
            self._log_error(e, "Failed to calculate MACD")
            if 'macd' not in df.columns:
                df['macd'] = 0.0
            if 'macd_signal' not in df.columns:
                df['macd_signal'] = 0.0
            if 'macd_hist' not in df.columns:
                df['macd_hist'] = 0.0
        return df
    @rate_limited(rate_limit_key="market", tokens=1)
    @circuit_protected(circuit_name="get_klines")
    def get_klines(self, symbol=None, interval=None, limit=None):
        symbol = symbol or config.SYMBOL
        interval = interval or config.TIMEFRAME
        min_periods = max(self.macd_slow, self.macd_fast, self.macd_signal)
        min_required = min_periods * 3
        if limit is None or limit < min_required:
            limit = min_required
        if self.logger:
            self.logger.debug(f"Getting {limit} klines for {symbol} ({interval}). Minimum required for MACD: {min_required}")
        if self.cache_enabled:
            cache_key = self._get_cache_key(symbol, interval, limit)
            cache_path = self._get_cache_path(cache_key)
            if self._is_cache_valid(cache_path):
                df = self._load_from_cache(cache_path)
                if df is not None and not df.empty:
                    if self.logger:
                        self.logger.debug(f"Using cached data for {symbol} ({interval})")
                    return df
        for attempt, days_ago in enumerate([7, 30, 3, 1]):
            try:
                end_time = int(time.time() * 1000)
                start_time = end_time - (days_ago * 24 * 60 * 60 * 1000)
                if self.logger:
                    self.logger.debug(f"Attempt {attempt+1}: Fetching klines for {symbol} ({interval}) from {days_ago} days ago")
                params = {
                    "category": "linear",
                    "symbol": symbol,
                    "interval": interval,
                    "start": start_time,
                    "end": end_time,
                    "limit": min(limit, 1000)
                }
                if self.logger:
                    self.logger.debug(f"Get klines parameters: {params}")
                response = self._retry_api_call(
                    self.client.get_kline,
                    **params
                )
                if self.logger:
                    self.logger.debug(f"API response status for klines: {response.get('retCode') if response else 'No response'}")
                if not response or not response.get("result"):
                    if self.logger:
                        self.logger.warning(f"No klines data returned for {symbol} ({interval}). Response: {response}")
                    continue
                if response.get("retCode") != 0:
                    if response.get("retCode") == -1 and \
                       "Authentication error" in str(response.get("retMsg", "")) and \
                       "OK" in str(response):
                        if self.logger:
                            self.logger.warning(f"Ignoring false authentication error for {symbol} ({interval}). Response: {response}")
                    else:
                        if self.logger:
                            self.logger.warning(f"API returned non-zero retCode for {symbol} ({interval}). Response: {response}")
                        continue
                klines_data = response.get("result", {}).get("list", [])
                if not klines_data:
                    if self.logger:
                        self.logger.warning(f"Empty klines data for {symbol} ({interval}) from {days_ago} days ago.")
                    continue
                if len(klines_data) > 0 and len(klines_data[0]) == 7:
                    df = pd.DataFrame(klines_data, columns=[
                        "timestamp", "open", "high", "low", "close", "volume", "turnover"
                    ])
                    df["confirm"] = True
                else:
                    df = pd.DataFrame(klines_data, columns=[
                        "timestamp", "open", "high", "low", "close", "volume", "turnover", "confirm"
                    ])
                for col in ["open", "high", "low", "close", "volume", "turnover"]:
                    try:
                        df[col] = pd.to_numeric(df[col])
                    except Exception as e:
                        if self.logger:
                            self.logger.warning(f"Error converting column {col} to numeric: {e}. Using original values.")
                try:
                    df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error converting timestamp to datetime: {e}. Using original values.")
                try:
                    df["confirm"] = df["confirm"] == "1"
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error converting confirm to boolean: {e}. Using original values.")
                try:
                    df = df.sort_values("timestamp").reset_index(drop=True)
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error sorting by timestamp: {e}. Using original order.")
                if self.logger:
                    self.logger.info(f"Successfully retrieved {len(df)} klines for {symbol} ({interval}) from {days_ago} days ago")
                if self.cache_enabled and df is not None and not df.empty:
                    cache_key = self._get_cache_key(symbol, interval, limit)
                    cache_path = self._get_cache_path(cache_key)
                    self._save_to_cache(df, cache_path)
                return df
            except Exception as e:
                self._log_error(e, f"Failed to get klines on attempt {attempt+1} for {days_ago} days ago")
        if self.logger:
            self.logger.error(f"All attempts to get klines for {symbol} ({interval}) failed")
        try:
            if self.logger:
                self.logger.debug(f"Final attempt: Fetching klines for {symbol} ({interval}) with default time range")
            params = {
                "category": "linear",
                "symbol": symbol,
                "interval": interval,
                "limit": min(limit, 1000)
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
            if response.get("retCode") != 0:
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
            if len(klines_data) > 0 and len(klines_data[0]) == 7:
                df = pd.DataFrame(klines_data, columns=[
                    "timestamp", "open", "high", "low", "close", "volume", "turnover"
                ])
                df["confirm"] = True
            else:
                df = pd.DataFrame(klines_data, columns=[
                    "timestamp", "open", "high", "low", "close", "volume", "turnover", "confirm"
                ])
            for col in ["open", "high", "low", "close", "volume", "turnover"]:
                try:
                    df[col] = pd.to_numeric(df[col])
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error converting column {col} to numeric: {e}. Using original values.")
            try:
                df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error converting timestamp to datetime: {e}. Using original values.")
            try:
                df["confirm"] = df["confirm"] == "1"
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error converting confirm to boolean: {e}. Using original values.")
            try:
                df = df.sort_values("timestamp").reset_index(drop=True)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error sorting by timestamp: {e}. Using original order.")
            if self.logger:
                self.logger.info(f"Final attempt succeeded: Retrieved {len(df)} klines for {symbol} ({interval})")
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
        if self.logger:
            self.logger.debug("Getting account information")
        try:
            response = self._retry_api_call(
                self.client.get_account_info
            )
            if not response or response.get("retCode") != 0 or not response.get("result"):
                if self.logger:
                    self.logger.warning("No account information returned")
                return None
            account_info = response.get("result", {})
            if self.logger:
                self.logger.info(f"Account type: {account_info.get('unifiedMarginStatus')}")
                self.logger.info(f"Account mode: {account_info.get('marginMode')}")
            return account_info
        except Exception as e:
            self._log_error(e, "Failed to get account information")
            return None
    @rate_limited(rate_limit_key="account", tokens=1)
    @circuit_protected(circuit_name="get_wallet_balance")
    def get_wallet_balance(self):
        if self.logger:
            self.logger.debug("Getting wallet balance")
        try:
            response = self._retry_api_call(
                self.client.get_wallet_balance,
                accountType="UNIFIED",
                coin="USDT"
            )
            if not response or response.get("retCode") != 0 or not response.get("result"):
                if self.logger:
                    self.logger.warning("No wallet balance data returned.")
                return None
            balance_data = response.get("result", {}).get("list", [])
            if not balance_data:
                if self.logger:
                    self.logger.warning("Empty wallet balance data.")
                return None
            usdt_balance = None
            for coin_balance in balance_data:
                if coin_balance.get("coin") == "USDT":
                    usdt_balance = coin_balance
                    break
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
            try:
                wallet_balance = self._safe_float_conversion(usdt_balance.get("walletBalance"), "walletBalance", 0)
                available_to_withdraw = usdt_balance.get("availableToWithdraw")
                if available_to_withdraw is None or (isinstance(available_to_withdraw, str) and not available_to_withdraw.strip()):
                    if self.logger:
                        self.logger.debug(f"Field 'availableToWithdraw' is {available_to_withdraw}, using walletBalance value {wallet_balance}")
                    available_balance = wallet_balance
                else:
                    try:
                        available_balance = float(available_to_withdraw)
                    except (ValueError, TypeError):
                        if self.logger:
                            self.logger.debug(f"Could not convert 'availableToWithdraw' value '{available_to_withdraw}' to float. Using walletBalance {wallet_balance}")
                        available_balance = wallet_balance
                unrealized_pnl = self._safe_float_conversion(usdt_balance.get("unrealisedPnl"), "unrealisedPnl", 0)
                result = {
                    "available_balance": available_balance,
                    "wallet_balance": wallet_balance,
                    "unrealized_pnl": unrealized_pnl
                }
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
    @rate_limited(rate_limit_key="position", tokens=1)
    @circuit_protected(circuit_name="get_positions")
    def get_positions(self, symbol=None):
        symbol = symbol or config.SYMBOL
        if self.logger:
            self.logger.debug(f"Getting positions for {symbol}")
        try:
            response = self._retry_api_call(
                self.client.get_positions,
                category="linear",
                symbol=symbol,
                settleCoin="USDT"
            )
            if not response or response.get("retCode") != 0:
                if self.logger:
                    self.logger.warning(f"Failed to get positions: {response.get('retMsg', 'Unknown error')}.")
                return None
            positions = response.get("result", {}).get("list", [])
            if not positions:
                if self.logger:
                    self.logger.debug(f"No positions found for {symbol}")
                return []
            result = []
            for pos in positions:
                size = float(pos.get('size', 0))
                if size > 0:
                    result.append({
                        "symbol": symbol,
                        "side": pos.get('side', ''),
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
        symbol = symbol or config.SYMBOL
        if self.logger:
            self.logger.debug(f"Getting ticker for {symbol}")
        if self.ws_enabled and self.ws_client is not None:
            realtime_ticker = self.get_realtime_ticker(symbol)
            if realtime_ticker is not None:
                return realtime_ticker
        try:
            response = self._retry_api_call(
                self.client.get_tickers,
                category="linear",
                symbol=symbol
            )
            if not response or response.get("retCode") != 0 or not response.get("result"):
                if self.logger:
                    self.logger.warning(f"No ticker data found for {symbol}.")
                return None
            tickers = response.get("result", {}).get("list", [])
            if not tickers:
                if self.logger:
                    self.logger.warning(f"Empty ticker data for {symbol}.")
                return None
            ticker = tickers[0]
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
        symbol = symbol or config.SYMBOL
        if self.logger:
            self.logger.debug(f"Getting real-time ticker data for {symbol}")
        if not self.ws_enabled or self.ws_client is None:
            return None
        topic = f"tickers.{symbol}"
        is_subscribed = topic in self.ws_callbacks
        if not is_subscribed:
            if self.logger:
                self.logger.debug(f"Not subscribed to {topic}, attempting to subscribe")
            try:
                if hasattr(self.ws_client, '_callback_directory'):
                    callback_directory = self.ws_client._callback_directory
                    if topic in callback_directory:
                        if self.logger:
                            self.logger.debug(f"PyBit already subscribed to {topic}, adding to local tracking")
                        self.ws_callbacks[topic] = None
                        is_subscribed = True
                if not is_subscribed:
                    if not self.subscribe_ticker(symbol):
                        if self.logger:
                            self.logger.warning(f"Failed to subscribe to ticker data for {symbol}")
                        return None
            except Exception as e:
                if "You have already subscribed to this topic" in str(e):
                    if self.logger:
                        self.logger.debug(f"Already subscribed to {topic} (from exception)")
                    self.ws_callbacks[topic] = None
                else:
                    self._log_error(e, f"Failed to subscribe to ticker data for {symbol}")
                    return None
        with self.ws_lock:
            data = self.ws_data.get(topic)
        if not data:
            if self.logger:
                self.logger.debug(f"No real-time ticker data available for {symbol}")
            return None
        try:
            ticker_data = data.get("data", {})
            if not ticker_data:
                if self.logger:
                    self.logger.warning(f"Empty ticker data received from WebSocket for {symbol}")
                return None
            if isinstance(ticker_data, list) and len(ticker_data) > 0:
                ticker_data = ticker_data[0]
            if not isinstance(ticker_data, dict):
                if self.logger:
                    self.logger.warning(f"Unexpected ticker data format: {type(ticker_data)}")
                return None
            if self.logger:
                self.logger.debug(f"Received WebSocket ticker data for {symbol}")
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
    @rate_limited(rate_limit_key="order", tokens=2)
    @circuit_protected(circuit_name="place_market_order")
    def place_market_order(self, symbol=None, side=None, qty=None, reduce_only=False,
                          take_profit=None, stop_loss=None):
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
            params = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "orderType": "Market",
                "qty": str(qty),
                "reduceOnly": reduce_only,
                "positionIdx": 0
            }
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
            if self.logger:
                self.logger.debug(f"Order parameters: {params}")
            response = self._retry_api_call(
                self.client.place_order,
                **params
            )
            if self.logger:
                self.logger.debug(f"Order response: {response}")
            return self._handle_response(response, "place_market_order")
        except Exception as e:
            self._log_error(e, "Failed to place market order")
            return None
    def set_leverage(self, symbol=None, leverage=None):
        symbol = symbol or config.SYMBOL
        leverage = leverage or config.LEVERAGE
        if config.DRY_RUN:
            if self.logger:
                self.logger.info(f"DRY RUN: Would set leverage to {leverage}x for {symbol}")
            return True
        if self.logger:
            self.logger.info(f"Setting leverage to {leverage}x for {symbol}")
        try:
            if self.logger:
                self.logger.debug(f"Setting leverage parameters: symbol={symbol}, leverage={leverage}")
            response = self._retry_api_call(
                self.client.set_leverage,
                category="linear",
                symbol=symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )
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
    @rate_limited(rate_limit_key="order", tokens=2)
    @circuit_protected(circuit_name="cancel_all_orders")
    def cancel_all_orders(self, symbol=None):
        symbol = symbol or config.SYMBOL
        if config.DRY_RUN:
            if self.logger:
                self.logger.info(f"DRY RUN: Would cancel all orders for {symbol}")
            return True
        if self.logger:
            self.logger.info(f"Cancelling all orders for {symbol}")
        try:
            if self.logger:
                self.logger.debug(f"Cancel all orders parameters: category=linear, symbol={symbol}")
            response = self._retry_api_call(
                self.client.cancel_all_orders,
                category="linear",
                symbol=symbol
            )
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
    @rate_limited(rate_limit_key="order", tokens=3)
    @circuit_protected(circuit_name="close_position")
    def close_position(self, symbol=None):
        symbol = symbol or config.SYMBOL
        if config.DRY_RUN:
            if self.logger:
                self.logger.info(f"DRY RUN: Would close position for {symbol}")
            return True
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
                params = {
                    "category": "linear",
                    "symbol": symbol,
                    "side": side,
                    "orderType": "Market",
                    "qty": str(abs(size)),
                    "reduceOnly": True,
                    "positionIdx": 0
                }
                if self.logger:
                    self.logger.debug(f"Close position parameters: {params}")
                response = self._retry_api_call(
                    self.client.place_order,
                    **params
                )
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
        if self.ws_enabled and self.ws_client is not None:
            if self.logger:
                self.logger.warning("WebSocket already started")
            if self.check_websocket_health():
                return True
            else:
                if self.logger:
                    self.logger.warning("Existing WebSocket connection is unhealthy, restarting...")
                self.stop_websocket()
        try:
            self.ws_reconnect_attempts = 0
            if self.logger:
                self.logger.debug(f"Starting WebSocket with parameters: testnet=False, domain=bybit, channel_type=linear")
            self.ws_client = WebSocket(
                testnet=False,
                api_key=self.api_key,
                api_secret=self.api_secret,
                domain="bybit",
                channel_type="linear"
            )
            self.ws_enabled = True
            self.ws_last_reconnect_time = int(time.time())
            self._resubscribe_to_topics()
            if self.logger:
                self.logger.info("WebSocket started successfully")
            return True
        except Exception as e:
            self._log_error(e, "Failed to start WebSocket")
            if self.logger:
                self.logger.error(f"WebSocket initialization parameters: testnet=False, domain=bybit, channel_type=linear")
            self.ws_client = None
            self.ws_enabled = False
            return False
    def check_websocket_health(self):
        if not self.ws_enabled or self.ws_client is None:
            return False
        try:
            if hasattr(self.ws_client, '_conn'):
                conn = self.ws_client._conn
                if conn is None or not conn.connected:
                    if self.logger:
                        self.logger.warning("WebSocket connection is not connected")
                    return False
            if self.ws_callbacks:
                with self.ws_lock:
                    for topic in self.ws_callbacks.keys():
                        if topic in self.ws_data:
                            return True
                if self.logger:
                    self.logger.warning("WebSocket has subscriptions but no data received")
                return False
            return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error checking WebSocket health: {e}")
            return False
    def stop_websocket(self):
        if not self.ws_enabled or self.ws_client is None:
            if self.logger:
                self.logger.warning("WebSocket not started")
            return True
        try:
            for topic in list(self.ws_callbacks.keys()):
                self.unsubscribe_topic(topic)
            try:
                if hasattr(self.ws_client, 'close') and callable(getattr(self.ws_client, 'close')):
                    self.ws_client.close()
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error closing WebSocket connection: {e}")
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
        if not self.ws_enabled or self.ws_client is None:
            return
        try:
            if not isinstance(message, dict):
                try:
                    message = json.loads(message)
                except json.JSONDecodeError as e:
                    if self.logger:
                        self.logger.warning(f"Failed to parse WebSocket message: {e}")
                    return
            topic = message.get("topic", "")
            if not topic:
                if self.logger:
                    self.logger.debug("Received WebSocket message without topic")
                return
            if topic not in self.ws_callbacks:
                if topic.startswith("kline.") or topic.startswith("tickers."):
                    if self.logger:
                        self.logger.debug(f"Auto-tracking untracked topic: {topic}")
                    self.ws_callbacks[topic] = None
                    if topic.startswith("kline."):
                        parts = topic.split('.')
                        if len(parts) == 3:
                            interval = parts[1]
                            symbol = parts[2]
                            self.ws_subscribed_topics.add(("kline", symbol, interval))
                    elif topic.startswith("tickers."):
                        parts = topic.split('.')
                        if len(parts) == 2:
                            symbol = parts[1]
                            self.ws_subscribed_topics.add(("ticker", symbol, None))
                else:
                    if self.logger:
                        self.logger.debug(f"Ignoring message for untracked topic: {topic}")
                    return
            if self.logger:
                self.logger.debug(f"Received WebSocket message for topic {topic}")
            with self.ws_lock:
                self.ws_data[topic] = message
            if topic.startswith("kline."):
                self.calculate_macd_callback(topic, message)
            callback_func = self.ws_callbacks.get(topic)
            if callback_func is not None and callable(callback_func):
                try:
                    callback_func(message)
                except Exception as callback_error:
                    if self.logger:
                        self.logger.error(f"Error in user callback for topic {topic}: {callback_error}")
        except Exception as e:
            self._log_error(e, "WebSocket callback error")
            if self.logger:
                self.logger.error(f"Error processing WebSocket message: {message if 'message' in locals() else 'Unknown message'}")
    def calculate_macd_callback(self, topic, message):
        try:
            parts = topic.split('.')
            if len(parts) != 3:
                if self.logger:
                    self.logger.warning(f"Invalid kline topic format: {topic}")
                return
            interval = parts[1]
            symbol = parts[2]
            macd_key = f"{symbol}_{interval}"
            current_time = int(time.time())
            last_update_time = self.macd_last_update.get(macd_key, 0)
            cache_valid = (current_time - last_update_time) < self.macd_cache_ttl
            if cache_valid and macd_key in self.macd_data and self.macd_data[macd_key] is not None:
                if self.logger:
                    self.logger.debug(f"Using cached MACD data for {symbol} ({interval}), last updated {current_time - last_update_time}s ago")
                return
            kline_data = message.get("data", {})
            if not kline_data:
                if self.logger:
                    self.logger.warning("Empty kline data received from WebSocket")
                return
            if isinstance(kline_data, list) and len(kline_data) > 0:
                kline_data = kline_data[0]
            if not isinstance(kline_data, dict):
                if self.logger:
                    self.logger.warning(f"Unexpected kline data format: {type(kline_data)}")
                return
            updated_df = self.update_macd_with_new_data(symbol, interval)
            if updated_df is None or updated_df.empty:
                if self.logger:
                    self.logger.warning("Failed to update MACD incrementally, falling back to full calculation")
                historical_df = self.get_klines(symbol, interval)
                if historical_df is None or historical_df.empty:
                    if self.logger:
                        self.logger.warning("Failed to get historical data for MACD calculation")
                    return
                historical_df = self.calculate_macd(historical_df, force_recalculate=True)
                self.macd_data[macd_key] = historical_df
                self.macd_last_update[macd_key] = current_time
            if self.logger:
                self.logger.debug(f"MACD calculated for {symbol} ({interval}) after receiving new data")
        except Exception as e:
            self._log_error(e, "Failed to calculate MACD from WebSocket data")
    def get_macd_data(self, symbol=None, interval=None, force_recalculate=False):
        symbol = symbol or config.SYMBOL
        interval = interval or config.TIMEFRAME
        macd_key = f"{symbol}_{interval}"
        current_time = int(time.time())
        cache_valid = False
        if macd_key in self.macd_data and self.macd_data[macd_key] is not None and not self.macd_data[macd_key].empty:
            last_update_time = self.macd_last_update.get(macd_key, 0)
            cache_valid = (current_time - last_update_time) < self.macd_cache_ttl
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
            min_periods = max(self.macd_slow, self.macd_fast, self.macd_signal)
            min_required = min_periods * 3
            historical_df = self.get_klines(symbol, interval, limit=min_required)
            if historical_df is None or historical_df.empty:
                if self.logger:
                    self.logger.warning(f"Failed to get historical data for {symbol} ({interval})")
                return None
            if len(historical_df) < min_periods:
                if self.logger:
                    self.logger.warning(f"Not enough historical data for MACD calculation. Need at least {min_periods} rows, got {len(historical_df)}.")
                    self.logger.warning(f"This may be due to insufficient historical data available for the selected timeframe.")
                    self.logger.warning(f"Try using a shorter timeframe or waiting for more data to accumulate.")
            historical_df = self.calculate_macd(historical_df, force_recalculate=force_recalculate)
            self.macd_data[macd_key] = historical_df
            self.macd_last_update[macd_key] = current_time
            if self.logger:
                self.logger.debug(f"MACD calculation completed for {symbol} ({interval})")
            return historical_df
    def update_macd_with_new_data(self, symbol=None, interval=None, new_candle=None):
        symbol = symbol or config.SYMBOL
        interval = interval or config.TIMEFRAME
        macd_key = f"{symbol}_{interval}"
        if macd_key not in self.macd_data or self.macd_data[macd_key] is None or self.macd_data[macd_key].empty:
            if self.logger:
                self.logger.debug(f"No existing MACD data for {symbol} ({interval}), calculating from scratch")
            return self.get_macd_data(symbol, interval, force_recalculate=True)
        try:
            df = self.macd_data[macd_key].copy()
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
            new_timestamp = new_candle["timestamp"] if isinstance(new_candle["timestamp"], pd.Timestamp) else pd.to_datetime(new_candle["timestamp"])
            existing_idx = df[df["timestamp"] == new_timestamp].index
            if len(existing_idx) > 0:
                idx = existing_idx[0]
                for key, value in new_candle.items():
                    if key in df.columns:
                        df.at[idx, key] = value
            else:
                new_row = pd.DataFrame([new_candle])
                df = pd.concat([df, new_row]).reset_index(drop=True)
            min_periods = max(self.macd_slow, self.macd_fast, self.macd_signal)
            history_size = max(min_periods * 3, 50)
            start_idx = max(0, len(df) - history_size)
            if len(df) < min_periods:
                if self.logger:
                    self.logger.warning(f"Not enough data for incremental MACD update. Need at least {min_periods} rows, got {len(df)}.")
                    self.logger.warning(f"Falling back to full MACD calculation.")
                return self.get_macd_data(symbol, interval, force_recalculate=True)
            df = self.calculate_macd(df, start_idx=start_idx, end_idx=len(df), force_recalculate=True)
            self.macd_data[macd_key] = df
            self.macd_last_update[macd_key] = int(time.time())
            if self.logger:
                self.logger.debug(f"MACD incrementally updated for {symbol} ({interval})")
            return df
        except Exception as e:
            self._log_error(e, f"Failed to update MACD incrementally for {symbol} ({interval})")
            if self.logger:
                self.logger.warning(f"Falling back to full MACD recalculation for {symbol} ({interval})")
            return self.get_macd_data(symbol, interval, force_recalculate=True)
    def subscribe_kline(self, symbol=None, interval=None, callback=None):
        symbol = symbol or config.SYMBOL
        interval = interval or config.TIMEFRAME
        if not self.ws_enabled or self.ws_client is None:
            if not self.start_websocket():
                return False
        try:
            topic = f"kline.{interval}.{symbol}"
            if topic in self.ws_callbacks:
                if self.logger:
                    self.logger.debug(f"Already subscribed to {topic} (local tracking)")
                return True
            try:
                if hasattr(self.ws_client, '_callback_directory'):
                    callback_directory = self.ws_client._callback_directory
                    if topic in callback_directory:
                        if self.logger:
                            self.logger.debug(f"PyBit already subscribed to {topic}, adding to local tracking")
                        self.ws_callbacks[topic] = None
                        self.ws_subscribed_topics.add(("kline", symbol, interval))
                        return True
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Error checking PyBit subscriptions: {e}")
            self.ws_callbacks[topic] = callback if callback is not None and callable(callback) else None
            if self.logger:
                self.logger.debug(f"Subscribing to kline stream with parameters: interval={interval}, symbol={symbol}")
            try:
                self.ws_client.kline_stream(
                    interval=interval,
                    symbol=symbol,
                    callback=self._ws_callback
                )
                self.ws_subscribed_topics.add(("kline", symbol, interval))
                if self.logger:
                    self.logger.info(f"Subscribed to kline data for {symbol} ({interval})")
                return True
            except Exception as sub_error:
                if "You have already subscribed to this topic" in str(sub_error):
                    if self.logger:
                        self.logger.debug(f"Already subscribed to {topic} (from PyBit exception)")
                    self.ws_subscribed_topics.add(("kline", symbol, interval))
                    return True
                else:
                    if topic in self.ws_callbacks:
                        del self.ws_callbacks[topic]
                    raise sub_error
        except Exception as e:
            self._log_error(e, "Failed to subscribe to kline data")
            if self.logger:
                self.logger.debug(f"Subscription parameters: interval={interval}, symbol={symbol}")
            if "Connection is closed" in str(e) or "Not connected" in str(e):
                self._reconnect_websocket()
            return False
    def subscribe_ticker(self, symbol=None, callback=None):
        symbol = symbol or config.SYMBOL
        if not self.ws_enabled or self.ws_client is None:
            if not self.start_websocket():
                return False
        try:
            topic = f"tickers.{symbol}"
            if topic in self.ws_callbacks:
                if self.logger:
                    self.logger.debug(f"Already subscribed to {topic} (local tracking)")
                return True
            try:
                if hasattr(self.ws_client, '_callback_directory'):
                    callback_directory = self.ws_client._callback_directory
                    if topic in callback_directory:
                        if self.logger:
                            self.logger.debug(f"PyBit already subscribed to {topic}, adding to local tracking")
                        self.ws_callbacks[topic] = None
                        self.ws_subscribed_topics.add(("ticker", symbol, None))
                        return True
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Error checking PyBit subscriptions: {e}")
            self.ws_callbacks[topic] = callback if callback is not None and callable(callback) else None
            if self.logger:
                self.logger.debug(f"Subscribing to ticker stream with parameters: symbol={symbol}")
            try:
                self.ws_client.ticker_stream(
                    symbol=symbol,
                    callback=self._ws_callback
                )
                self.ws_subscribed_topics.add(("ticker", symbol, None))
                if self.logger:
                    self.logger.info(f"Subscribed to ticker data for {symbol}")
                return True
            except Exception as sub_error:
                if "You have already subscribed to this topic" in str(sub_error):
                    if self.logger:
                        self.logger.debug(f"Already subscribed to {topic} (from PyBit exception)")
                    self.ws_subscribed_topics.add(("ticker", symbol, None))
                    return True
                else:
                    if topic in self.ws_callbacks:
                        del self.ws_callbacks[topic]
                    raise sub_error
        except Exception as e:
            self._log_error(e, "Failed to subscribe to ticker data")
            if self.logger:
                self.logger.debug(f"Subscription parameters: symbol={symbol}")
            if "Connection is closed" in str(e) or "Not connected" in str(e):
                self._reconnect_websocket()
            return False
    def _reconnect_websocket(self):
        if self.ws_reconnect_attempts >= self.ws_max_reconnect_attempts:
            if self.logger:
                self.logger.error(f"Failed to reconnect WebSocket after {self.ws_reconnect_attempts} attempts")
                self.logger.error("Maximum reconnection attempts reached. WebSocket will not be reconnected automatically.")
                self.logger.error("Please check your network connection and restart the bot if needed.")
            return False
        current_time = int(time.time())
        time_since_last_reconnect = current_time - self.ws_last_reconnect_time
        reconnect_delay = min(300, self.ws_reconnect_delay * (2 ** self.ws_reconnect_attempts))
        if time_since_last_reconnect < reconnect_delay:
            wait_time = reconnect_delay - time_since_last_reconnect
            if self.logger:
                self.logger.debug(f"Waiting {wait_time}s before reconnecting WebSocket (exponential backoff)")
            time.sleep(wait_time)
        self.ws_reconnect_attempts += 1
        if self.logger:
            self.logger.info(f"Reconnecting WebSocket (attempt {self.ws_reconnect_attempts}/{self.ws_max_reconnect_attempts})")
        self.stop_websocket()
        if self.start_websocket():
            self.ws_reconnect_attempts = 0
            if self.logger:
                self.logger.info("WebSocket reconnected successfully")
            return True
        else:
            if self.logger:
                self.logger.error("Failed to reconnect WebSocket")
                self.logger.info(f"Will try again in {reconnect_delay * 2}s (exponential backoff)")
            return False
    def _resubscribe_to_topics(self):
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
        if not self.ws_enabled or self.ws_client is None:
            if self.logger:
                self.logger.warning("WebSocket not started")
            return True
        try:
            if topic.startswith("kline."):
                parts = topic.split('.')
                if len(parts) == 3:
                    interval = parts[1]
                    symbol = parts[2]
                    self.ws_subscribed_topics.discard(("kline", symbol, interval))
            elif topic.startswith("tickers."):
                parts = topic.split('.')
                if len(parts) == 2:
                    symbol = parts[1]
                    self.ws_subscribed_topics.discard(("ticker", symbol, None))
            if topic in self.ws_callbacks:
                del self.ws_callbacks[topic]
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
        symbol = symbol or config.SYMBOL
        interval = interval or config.TIMEFRAME
        if self.logger:
            self.logger.debug(f"Getting real-time kline data for {symbol} ({interval})")
        if not self.ws_enabled or self.ws_client is None:
            if self.logger:
                self.logger.info("WebSocket not started, falling back to REST API")
            return self.get_klines(symbol, interval)
        topic = f"kline.{interval}.{symbol}"
        is_subscribed = topic in self.ws_callbacks
        if not is_subscribed:
            if self.logger:
                self.logger.debug(f"Not subscribed to {topic}, attempting to subscribe")
            try:
                if hasattr(self.ws_client, '_callback_directory'):
                    callback_directory = self.ws_client._callback_directory
                    if topic in callback_directory:
                        if self.logger:
                            self.logger.debug(f"PyBit already subscribed to {topic}, adding to local tracking")
                        self.ws_callbacks[topic] = None
                        is_subscribed = True
                if not is_subscribed:
                    if not self.subscribe_kline(symbol, interval):
                        if self.logger:
                            self.logger.warning("Failed to subscribe to kline data, falling back to REST API")
                        return self.get_klines(symbol, interval)
            except Exception as e:
                self._log_error(e, f"Failed to subscribe to kline data for {symbol} ({interval})")
                if self.logger:
                    self.logger.warning("Falling back to REST API after subscription error")
                return self.get_klines(symbol, interval)
        with self.ws_lock:
            data = self.ws_data.get(topic)
        if not data:
            if self.logger:
                self.logger.info("No real-time kline data available, falling back to REST API")
            return self.get_klines(symbol, interval)
        try:
            kline_data = data.get("data", {})
            if not kline_data:
                if self.logger:
                    self.logger.warning("Empty kline data received from WebSocket, falling back to REST API")
                return self.get_klines(symbol, interval)
            if isinstance(kline_data, list) and len(kline_data) > 0:
                kline_data = kline_data[0]
            if not isinstance(kline_data, dict):
                if self.logger:
                    self.logger.warning(f"Unexpected kline data format: {type(kline_data)}, falling back to REST API")
                return self.get_klines(symbol, interval)
            if self.logger:
                self.logger.debug(f"Received WebSocket data for {symbol} ({interval}): {kline_data}")
            try:
                candle_data = {
                    "timestamp": pd.to_datetime(int(kline_data.get("start", 0)), unit="ms"),
                    "open": float(kline_data.get("open", 0)),
                    "high": float(kline_data.get("high", 0)),
                    "low": float(kline_data.get("low", 0)),
                    "close": float(kline_data.get("close", 0)),
                    "volume": float(kline_data.get("volume", 0)),
                    "turnover": float(kline_data.get("turnover", 0))
                }
                if "confirm" in kline_data:
                    candle_data["confirm"] = kline_data.get("confirm", "1") == "1"
                else:
                    candle_data["confirm"] = True
                df = pd.DataFrame([candle_data])
            except (ValueError, TypeError) as e:
                if self.logger:
                    self.logger.error(f"Error creating DataFrame from WebSocket data: {e}")
                    self.logger.error(f"Raw WebSocket data: {kline_data}")
                return self.get_klines(symbol, interval)
            historical_df = self.get_macd_data(symbol, interval)
            if historical_df is None or historical_df.empty:
                if self.logger:
                    self.logger.warning("Failed to get historical data with MACD to combine with real-time data")
                historical_df = self.get_klines(symbol, interval)
                if historical_df is None or historical_df.empty:
                    if self.logger:
                        self.logger.warning("Failed to get any historical data to combine with real-time data")
                    return df
                df = self.calculate_macd(df)
            try:
                if historical_df.iloc[-1]["timestamp"] == df.iloc[0]["timestamp"]:
                    historical_df = historical_df.iloc[:-1]
                combined_df = pd.concat([historical_df, df]).reset_index(drop=True)
                if self.logger:
                    self.logger.debug(f"Successfully combined historical ({len(historical_df)} candles) and real-time data")
                return combined_df
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error combining historical and real-time data: {e}")
                return historical_df
        except Exception as e:
            self._log_error(e, "Failed to parse real-time kline data")
            if self.logger:
                self.logger.info("Falling back to REST API after WebSocket error")
            return self.get_klines(symbol, interval)
