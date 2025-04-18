<div align="center">

# 🤖 Bybit Trading Bot 📈

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge&logo=license&logoColor=white)](LICENSE)
[![Bybit API](https://img.shields.io/badge/bybit-v5%20API-orange.svg?style=for-the-badge&logo=bitcoin&logoColor=white)](https://bybit-exchange.github.io/docs/v5/intro)
[![Status](https://img.shields.io/badge/status-beta-yellow.svg?style=for-the-badge&logo=statuspage&logoColor=white)]()

*A professional Python-based trading bot for Bybit futures trading with a focus on long-term stable trading and minimizing drawdowns.*

[Features](#-features) • [Requirements](#-requirements) • [Installation](#-installation) • [Usage](#-usage) • [Strategy](#-trading-strategy) • [Risk Management](#-risk-management) • [Monitoring & Control](#-monitoring--control) • [Project Structure](#-project-structure) • [Future Improvements](#-future-improvements) • [Disclaimer](#-disclaimer) • [License](#-license)

<hr>

</div>

## ✨ Features

<table>
  <tr>
    <td width="50%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>🏗️ Architecture</h3>
      <ul align="left">
        <li><b>Modular</b>, well-structured code</li>
        <li><b>Separate components</b> for different functionalities</li>
        <li><b>Easy to extend</b> and customize</li>
      </ul>
    </td>
    <td width="50%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>📊 Technical Analysis</h3>
      <ul align="left">
        <li><b>EMA crossover</b> strategy</li>
        <li><b>RSI</b> for overbought/oversold conditions</li>
        <li><b>MACD</b> for trend confirmation</li>
        <li><b>Volume analysis</b> for trend strength confirmation</li>
        <li><b>On-Balance Volume (OBV)</b> for volume trend direction</li>
        <li><b>ATR</b> for volatility-based stops</li>

        <li><b>Multi-timeframe analysis</b> for signal confirmation</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>🛡️ Risk Management</h3>
      <ul align="left">
        <li><b>Fixed risk</b> per trade (1.5%)</li>
        <li><b>Dynamic position</b> sizing</li>
        <li><b>ATR-based</b> stop losses</li>
        <li><b>Risk:Reward</b> ratio of 1:2</li>
      </ul>
    </td>
    <td width="50%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>🔔 Monitoring & Control</h3>
      <ul align="left">
        <li><b>Real-time Telegram</b> notifications</li>
        <li><b>Web Dashboard</b> for monitoring</li>
        <li><b>Comprehensive</b> logging system</li>
        <li><b>Detailed trade</b> information</li>
        <li><b>Error and warning</b> alerts</li>
      </ul>
    </td>
  </tr>
</table>

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 🔧 Requirements

- Python 3.8+
- Bybit API key and secret
- Telegram bot token and chat ID (optional, for notifications)

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

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

3. Create a `.env` file based on the provided `.env.example`:
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file to add your Bybit API credentials:
   ```
   BYBIT_API_KEY=your_actual_api_key_here
   BYBIT_API_SECRET=your_actual_api_secret_here
   ```

5. Configure other bot settings by editing `config.py`:
   - Set trading parameters
   - Configure risk management settings
   - Add Telegram bot token and chat ID (optional)
</details>

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## ⚙️ Configuration

<details>
<summary>Click to view configuration options</summary>

Edit the `config.py` file to customize the bot's behavior:

### API Configuration
API keys are now stored in the `.env` file for better security:

```
# In .env file
BYBIT_API_KEY=your_actual_api_key_here
BYBIT_API_SECRET=your_actual_api_secret_here
```

The `config.py` file will automatically load these values from the `.env` file.

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


# Multi-Timeframe Analysis Parameters
MULTI_TIMEFRAME_ENABLED = True  # Whether to use multi-timeframe analysis
CONFIRMATION_TIMEFRAMES = ["15m", "4h", "1d"]  # Timeframes to use for confirmation
MTF_ALIGNMENT_REQUIRED = 2  # Minimum number of timeframes that must align with the signal
MTF_WEIGHT_MAIN = 1.0  # Weight of the main timeframe
MTF_WEIGHT_LOWER = 0.7  # Weight of lower timeframes (faster)
MTF_WEIGHT_HIGHER = 1.2  # Weight of higher timeframes (slower)
MTF_VOLATILITY_ADJUSTMENT = True  # Whether to adjust timeframe weights based on market volatility
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

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 👉 Usage

<div align="center">

```bash
python main.py
```

</div>

This will start both the trading bot and the web interface (if enabled in config.py). You can access the web interface by opening a browser and navigating to:

```
http://localhost:5000
```

Or if you've configured a different host/port in config.py, use that instead.

### What the Bot Does:

1. **Initialization**: Loads configuration and initializes all components
2. **Data Collection**: Fetches historical price data from Bybit
3. **Analysis**: Calculates technical indicators (EMA, RSI, MACD, ATR)
4. **Signal Generation**: Identifies trading opportunities based on indicator conditions
5. **Risk Calculation**: Determines position size, stop-loss, and take-profit levels
6. **Order Execution**: Places market orders with appropriate risk parameters
7. **Monitoring**: Continuously monitors positions and market conditions
8. **Reporting**: Logs all activities and sends notifications via Telegram

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 💸 Trading Strategy

### Long (Buy) Signal 🔼
1. Fast EMA(20) crosses **above** Slow EMA(50)
2. RSI(14) is **below** 70 (not overbought)
3. MACD histogram is **positive** OR MACD line crosses **above** signal line
4. **Volume confirmation**: Current volume > 1.5x its 20-period MA AND OBV is trending up

5. **Multi-timeframe confirmation**: Signal is confirmed across multiple timeframes
6. No active short position

### Short (Sell) Signal 🔽
1. Fast EMA(20) crosses **below** Slow EMA(50)
2. RSI(14) is **above** 30 (not oversold)
3. MACD histogram is **negative** OR MACD line crosses **below** signal line
4. **Volume confirmation**: Current volume > 1.5x its 20-period MA AND OBV is trending down

5. **Multi-timeframe confirmation**: Signal is confirmed across multiple timeframes
6. No active long position

### Exit Signal 🚪
1. Stop-Loss or Take-Profit is hit
2. Opposite signal appears

### Multi-Timeframe Analysis
The bot uses multiple timeframes to confirm trading signals, reducing false signals and improving trade quality:

1. **Primary Timeframe**: Main trading timeframe (e.g., 1h)
2. **Confirmation Timeframes**: Additional timeframes (e.g., 15m, 4h, 1d)
3. **Weighted Scoring**: Higher timeframes have more weight in the decision
4. **Alignment Requirement**: Minimum number of timeframes that must align
5. **Volatility Adjustment**: During high volatility, higher timeframes get more weight



<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 💰 Risk Management

- **Risk per trade**: 1.5% of available balance
- **Stop-Loss**: Based on ATR (Average True Range)
- **Take-Profit**: Based on Risk-Reward Ratio (1:2)
- **Position sizing**: Calculated to risk exactly the specified percentage
- **Leverage**: Used only for margin calculation, not to increase risk

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 📝 Monitoring & Control

<table>
  <tr>
    <td width="33%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>📓 Logging</h3>
      <p>The bot logs all activities to both console and file:</p>
      <ul align="left">
        <li><b>Trading signals</b> with indicator values</li>
        <li><b>Order placement</b> and execution details</li>
        <li><b>Balance and position</b> updates</li>
        <li><b>Errors and warnings</b> with timestamps</li>
      </ul>
    </td>
    <td width="33%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>📲 Telegram Notifications</h3>
      <p>If configured, the bot sends notifications via Telegram:</p>
      <ul align="left">
        <li><b>New trade entries</b> with entry price, SL, and TP</li>
        <li><b>Trade exits</b> with P&L and reason</li>
        <li><b>Critical errors</b> with timestamps</li>
        <li><b>Bot status updates</b> (start/stop)</li>
      </ul>
    </td>
    <td width="33%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>💻 Web Interface</h3>
      <p>Monitor and control the bot through a web dashboard:</p>
      <ul align="left">
        <li><b>Real-time status</b> monitoring</li>
        <li><b>Account balance</b> and positions</li>
        <li><b>Interactive charts</b> with multiple timeframes</li>
        <li><b>Technical indicators</b> visualization</li>
        <li><b>Performance metrics</b> with equity curve</li>
        <li><b>Trade history</b> with detailed analytics</li>
        <li><b>Start/stop</b> the bot remotely</li>
        <li><b>Adjust settings</b> without restarting</li>
        <li><b>Export data</b> for external analysis</li>
      </ul>
    </td>
  </tr>
</table>

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 📍 Project Structure

```
├── main.py                # Main entry point and trading loop
├── config.py              # Configuration parameters
├── bybit_client.py        # API client for Bybit
├── strategy.py            # Trading strategy implementation

├── risk_manager.py        # Risk management and position sizing
├── order_manager.py       # Order placement and management
├── logger.py              # Logging functionality
├── notifier.py            # Telegram notification system
├── utils.py               # Utility functions
├── web_interface.py       # Web interface for monitoring and control
├── cache/                 # Cached data for API responses
├── logs/                  # Log files
│   └── trading_bot.log    # Main log file
├── templates/             # HTML templates for web interface
│   ├── base.html          # Base template with common layout
│   ├── index.html         # Dashboard page
│   ├── login.html         # Login page
│   ├── settings.html      # Settings page
│   └── trades.html        # Trade history page
├── static/                # Static files for web interface
│   ├── css/               # CSS stylesheets
│   ├── js/                # JavaScript files
│   └── img/               # Images
├── requirements.txt       # Required packages
└── README.md              # Documentation
```

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 🔥 Future Improvements

<details>
<summary>Click to view potential enhancements</summary>

### Advanced Strategy Enhancements
- **Machine Learning Integration**: Add predictive models for enhanced signal generation

### Risk Management Improvements
- **Dynamic Risk Adjustment**: Adjust risk based on market volatility
- **Trailing Stop-Loss**: Implement trailing stops to lock in profits
- **Partial Take-Profits**: Allow multiple take-profit levels
- **Drawdown Protection**: Reduce position sizes after consecutive losses

### System Enhancements
- **WebSocket Implementation**: Use WebSockets for real-time data and reduced latency
- **Performance Analytics**: Add detailed performance metrics and reporting
- **Multi-Exchange Support**: Extend to support multiple exchanges
- **Multi-Asset Trading**: Support trading multiple assets simultaneously

### Web Interface Improvements
- **User Management**: Multiple user accounts with different permission levels
- **Mobile Responsiveness**: Optimize for mobile devices
- **API Documentation**: Interactive API documentation
- **Strategy Builder**: Visual interface for creating custom strategies
- **Alerts System**: Customizable alerts for specific market conditions

### Backtesting Module
- **Historical Data Analysis**: Test strategy on historical data
- **Performance Metrics**: Calculate Sharpe ratio, drawdown, win rate, etc.
- **Parameter Optimization**: Find optimal parameters for the strategy
- **Monte Carlo Simulation**: Assess strategy robustness
</details>

## 🔄 Recent Updates

<details>
<summary>Click to view recent updates</summary>

### API Client Improvements (v1.4.0)
- **Secure API Key Storage**: Added support for storing API keys in `.env` file for better security
- **PyBit V5 API**: Updated to use the latest Bybit V5 API for all operations
- **WebSocket Support**: Enhanced WebSocket functionality for real-time data streaming
- **Data Caching**: Improved caching for historical data to reduce API calls
- **Error Handling**: Enhanced error logging and recovery mechanisms
- **Performance Optimization**: Reduced memory usage and improved response times

### Code Quality Improvements (v1.2.0)
- **Pandas Warnings Fixed**: Updated code to use proper DataFrame indexing
- **Error Handling**: Added comprehensive error handling throughout the codebase
- **Code Documentation**: Improved code comments and documentation
- **Unit Tests**: Added comprehensive unit tests for key components



### Technical Indicator Improvements (v1.2.0)
- **Custom MACD Implementation**: Replaced pandas_ta MACD with robust custom implementation
- **Indicator Validation**: Added validation for input data before calculating indicators
- **Default Values**: Implemented sensible default values when calculations fail
- **Error Handling**: Improved error handling for all technical indicators

### Performance Optimizations (v1.2.0)
- **Reduced API Calls**: Implemented caching to minimize API usage
- **Memory Usage**: Optimized memory usage for long-running sessions
- **Error Recovery**: Added automatic recovery from temporary API failures

### Web Interface Improvements (v1.3.0)
- **Interactive Charts**: Added real-time price charts with multiple timeframe options
- **Technical Indicators**: Added visualization for EMA, RSI, MACD and other indicators
- **Performance Dashboard**: Added detailed performance metrics with equity curve
- **Data Export**: Added functionality to export trade history and settings
- **Enhanced Controls**: Added more control options for strategy parameters
</details>

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## ⚠️ Disclaimer

<div align="center">

*This bot is provided for educational and informational purposes only. Use it at your own risk. Cryptocurrency trading involves substantial risk and is not suitable for everyone. The developers are not responsible for any financial losses incurred from using this bot.*

</div>

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 📄 License

<div align="center">

This project is licensed under the MIT License - see the LICENSE file for details.

</div>