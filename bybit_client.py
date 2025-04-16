"""
Bybit API client for the Trading Bot.
Handles all interactions with the Bybit API.
"""

import time
import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import config

class BybitAPIClient:
    """
    Bybit API client for the Trading Bot.
    Handles all interactions with the Bybit API.
    """
    def __init__(self, api_key=None, api_secret=None, testnet=None, logger=None):
        """
        Initialize the Bybit API client.
        
        Args:
            api_key (str, optional): API key. Defaults to config.API_KEY.
            api_secret (str, optional): API secret. Defaults to config.API_SECRET.
            testnet (bool, optional): Use testnet. Defaults to config.TESTNET.
            logger (Logger, optional): Logger instance.
        """
        self.api_key = api_key or config.API_KEY
        self.api_secret = api_secret or config.API_SECRET
        self.testnet = testnet if testnet is not None else config.TESTNET
        self.logger = logger
        
        # Initialize client
        self.client = HTTP(
            testnet=self.testnet,
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        
        if self.logger:
            self.logger.info(f"Bybit API client initialized (testnet: {self.testnet})")
    
    def _handle_response(self, response, action):
        """
        Handle API response.
        
        Args:
            response (dict): API response.
            action (str): Action description.
            
        Returns:
            dict: Response result or None on error.
        """
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
            dict: API response.
        """
        max_retries = config.MAX_RETRIES
        retry_delay = config.RETRY_DELAY
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries - 1:
                    if self.logger:
                        self.logger.warning(f"API call failed, retrying in {retry_delay}s: {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    if self.logger:
                        self.logger.error(f"API call failed after {max_retries} attempts: {e}")
                    raise
    
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
        
        try:
            response = self._retry_api_call(
                self.client.get_kline,
                category="linear",
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            result = self._handle_response(response, "get_klines")
            if not result or "list" not in result:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(result["list"], columns=[
                "timestamp", "open", "high", "low", "close", "volume", 
                "turnover", "confirm"
            ])
            
            # Convert types
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            for col in ["open", "high", "low", "close", "volume", "turnover"]:
                df[col] = pd.to_numeric(df[col])
            
            # Sort by timestamp (oldest first)
            df = df.sort_values("timestamp").reset_index(drop=True)
            
            return df
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get klines: {e}")
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
            response = self._retry_api_call(
                self.client.get_wallet_balance,
                accountType="CONTRACT"
            )
            
            result = self._handle_response(response, "get_wallet_balance")
            if not result or "list" not in result:
                return None
            
            # Find USDT balance
            for account in result["list"]:
                for coin in account["coin"]:
                    if coin["coin"] == "USDT":
                        return {
                            "available_balance": float(coin["availableBalance"]),
                            "wallet_balance": float(coin["walletBalance"]),
                            "unrealized_pnl": float(coin["unrealisedPnl"])
                        }
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get wallet balance: {e}")
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
            response = self._retry_api_call(
                self.client.get_positions,
                category="linear",
                symbol=symbol
            )
            
            result = self._handle_response(response, "get_positions")
            if not result or "list" not in result:
                return None
            
            return result["list"]
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get positions: {e}")
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
            response = self._retry_api_call(
                self.client.get_tickers,
                category="linear",
                symbol=symbol
            )
            
            result = self._handle_response(response, "get_ticker")
            if not result or "list" not in result or not result["list"]:
                return None
            
            return result["list"][0]
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get ticker: {e}")
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
            params = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "orderType": "Market",
                "qty": str(qty),
                "reduceOnly": reduce_only
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
            if self.logger:
                self.logger.error(f"Failed to place market order: {e}")
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
            if self.logger:
                self.logger.error(f"Failed to set leverage: {e}")
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
            if self.logger:
                self.logger.error(f"Failed to cancel all orders: {e}")
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
                if self.logger:
                    self.logger.error(f"Failed to close position: {e}")
                return False
        
        return True
