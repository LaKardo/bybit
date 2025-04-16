<div align="center">

# 🤖 Bybit Trading Bot 📈

<img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python Version">
<img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
<img src="https://img.shields.io/badge/bybit-v5%20API-orange.svg" alt="Bybit API">
<img src="https://img.shields.io/badge/status-beta-yellow.svg" alt="Status">

*A professional Python-based trading bot for Bybit futures trading with a focus on long-term stable trading and minimizing drawdowns.*

</div>

## ✨ Features

<table>
  <tr>
    <td>
      <h3>🏗️ Architecture</h3>
      <ul>
        <li>Modular, well-structured code</li>
        <li>Separate components for different functionalities</li>
        <li>Easy to extend and customize</li>
      </ul>
    </td>
    <td>
      <h3>📊 Technical Analysis</h3>
      <ul>
        <li>EMA crossover strategy</li>
        <li>RSI for overbought/oversold conditions</li>
        <li>MACD for trend confirmation</li>
        <li>Volume analysis for trend strength confirmation</li>
        <li>On-Balance Volume (OBV) for volume trend direction</li>
        <li>ATR for volatility-based stops</li>
        <li>Candlestick pattern recognition</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td>
      <h3>🛡️ Risk Management</h3>
      <ul>
        <li>Fixed risk per trade (1.5%)</li>
        <li>Dynamic position sizing</li>
        <li>ATR-based stop losses</li>
        <li>Risk:Reward ratio of 1:2</li>
      </ul>
    </td>
    <td>
      <h3>🔔 Notifications & Logging</h3>
      <ul>
        <li>Real-time Telegram notifications</li>
        <li>Comprehensive logging system</li>
        <li>Detailed trade information</li>
        <li>Error and warning alerts</li>
      </ul>
    </td>
  </tr>
</table>

## 🔧 Requirements

- Python 3.8+
- Bybit API key and secret
- Telegram bot token and chat ID (optional, for notifications)

## 🚀 Installation

<details>
<summary>Click to expand installation steps</summary>

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd bybit-trading-bot
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the bot by editing `config.py`:
   - Add your Bybit API credentials
   - Set trading parameters
   - Configure risk management settings
   - Add Telegram bot token and chat ID (optional)
</details>

## ⚙️ Configuration

<details>
<summary>Click to view configuration options</summary>

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

# Volume Filter Parameters
VOLUME_MA_PERIOD = 20  # Period for volume moving average
VOLUME_THRESHOLD = 1.5  # Volume must be this multiple of its MA to confirm trend
OBV_SMOOTHING = 5  # Smoothing period for On-Balance Volume
VOLUME_REQUIRED = True  # Whether to require volume confirmation for signals

# Pattern Recognition Parameters
PATTERN_RECOGNITION_ENABLED = True  # Whether to use candlestick pattern recognition
PATTERN_STRENGTH_THRESHOLD = 2  # Minimum pattern strength to generate a signal
PATTERN_CONFIRMATION_REQUIRED = True  # Whether to require pattern confirmation for signals
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
</details>

## 👉 Usage

<div align="center">

```bash
python main.py
```

</div>

### What the Bot Does:

1. **Initialization**: Loads configuration and initializes all components
2. **Data Collection**: Fetches historical price data from Bybit
3. **Analysis**: Calculates technical indicators (EMA, RSI, MACD, ATR)
4. **Signal Generation**: Identifies trading opportunities based on indicator conditions
5. **Risk Calculation**: Determines position size, stop-loss, and take-profit levels
6. **Order Execution**: Places market orders with appropriate risk parameters
7. **Monitoring**: Continuously monitors positions and market conditions
8. **Reporting**: Logs all activities and sends notifications via Telegram

## 💸 Trading Strategy

### Long (Buy) Signal 🔼
1. Fast EMA(20) crosses **above** Slow EMA(50)
2. RSI(14) is **below** 70 (not overbought)
3. MACD histogram is **positive** OR MACD line crosses **above** signal line
4. **Volume confirmation**: Current volume > 1.5x its 20-period MA AND OBV is trending up
5. **Pattern confirmation**: Bullish candlestick pattern(s) with strength >= threshold
6. No active short position

### Short (Sell) Signal 🔽
1. Fast EMA(20) crosses **below** Slow EMA(50)
2. RSI(14) is **above** 30 (not oversold)
3. MACD histogram is **negative** OR MACD line crosses **below** signal line
4. **Volume confirmation**: Current volume > 1.5x its 20-period MA AND OBV is trending down
5. **Pattern confirmation**: Bearish candlestick pattern(s) with strength >= threshold
6. No active long position

### Candlestick Patterns

