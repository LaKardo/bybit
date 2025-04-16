import os
import dotenv
from pathlib import Path
env_path = Path('.') / '.env'
if env_path.exists():
    dotenv.load_dotenv(dotenv_path=env_path)
API_KEY = os.getenv("BYBIT_API_KEY", "your_api_key_here")
API_SECRET = os.getenv("BYBIT_API_SECRET", "your_api_secret_here")
SYMBOL = "BTCUSDT"
TIMEFRAME = "15"
LEVERAGE = 5
FAST_EMA = 20
SLOW_EMA = 50
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
ATR_PERIOD = 14
RISK_PER_TRADE = 0.015
RISK_REWARD_RATIO = 2
SL_ATR_MULTIPLIER = 2
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_telegram_bot_token_here")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "your_telegram_chat_id_here")
DRY_RUN = True
CHECK_INTERVAL = 60
LOG_LEVEL = "INFO"
LOG_FILE = "trading_bot.log"
USE_WEBSOCKET = True
WS_RECONNECT_INTERVAL = 60
MAX_OPEN_POSITIONS = 1
MAX_RETRIES = 3
RETRY_DELAY = 5
CLOSE_POSITIONS_ON_SHUTDOWN = True
LOG_ROTATION = True
MAX_LOG_SIZE_MB = 10
LOG_BACKUP_COUNT = 5
LOG_JSON_FORMAT = False
PERFORMANCE_TRACKING = True
RATE_LIMITING_ENABLED = True
RATE_LIMITS = {
    "default": (100, 10),
    "order": (50, 10),
    "position": (50, 10),
    "market": (120, 10),
    "account": (60, 10)
}
CIRCUIT_BREAKER_ENABLED = True
ERROR_THRESHOLD = 5
ERROR_TIMEOUT = 60
CIRCUIT_TIMEOUT = 300
WEB_INTERFACE_ENABLED = True
WEB_HOST = "0.0.0.0"
WEB_PORT = 5000
WEB_DEBUG = False
DEBUG = WEB_DEBUG  # Add this line for compatibility with run_web_app.py
WEB_USERNAME = os.getenv("WEB_USERNAME", "admin")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "admin")
WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", "a9d8e7f6c5b4a3c2d1e0f9g8h7i6j5k4l3m2n1o0p")
