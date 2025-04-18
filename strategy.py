"""
Strategy module for the Bybit Trading Bot.
Implements the trading strategy using technical indicators.
"""

import pandas_ta as ta
import config
from bybit_client import BybitAPIClient

class Strategy:
    """
    Strategy class for the Bybit Trading Bot.
    Implements the trading strategy using technical indicators.
    """
    def __init__(self, logger=None, bybit_client=None):
        """
        Initialize the strategy.

        Args:
            logger (Logger, optional): Logger instance.
            bybit_client (BybitAPIClient, optional): Bybit API client instance.
        """
        self.logger = logger

        # Initialize or use provided Bybit client
        self.bybit_client = bybit_client if bybit_client is not None else BybitAPIClient(logger=logger)

        # Strategy parameters
        self.fast_ema = config.FAST_EMA
        self.slow_ema = config.SLOW_EMA
        self.rsi_period = config.RSI_PERIOD
        self.rsi_overbought = config.RSI_OVERBOUGHT
        self.rsi_oversold = config.RSI_OVERSOLD
        self.macd_fast = config.MACD_FAST
        self.macd_slow = config.MACD_SLOW
        self.macd_signal = config.MACD_SIGNAL
        self.atr_period = config.ATR_PERIOD



        # Multi-timeframe analysis has been removed



        if self.logger:
            self.logger.info("Strategy initialized")

    def calculate_indicators(self, df):
        """
        Calculate technical indicators.

        Args:
            df (pandas.DataFrame): Price data with OHLCV columns.

        Returns:
            pandas.DataFrame: DataFrame with indicators.
        """
        if df is None or df.empty:
            if self.logger:
                self.logger.error("Cannot calculate indicators: No data provided")
            return None

        # Make a copy to avoid modifying the original
        df = df.copy()

        try:
            # Calculate EMAs
            df[f'ema_{self.fast_ema}'] = ta.ema(df['close'], length=self.fast_ema)
            df[f'ema_{self.slow_ema}'] = ta.ema(df['close'], length=self.slow_ema)

            # Calculate RSI
            df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)

            # Calculate MACD using optimized implementation from BybitAPIClient
            try:
                # Use the optimized MACD calculation from BybitAPIClient
                df = self.bybit_client.calculate_macd(df)

                if self.logger:
                    self.logger.debug("MACD calculated successfully using optimized implementation")

            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to calculate MACD: {e}, using default values")
                # Use default values
                df['macd'] = 0.0
                df['macd_signal'] = 0.0
                df['macd_hist'] = 0.0

            # Calculate ATR
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_period)


            # Drop NaN values
            df = df.dropna()



            if self.logger:
                self.logger.debug("Indicators calculated successfully")

            return df

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to calculate indicators: {e}")
                # Log more detailed error information
                import traceback
                self.logger.error(f"Detailed error: {traceback.format_exc()}")
                # Log the DataFrame info
                if df is not None and not df.empty:
                    self.logger.error(f"DataFrame columns: {df.columns.tolist()}")
                    self.logger.error(f"DataFrame head: {df.head(1).to_dict()}")
            return None

    def generate_signal(self, df):
        """
        Generate trading signal based on indicators.

        Args:
            df (pandas.DataFrame): Price data with indicators for the main timeframe.

        Returns:
            str: Signal (LONG, SHORT, NONE).
        """
        if df is None or df.empty or len(df) < 2:
            if self.logger:
                self.logger.error("Cannot generate signal: Insufficient data")
            return "NONE"

        try:
            # Use single timeframe analysis
            return self._generate_signal_from_single_timeframe(df)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to generate signal: {e}")
            return "NONE"



    # Multi-timeframe analysis has been removed

    def _generate_signal_from_single_timeframe(self, df):
        """
        Generate trading signal based on indicators.

        Args:
            df (pandas.DataFrame): Price data with indicators.

        Returns:
            str: Signal (LONG, SHORT, NONE).
        """
        if df is None or df.empty or len(df) < 2:
            if self.logger:
                self.logger.warning("Cannot generate signal from single timeframe: Insufficient data")
            return "NONE"

        # Check if required indicators are present
        required_indicators = ['ema_20', 'ema_50', 'rsi', 'macd', 'macd_signal', 'macd_hist']
        missing_indicators = [ind for ind in required_indicators if ind not in df.columns]

        if missing_indicators:
            if self.logger:
                self.logger.warning(f"Cannot generate signal from single timeframe: Missing indicators {missing_indicators}")
            return "NONE"

        try:
            # Get the last two rows for crossover detection
            current = df.iloc[-1]
            previous = df.iloc[-2]

            # Check for EMA crossover
            fast_ema_current = current[f'ema_{self.fast_ema}']
            fast_ema_previous = previous[f'ema_{self.fast_ema}']
            slow_ema_current = current[f'ema_{self.slow_ema}']
            slow_ema_previous = previous[f'ema_{self.slow_ema}']

            # Check for MACD conditions
            try:
                macd_current = float(current['macd'])
                macd_signal_current = float(current['macd_signal'])
                macd_hist_current = float(current['macd_hist'])
                macd_previous = float(previous['macd'])
                macd_signal_previous = float(previous['macd_signal'])

                # Check for MACD crossover
                macd_crossover_up = macd_previous < macd_signal_previous and macd_current > macd_signal_current
                macd_crossover_down = macd_previous > macd_signal_previous and macd_current < macd_signal_current
            except (TypeError, ValueError, KeyError) as e:
                if self.logger:
                    self.logger.debug(f"MACD calculation error in _generate_signal_from_single_timeframe: {e}, using default values")
                macd_current = 0.0
                macd_signal_current = 0.0
                macd_hist_current = 0.0
                macd_crossover_up = False
                macd_crossover_down = False

            # Check for RSI conditions
            rsi_current = current['rsi']


            # Long signal conditions
            ema_crossover_up = fast_ema_previous < slow_ema_previous and fast_ema_current > slow_ema_current
            rsi_not_overbought = rsi_current < self.rsi_overbought
            macd_positive = macd_hist_current > 0 or macd_crossover_up

            # Short signal conditions
            ema_crossover_down = fast_ema_previous > slow_ema_previous and fast_ema_current < slow_ema_current
            rsi_not_oversold = rsi_current > self.rsi_oversold
            macd_negative = macd_hist_current < 0 or macd_crossover_down

            # Pattern recognition has been removed

            # Generate signal based on indicators
            if ema_crossover_up and rsi_not_overbought and macd_positive:
                return "LONG"
            elif ema_crossover_down and rsi_not_oversold and macd_negative:
                return "SHORT"
            else:
                return "NONE"

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to generate signal from single timeframe: {e}")
            return "NONE"

    # Multi-timeframe helper methods have been removed

    def should_exit_position(self, df, position_side):
        """
        Check if position should be exited based on opposite signal.

        Args:
            df (pandas.DataFrame): Price data with indicators.
            position_side (str): Current position side (Buy or Sell).

        Returns:
            bool: True if position should be exited, False otherwise.
        """
        if df is None or df.empty or len(df) < 2:
            return False

        try:
            # Generate signal
            signal = self.generate_signal(df)

            # Exit long position on SHORT signal
            if position_side == "Buy" and signal == "SHORT":
                if self.logger:
                    self.logger.info("Exit signal for LONG position: Opposite signal detected")
                return True

            # Exit short position on LONG signal
            if position_side == "Sell" and signal == "LONG":
                if self.logger:
                    self.logger.info("Exit signal for SHORT position: Opposite signal detected")
                return True

            return False

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to check exit signal: {e}")
            return False

    def get_atr_value(self, df):
        """
        Get the current ATR value.

        Args:
            df (pandas.DataFrame): Price data with indicators.

        Returns:
            float: ATR value or None on error.
        """
        if df is None or df.empty:
            return None

        try:
            return df.iloc[-1]['atr']
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get ATR value: {e}")
            return None
