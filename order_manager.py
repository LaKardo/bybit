import config
class OrderManager:
    def __init__(self, bybit_client, risk_manager, logger=None, notifier=None):
        self.bybit_client = bybit_client
        self.risk_manager = risk_manager
        self.logger = logger
        self.notifier = notifier
        self.symbol = config.SYMBOL
        self.max_open_positions = config.MAX_OPEN_POSITIONS
        if self.logger:
            self.logger.info("Order Manager initialized")
    def enter_position(self, signal, price_data):
        if signal not in ["LONG", "SHORT"]:
            if self.logger:
                self.logger.warning(f"Invalid signal for position entry: {signal}")
            return False
        if price_data is None or price_data.empty:
            if self.logger:
                self.logger.error("Cannot enter position: Price data is empty or None")
            return False
        try:
            positions = self.bybit_client.get_positions(self.symbol)
            if positions:
                for position in positions:
                    size = float(position.get("size", 0))
                    if size > 0:
                        if self.logger:
                            self.logger.warning(f"Already have an open position for {self.symbol}, skipping entry")
                        return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking positions: {e}")
                import traceback
                self.logger.error(f"Detailed error: {traceback.format_exc()}")
            return False
        try:
            balance_info = self.bybit_client.get_wallet_balance()
            if not balance_info:
                if self.logger:
                    self.logger.error("Failed to get wallet balance")
                return False
            available_balance = balance_info["available_balance"]
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting wallet balance: {e}")
                import traceback
                self.logger.error(f"Detailed error: {traceback.format_exc()}")
            return False
        try:
            ticker = self.bybit_client.get_ticker(self.symbol)
            if not ticker:
                if self.logger:
                    self.logger.error("Failed to get ticker")
                return False
            entry_price = float(ticker["lastPrice"])
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting ticker: {e}")
                import traceback
                self.logger.error(f"Detailed error: {traceback.format_exc()}")
            return False
        try:
            atr_value = price_data.iloc[-1]["atr"] if "atr" in price_data.columns else None
            if not atr_value:
                if self.logger:
                    self.logger.error("Failed to get ATR value")
                return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting ATR value: {e}")
                import traceback
                self.logger.error(f"Detailed error: {traceback.format_exc()}")
            return False
        side = "Buy" if signal == "LONG" else "Sell"
        try:
            stop_loss = self.risk_manager.calculate_stop_loss(entry_price, side, atr_value)
            if not stop_loss:
                if self.logger:
                    self.logger.error("Failed to calculate stop loss")
                return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error calculating stop loss: {e}")
                import traceback
                self.logger.error(f"Detailed error: {traceback.format_exc()}")
            return False
        try:
            take_profit = self.risk_manager.calculate_take_profit(entry_price, stop_loss, side)
            if not take_profit:
                if self.logger:
                    self.logger.error("Failed to calculate take profit")
                return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error calculating take profit: {e}")
                import traceback
                self.logger.error(f"Detailed error: {traceback.format_exc()}")
            return False
        try:
            position_size = self.risk_manager.calculate_position_size(available_balance, entry_price, stop_loss)
            if not position_size:
                if self.logger:
                    self.logger.error("Failed to calculate position size")
                return False
            position_size = self.risk_manager.validate_position_size(position_size)
            if not position_size:
                if self.logger:
                    self.logger.error("Position size is too small")
                return False
            position_size = self.risk_manager.adjust_quantity_precision(position_size, self.symbol)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error calculating position size: {e}")
                import traceback
                self.logger.error(f"Detailed error: {traceback.format_exc()}")
            return False
        try:
            leverage_set = self.bybit_client.set_leverage(self.symbol, config.LEVERAGE)
            if not leverage_set:
                if self.logger:
                    self.logger.warning("Failed to set leverage, continuing anyway")
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error setting leverage: {e}, continuing anyway")
        try:
            if self.logger:
                self.logger.info(f"Размещение ордера на Bybit")
                self.logger.info(f"Символ: {self.symbol}, Сторона: {side}, Количество: {position_size}")
                self.logger.info(f"Цена входа: {entry_price}, Stop Loss: {stop_loss}, Take Profit: {take_profit}")
            order_result = self.bybit_client.place_market_order(
                symbol=self.symbol,
                side=side,
                qty=position_size,
                take_profit=take_profit,
                stop_loss=stop_loss
            )
            if not order_result:
                if self.logger:
                    self.logger.error("Failed to place market order")
                return False
            if self.logger:
                self.logger.info(f"Ордер успешно размещен на Bybit")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error placing market order: {e}")
                import traceback
                self.logger.error(f"Detailed error: {traceback.format_exc()}")
            return False
        if self.logger:
            self.logger.trade(
                action="ENTRY",
                symbol=self.symbol,
                side=side,
                quantity=position_size,
                price=entry_price,
                sl=stop_loss,
                tp=take_profit
            )
        if self.notifier:
            self.notifier.notify_trade_entry(
                symbol=self.symbol,
                side=side,
                quantity=position_size,
                price=entry_price,
                sl=stop_loss,
                tp=take_profit
            )
        return True
    def exit_position(self, reason="SIGNAL"):
        try:
            positions = self.bybit_client.get_positions(self.symbol)
            if not positions:
                if self.logger:
                    self.logger.info(f"No position to exit for {self.symbol}")
                return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting positions: {e}")
                import traceback
                self.logger.error(f"Detailed error: {traceback.format_exc()}")
            return False
        has_position = False
        for position in positions:
            try:
                size = float(position.get("size", 0))
                if size == 0:
                    continue
                has_position = True
                side = position.get("side")
                entry_price = float(position.get("entryPrice", 0))
                unrealized_pnl = float(position.get("unrealisedPnl", 0))
                try:
                    ticker = self.bybit_client.get_ticker(self.symbol)
                    exit_price = float(ticker["lastPrice"]) if ticker else 0
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error getting ticker for exit price: {e}")
                        import traceback
                        self.logger.error(f"Detailed error: {traceback.format_exc()}")
                    exit_price = 0
                try:
                    if self.logger:
                        self.logger.info(f"Закрытие позиции на Bybit")
                        self.logger.info(f"Символ: {self.symbol}, Сторона: {side}, Количество: {size}")
                        self.logger.info(f"Цена входа: {entry_price}, Цена выхода: {exit_price}, P&L: {unrealized_pnl}")
                    close_result = self.bybit_client.close_position(self.symbol)
                    if not close_result:
                        if self.logger:
                            self.logger.error(f"Failed to close {side} position for {self.symbol}")
                        return False
                    if self.logger:
                        self.logger.info(f"Позиция успешно закрыта на Bybit")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error closing position: {e}")
                        import traceback
                        self.logger.error(f"Detailed error: {traceback.format_exc()}")
                    return False
                if self.logger:
                    self.logger.trade(
                        action="EXIT",
                        symbol=self.symbol,
                        side=side,
                        quantity=size,
                        price=exit_price
                    )
                if self.notifier:
                    try:
                        self.notifier.notify_trade_exit(
                            symbol=self.symbol,
                            side=side,
                            quantity=size,
                            entry_price=entry_price,
                            exit_price=exit_price,
                            pnl=unrealized_pnl,
                            exit_reason=reason
                        )
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Error sending notification: {e}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error processing position: {e}")
                    import traceback
                    self.logger.error(f"Detailed error: {traceback.format_exc()}")
                return False
        if not has_position:
            if self.logger:
                self.logger.info(f"No position to exit for {self.symbol}")
        return True
    def check_and_exit_on_signal(self, price_data):
        if price_data is None or price_data.empty:
            if self.logger:
                self.logger.warning("Cannot check exit signal: Price data is empty or None")
            return False
        try:
            positions = self.bybit_client.get_positions(self.symbol)
            if not positions:
                return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting positions: {e}")
                import traceback
                self.logger.error(f"Detailed error: {traceback.format_exc()}")
            return False
        for position in positions:
            try:
                size = float(position.get("size", 0))
                if size == 0:
                    continue
                side = position.get("side")
                try:
                    from strategy import Strategy
                    strategy = Strategy(self.logger)
                    should_exit = strategy.should_exit_position(price_data, side)
                    if should_exit:
                        if self.logger:
                            self.logger.info(f"Exiting {side} position for {self.symbol} based on opposite signal")
                        return self.exit_position(reason="OPPOSITE_SIGNAL")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error checking exit signal: {e}")
                        import traceback
                        self.logger.error(f"Detailed error: {traceback.format_exc()}")
                    return False
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error processing position for exit check: {e}")
                    import traceback
                    self.logger.error(f"Detailed error: {traceback.format_exc()}")
                return False
        return False
