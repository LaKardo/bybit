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
