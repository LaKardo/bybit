# Bybit Trading Bot

A Python-based trading bot for Bybit futures trading with a focus on long-term stable trading and minimizing drawdowns.

## Features

- **Modular Architecture**: Well-structured code with separate modules for different functionalities
- **Technical Analysis**: Uses EMA, RSI, MACD, and ATR indicators for signal generation
- **Risk Management**: Calculates position size, stop-loss, and take-profit based on risk parameters
- **Telegram Notifications**: Sends real-time notifications about trades and errors
- **Detailed Logging**: Comprehensive logging of all bot activities
- **Dry Run Mode**: Test the bot without placing real orders

## Requirements

- Python 3.8+
- Bybit API key and secret
- Telegram bot token and chat ID (optional, for notifications)

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd bybit-trading-bot
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Configure the bot by editing `config.py`:
   - Add your Bybit API credentials
   - Set trading parameters
   - Configure risk management settings
   - Add Telegram bot token and chat ID (optional)

## Configuration

Edit the `config.py` file to customize the bot's behavior:

### API Configuration
```python
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"
TESTNET = True  # Set to False for live trading
```

### Trading Parameters
```python
SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"  # 1h, 4h, 1d, etc.
LEVERAGE = 5  # Leverage to use (1-100)
```

### Strategy Parameters
```python
FAST_EMA = 20
SLOW_EMA = 50
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
ATR_PERIOD = 14
```

### Risk Management
```python
RISK_PER_TRADE = 0.015  # 1.5% of balance per trade
RISK_REWARD_RATIO = 2  # Risk:Reward ratio (1:2)
SL_ATR_MULTIPLIER = 2  # Stop Loss = Entry Price +/- (ATR * SL_ATR_MULTIPLIER)
```

### Bot Settings
```python
DRY_RUN = True  # Set to False for live trading
CHECK_INTERVAL = 60  # Seconds between checks
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
CLOSE_POSITIONS_ON_SHUTDOWN = True  # Close all positions when bot is shut down
```

## Usage

1. Configure the bot by editing `config.py`
2. Run the bot:
   ```
   python main.py
   ```

3. The bot will:
   - Initialize all components
   - Connect to Bybit API
   - Start the main trading loop
   - Generate signals based on the configured strategy
   - Place orders according to the risk management rules
   - Log all activities and send notifications

## Trading Strategy

The bot uses a combination of technical indicators to generate trading signals:

### Long (Buy) Signal
1. Fast EMA(20) crosses above Slow EMA(50)
2. RSI(14) is below 70 (not overbought)
3. MACD histogram is positive OR MACD line crosses above signal line
4. No active short position

### Short (Sell) Signal
1. Fast EMA(20) crosses below Slow EMA(50)
2. RSI(14) is above 30 (not oversold)
3. MACD histogram is negative OR MACD line crosses below signal line
4. No active long position

### Exit Signal
1. Stop-Loss or Take-Profit is hit
2. Opposite signal appears

## Risk Management

The bot implements robust risk management:

- Risk per trade: 1.5% of available balance
- Stop-Loss: Based on ATR (Average True Range)
- Take-Profit: Based on Risk-Reward Ratio (1:2)
- Position sizing: Calculated to risk exactly the specified percentage

## Logging

The bot logs all activities to both console and file:

- Trading signals
- Order placement and execution
- Balance and position updates
- Errors and warnings

## Telegram Notifications

If configured, the bot sends notifications via Telegram:

- New trade entries
- Trade exits with P&L
- Critical errors
- Bot status updates

## Disclaimer

This bot is provided for educational and informational purposes only. Use it at your own risk. Cryptocurrency trading involves substantial risk and is not suitable for everyone. The developers are not responsible for any financial losses incurred from using this bot.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
