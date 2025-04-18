"""
Configuration file for the Bybit Trading Bot.
Contains all configurable parameters for the bot.

API keys are loaded from .env file if it exists, otherwise default values are used.
Create a .env file based on .env.example to use your own API keys.
"""

import os
import dotenv
from pathlib import Path

# Load environment variables from .env file if it exists
env_path = Path('.') / '.env'
if env_path.exists():
    dotenv.load_dotenv(dotenv_path=env_path)

# API Configuration
# Keys are loaded from .env file if available, otherwise example keys are used

# API keys (real trading)
API_KEY = os.getenv("BYBIT_API_KEY", "your_api_key_here")
API_SECRET = os.getenv("BYBIT_API_SECRET", "your_api_secret_here")

# Always use mainnet
TESTNET = False

# Trading Parameters
SYMBOL = "BTCUSDT"
TIMEFRAME = "15"  # Bybit API V5 format: 1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M
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


# Multi-Timeframe Analysis has been removed

# Risk Management
RISK_PER_TRADE = 0.015  # 1.5% of balance per trade
RISK_REWARD_RATIO = 2  # Risk:Reward ratio (1:2)
SL_ATR_MULTIPLIER = 2  # Stop Loss = Entry Price +/- (ATR * SL_ATR_MULTIPLIER)

# Telegram Notifications
TELEGRAM_BOT_TOKEN = "your_telegram_bot_token_here"
TELEGRAM_CHAT_ID = "your_telegram_chat_id_here"

# Bot Settings
# DRY_RUN=True означает, что бот не будет выполнять реальные сделки (только симуляция)
# DRY_RUN=False означает, что бот будет выполнять реальные сделки

DRY_RUN = True  # Set to False for live trading
CHECK_INTERVAL = 60  # Seconds between checks (for non-websocket mode)
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = "trading_bot.log"

# WebSocket Settings
USE_WEBSOCKET = True  # Use WebSocket for real-time data (potential fix applied in bybit_client.py)
WS_RECONNECT_INTERVAL = 60  # Seconds between WebSocket reconnection attempts

# Advanced Settings
MAX_OPEN_POSITIONS = 1  # Maximum number of open positions
MAX_RETRIES = 3  # Maximum number of retries for API calls
RETRY_DELAY = 5  # Seconds between retries
CLOSE_POSITIONS_ON_SHUTDOWN = True  # Close all positions when bot is shut down

# Web Interface Settings
WEB_INTERFACE_ENABLED = True  # Enable web interface
WEB_HOST = "0.0.0.0"  # Web interface host (0.0.0.0 to allow external connections)
WEB_PORT = 5000  # Web interface port
WEB_DEBUG = False  # Enable debug mode for web interface
WEB_USERNAME = os.getenv("WEB_USERNAME", "admin")  # Web interface username (Set in .env)
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "admin")  # Web interface password (Set in .env - CHANGE THIS!)
WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", "a9d8e7f6c5b4a3c2d1e0f9g8h7i6j5k4l3m2n1o0p")  # Secret key for session management (Set in .env)
