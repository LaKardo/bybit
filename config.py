"""
Configuration file for the Bybit Trading Bot.
Contains all configurable parameters for the bot.
"""

# API Configuration
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"
TESTNET = True  # Set to False for live trading

# Trading Parameters
SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"  # 1h, 4h, 1d, etc.
LEVERAGE = 5  # Leverage to use (1-100)

# Strategy Parameters
FAST_EMA = 20
SLOW_EMA = 50
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
ATR_PERIOD = 14

# Volume Filter Parameters
VOLUME_MA_PERIOD = 20  # Period for volume moving average
VOLUME_THRESHOLD = 1.5  # Volume must be this multiple of its MA to confirm trend
OBV_SMOOTHING = 5  # Smoothing period for On-Balance Volume
VOLUME_REQUIRED = True  # Whether to require volume confirmation for signals

# Pattern Recognition Parameters
PATTERN_RECOGNITION_ENABLED = True  # Whether to use candlestick pattern recognition
PATTERN_STRENGTH_THRESHOLD = 2  # Minimum pattern strength to generate a signal
PATTERN_CONFIRMATION_REQUIRED = True  # Whether to require pattern confirmation for signals

# Complex Pattern Parameters
COMPLEX_PATTERNS_ENABLED = True  # Whether to use complex chart patterns (H&S, Double Top/Bottom)
COMPLEX_PATTERN_MIN_CANDLES = 14  # Minimum number of candles to analyze for complex patterns
HS_PATTERN_SHOULDER_DIFF_THRESHOLD = 0.1  # Maximum allowed difference between shoulders (10%)
DOUBLE_PATTERN_LEVEL_THRESHOLD = 0.03  # Maximum allowed difference between tops/bottoms (3%)

# Multi-Timeframe Analysis Parameters
MULTI_TIMEFRAME_ENABLED = True  # Whether to use multi-timeframe analysis
CONFIRMATION_TIMEFRAMES = ["15m", "4h", "1d"]  # Timeframes to use for confirmation (in addition to main timeframe)
MTF_ALIGNMENT_REQUIRED = 2  # Minimum number of timeframes that must align with the signal (including main timeframe)
MTF_WEIGHT_MAIN = 1.0  # Weight of the main timeframe
MTF_WEIGHT_LOWER = 0.7  # Weight of lower timeframes (faster)
MTF_WEIGHT_HIGHER = 1.2  # Weight of higher timeframes (slower)
MTF_VOLATILITY_ADJUSTMENT = True  # Whether to adjust timeframe weights based on market volatility

# Risk Management
RISK_PER_TRADE = 0.015  # 1.5% of balance per trade
RISK_REWARD_RATIO = 2  # Risk:Reward ratio (1:2)
SL_ATR_MULTIPLIER = 2  # Stop Loss = Entry Price +/- (ATR * SL_ATR_MULTIPLIER)

# Telegram Notifications
TELEGRAM_BOT_TOKEN = "your_telegram_bot_token_here"
TELEGRAM_CHAT_ID = "your_telegram_chat_id_here"

# Bot Settings
DRY_RUN = True  # Set to False for live trading
CHECK_INTERVAL = 60  # Seconds between checks (for non-websocket mode)
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = "trading_bot.log"

# Advanced Settings
MAX_OPEN_POSITIONS = 1  # Maximum number of open positions
MAX_RETRIES = 3  # Maximum number of retries for API calls
RETRY_DELAY = 5  # Seconds between retries
CLOSE_POSITIONS_ON_SHUTDOWN = True  # Close all positions when bot is shut down