#### Bullish Patterns
- **Hammer**: Small body at the top with a long lower shadow
- **Bullish Engulfing**: A bullish candle that completely engulfs the previous bearish candle
- **Bullish Harami**: A small bullish candle contained within the body of the previous larger bearish candle
- **Tweezer Bottom**: Two candles with the same low, first bearish, second bullish
- **Morning Star**: Three-candle pattern with a large bearish candle, a small-bodied candle, and a large bullish candle
- **Three White Soldiers**: Three consecutive bullish candles, each closing higher than the previous
- **Bullish Marubozu**: A bullish candle with no or very small shadows

#### Bearish Patterns
- **Shooting Star**: Small body at the bottom with a long upper shadow
- **Inverted Hammer**: Small body at the bottom with a long upper shadow (appears in a downtrend)
- **Bearish Engulfing**: A bearish candle that completely engulfs the previous bullish candle
- **Bearish Harami**: A small bearish candle contained within the body of the previous larger bullish candle
- **Tweezer Top**: Two candles with the same high, first bullish, second bearish
- **Evening Star**: Three-candle pattern with a large bullish candle, a small-bodied candle, and a large bearish candle
- **Three Black Crows**: Three consecutive bearish candles, each closing lower than the previous
- **Bearish Marubozu**: A bearish candle with no or very small shadows

### Exit Signal 🚪
1. Stop-Loss or Take-Profit is hit
2. Opposite signal appears

## 💰 Risk Management

- **Risk per trade**: 1.5% of available balance
- **Stop-Loss**: Based on ATR (Average True Range)
- **Take-Profit**: Based on Risk-Reward Ratio (1:2)
- **Position sizing**: Calculated to risk exactly the specified percentage
- **Leverage**: Used only for margin calculation, not to increase risk

## 📝 Logging & Notifications

<table>
  <tr>
    <td width="50%">
      <h3>📓 Logging</h3>
      <p>The bot logs all activities to both console and file:</p>
      <ul>
        <li>Trading signals with indicator values</li>
        <li>Order placement and execution details</li>
        <li>Balance and position updates</li>
        <li>Errors and warnings with timestamps</li>
      </ul>
    </td>
    <td width="50%">
      <h3>📲 Telegram Notifications</h3>
      <p>If configured, the bot sends notifications via Telegram:</p>
      <ul>
        <li>New trade entries with entry price, SL, and TP</li>
        <li>Trade exits with P&L and reason</li>
        <li>Critical errors with timestamps</li>
        <li>Bot status updates (start/stop)</li>
      </ul>
    </td>
  </tr>
</table>

## 📍 Project Structure

```
├── main.py                # Main entry point and trading loop
├── config.py              # Configuration parameters
├── bybit_client.py        # API client for Bybit
├── strategy.py            # Trading strategy implementation
├── pattern_recognition.py # Candlestick pattern recognition
├── risk_manager.py        # Risk management and position sizing
├── order_manager.py       # Order placement and management
├── logger.py              # Logging functionality
├── notifier.py            # Telegram notification system
├── utils.py               # Utility functions
├── requirements.txt       # Required packages
└── README.md              # Documentation
```

## 🔥 Future Improvements

<details>
<summary>Click to view potential enhancements</summary>

### Advanced Strategy Enhancements
- **Multi-Timeframe Analysis**: Implement signal confirmation across multiple timeframes
- **Advanced Pattern Recognition**: Implement more complex chart patterns (Head & Shoulders, Double Top/Bottom, etc.)
- **Machine Learning Integration**: Add predictive models for enhanced signal generation

### Risk Management Improvements
- **Dynamic Risk Adjustment**: Adjust risk based on market volatility
- **Trailing Stop-Loss**: Implement trailing stops to lock in profits
- **Partial Take-Profits**: Allow multiple take-profit levels
- **Drawdown Protection**: Reduce position sizes after consecutive losses

### System Enhancements
- **WebSocket Implementation**: Use WebSockets for real-time data and reduced latency
- **Web Dashboard**: Create a web interface for monitoring and control
- **Performance Analytics**: Add detailed performance metrics and reporting
- **Multi-Exchange Support**: Extend to support multiple exchanges
- **Multi-Asset Trading**: Support trading multiple assets simultaneously

### Backtesting Module
- **Historical Data Analysis**: Test strategy on historical data
- **Performance Metrics**: Calculate Sharpe ratio, drawdown, win rate, etc.
- **Parameter Optimization**: Find optimal parameters for the strategy
- **Monte Carlo Simulation**: Assess strategy robustness
</details>

## ⚠️ Disclaimer

<div align="center">

*This bot is provided for educational and informational purposes only. Use it at your own risk. Cryptocurrency trading involves substantial risk and is not suitable for everyone. The developers are not responsible for any financial losses incurred from using this bot.*

</div>

## 📄 License

<div align="center">

This project is licensed under the MIT License - see the LICENSE file for details.

<img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">

</div>
