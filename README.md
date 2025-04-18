<div align="center">

# 🤖 Bybit Trading Bot 📈

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge&logo=license&logoColor=white)](LICENSE)
[![Bybit API](https://img.shields.io/badge/bybit-v5%20API-orange.svg?style=for-the-badge&logo=bitcoin&logoColor=white)](https://bybit-exchange.github.io/docs/v5/intro)
[![Status](https://img.shields.io/badge/status-beta-yellow.svg?style=for-the-badge&logo=statuspage&logoColor=white)]()

*A professional Python-based trading bot for Bybit futures trading with EMA/RSI/MACD strategy, interactive web interface, and strict risk management.*

[Features](#-features) • [Requirements](#-requirements) • [Installation](#-installation) • [Configuration](#-configuration) • [Usage](#-usage) • [Strategy](#-trading-strategy) • [Risk Management](#-risk-management) • [Web Interface](#-web-interface) • [Project Structure](#-project-structure) • [Future Improvements](#-future-improvements) • [Disclaimer](#-disclaimer) • [License](#-license)

<hr>

</div>

## ✨ Features

<table>
  <tr>
    <td width="50%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>🏗️ Architecture</h3>
      <ul align="left">
        <li><b>Modular</b>, well-structured code</li>
        <li><b>PyBit V5 API</b> integration</li>
        <li><b>WebSocket support</b> with auto-reconnection</li>
        <li><b>Separate components</b> for different functionalities</li>
        <li><b>Optimized</b> for performance</li>
        <li><b>Robust error handling</b> with detailed logging</li>
      </ul>
    </td>
    <td width="50%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>📊 Technical Analysis</h3>
      <ul align="left">
        <li><b>EMA crossover</b> strategy</li>
        <li><b>RSI</b> for overbought/oversold conditions</li>
        <li><b>MACD</b> for trend confirmation</li>
        <li><b>ATR</b> for volatility-based stops</li>
        <li><b>Optimized indicator</b> calculations</li>
        <li><b>Automatic MACD</b> recalculation with pandas_ta</li>
        <li><b>Efficient partial</b> indicator updates</li>
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
        <li><b>Configurable</b> risk parameters</li>
        <li><b>Single position</b> management</li>
      </ul>
    </td>
    <td width="50%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>🔔 Monitoring & Control</h3>
      <ul align="left">
        <li><b>Interactive web interface</b> with real-time updates</li>
        <li><b>Real-time Telegram</b> notifications</li>
        <li><b>Comprehensive</b> logging system</li>
        <li><b>Health check</b> dashboard with system metrics</li>
        <li><b>Detailed trade</b> information</li>
        <li><b>Error and warning</b> alerts</li>
        <li><b>Account balance</b> and position monitoring</li>
        <li><b>Multiple web interface</b> options</li>
      </ul>
    </td>
  </tr>
</table>

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 🔧 Requirements

- Python 3.8+
- Bybit API key and secret (mainnet)
- Telegram bot token and chat ID (optional, for notifications)
- Web browser (for web interface)
- Required Python packages:
  - pybit (for Bybit API V5)
  - pandas (for data manipulation)
  - numpy (for numerical operations)
  - flask (for web interface)
  - flask-socketio (for real-time updates)
  - flask-login (for web interface authentication)
  - python-dotenv (for environment variables)

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 🚀 Installation

<details>
<summary>Click to expand installation steps</summary>

1. Clone the repository or download the source code:
   ```bash
   git clone <repository-url>
   cd bybit
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
   WEB_USERNAME=your_web_interface_username
   WEB_PASSWORD=your_web_interface_password
   WEB_SECRET_KEY=your_random_secret_key_for_sessions
   ```

5. Configure bot settings by editing `config.py`:
   - Set trading parameters (symbol, timeframe, etc.)
   - Configure strategy parameters (EMA, RSI, MACD settings)
   - Set risk management parameters
   - Configure Telegram notifications (optional)
   - Adjust web interface settings
</details>

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## ⚙️ Configuration

<details>
<summary>Click to view configuration options</summary>

Edit the `config.py` file to customize the bot's behavior:

### API Configuration
API keys are stored in the `.env` file for better security:

```
# In .env file
BYBIT_API_KEY=your_actual_api_key_here
BYBIT_API_SECRET=your_actual_api_secret_here
WEB_USERNAME=your_web_interface_username
WEB_PASSWORD=your_web_interface_password
WEB_SECRET_KEY=your_random_secret_key_for_sessions
```

The `config.py` file automatically loads these values from the `.env` file.

### Trading Parameters
```python
# Trading Parameters
SYMBOL = "BTCUSDT"
TIMEFRAME = "15"  # Bybit API V5 format: 1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M
LEVERAGE = 5  # Leverage to use (1-100)
```

### Strategy Parameters
```python
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
```

### Risk Management
```python
# Risk Management
RISK_PER_TRADE = 0.015  # 1.5% of balance per trade
RISK_REWARD_RATIO = 2  # Risk:Reward ratio (1:2)
SL_ATR_MULTIPLIER = 2  # Stop Loss = Entry Price +/- (ATR * SL_ATR_MULTIPLIER)
```

### Bot Settings
```python
# Bot Settings
DRY_RUN = True  # Set to False for live trading
CHECK_INTERVAL = 60  # Seconds between checks (for non-websocket mode)
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
CLOSE_POSITIONS_ON_SHUTDOWN = True  # Close all positions when bot is shut down
```

### WebSocket Settings
```python
# WebSocket Settings
USE_WEBSOCKET = True  # Use WebSocket for real-time data
WS_RECONNECT_INTERVAL = 60  # Seconds between WebSocket reconnection attempts
```

### Web Interface Settings
```python
# Web Interface Settings
WEB_INTERFACE_ENABLED = True  # Enable web interface
WEB_HOST = "0.0.0.0"  # Web interface host (0.0.0.0 to allow external connections)
WEB_PORT = 5000  # Web interface port
WEB_DEBUG = False  # Enable debug mode for web interface
```
</details>

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 👉 Usage

### Starting the Trading Bot

To start the trading bot with the web interface:

```bash
python main.py
```

This will start both the trading bot and the web interface (if enabled in config.py).

### Starting Only the Web Interface

If you want to start only the web interface without the trading bot, you have several options:

#### Full Web Interface (with Socket.IO)
```bash
python run_web_app.py
```

#### Simple Web Interface (without Socket.IO)
```bash
python simple_web_app.py
```

Or use the provided batch file (Windows):
```bash
start_simple_web_interface.bat
```

#### Very Simple Web Interface (minimal version)
```bash
python very_simple_web_app.py
```

### Accessing the Web Interface

Open a browser and navigate to:

```
http://localhost:5000
```

Or if you've configured a different host/port in config.py, use that instead.

### What the Bot Does:

1. **Initialization**: Loads configuration and initializes all components
2. **Data Collection**: Fetches historical price data from Bybit (via REST API or WebSocket)
3. **Analysis**: Calculates technical indicators (EMA, RSI, MACD, ATR) with optimized methods
4. **Signal Generation**: Identifies trading opportunities based on indicator conditions
5. **Risk Calculation**: Determines position size, stop-loss, and take-profit levels
6. **Order Execution**: Places market orders with appropriate risk parameters
7. **Monitoring**: Continuously monitors positions and market conditions
8. **Reporting**: Logs all activities and sends notifications via Telegram and web interface
9. **Web Interface**: Provides real-time monitoring and control through multiple interface options

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 💸 Trading Strategy

### Long (Buy) Signal 🔼
1. Fast EMA(20) crosses **above** Slow EMA(50)
2. RSI(14) is **below** 70 (not overbought)
3. MACD histogram is **positive** OR MACD line crosses **above** signal line
4. No active short position

### Short (Sell) Signal 🔽
1. Fast EMA(20) crosses **below** Slow EMA(50)
2. RSI(14) is **above** 30 (not oversold)
3. MACD histogram is **negative** OR MACD line crosses **below** signal line
4. No active long position

### Exit Signal 🚪
1. Stop-Loss or Take-Profit is hit
2. Opposite signal appears (e.g., short signal while in a long position)

### Strategy Logic
The strategy combines trend-following (EMA crossover) with momentum (RSI) and trend confirmation (MACD) indicators to generate trading signals. The ATR indicator is used for dynamic stop-loss placement based on market volatility.

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 💰 Risk Management

- **Risk per trade**: 1.5% of available balance
- **Stop-Loss**: Based on ATR (Average True Range)
- **Take-Profit**: Based on Risk-Reward Ratio (1:2)
- **Position sizing**: Calculated to risk exactly the specified percentage
- **Leverage**: Used only for margin calculation, not to increase risk
- **Maximum positions**: Limited to one open position at a time
- **Automatic exit**: Positions are closed when opposite signals appear
- **Shutdown protection**: Option to close all positions on bot shutdown

<div align="center">
<img src="https://i.imgur.com/waxVImv.png" alt="Colorful Divider" width="600">
</div>

## 📝 Monitoring & Control

<table>
  <tr>
    <td width="50%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>📓 Logging</h3>
      <p>The bot logs all activities to both console and file:</p>
      <ul align="left">
        <li><b>Trading signals</b> with indicator values</li>
        <li><b>Order placement</b> and execution details</li>
        <li><b>Balance and position</b> updates</li>
        <li><b>Enhanced errors and warnings</b> with context</li>
        <li><b>WebSocket</b> connection status and reconnection</li>
        <li><b>Function-level</b> detailed logging</li>
        <li><b>System information</b> for critical errors</li>
      </ul>
    </td>
    <td width="50%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>📲 Telegram Notifications</h3>
      <p>If configured, the bot sends notifications via Telegram:</p>
      <ul align="left">
        <li><b>New trade entries</b> with entry price, SL, and TP</li>
        <li><b>Trade exits</b> with P&L and reason</li>
        <li><b>Critical errors</b> with timestamps</li>
        <li><b>Bot status updates</b> (start/stop)</li>
        <li><b>Account balance</b> updates</li>
      </ul>
    </td>
  </tr>
</table>

## 💻 Web Interface

The bot includes multiple web interface options for monitoring and controlling your trading:

<table>
  <tr>
    <td width="50%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>📊 Dashboard Features</h3>
      <ul align="left">
        <li><b>Real-time status</b> monitoring</li>
        <li><b>Account balance</b> and positions</li>
        <li><b>Interactive price charts</b> with multiple timeframes</li>
        <li><b>Technical indicators</b> visualization (EMA, RSI, MACD)</li>
        <li><b>Trade history</b> with detailed analytics</li>
        <li><b>Real-time log</b> streaming</li>
        <li><b>Chart settings memory</b> for user preferences</li>
      </ul>
    </td>
    <td width="50%" align="center" bgcolor="#f8f9fa" style="border-radius:10px; padding:15px;">
      <h3>⚙️ Control Features</h3>
      <ul align="left">
        <li><b>Start/stop</b> the bot remotely</li>
        <li><b>Close positions</b> manually</li>
        <li><b>Adjust strategy parameters</b> without restarting</li>
        <li><b>Change trading pair</b> and timeframe</li>
        <li><b>Toggle between real trading</b> and simulation mode</li>
        <li><b>Secure login</b> with username/password protection</li>
        <li><b>Multiple interface options</b> (full, simple, very simple)</li>
      </ul>
    </td>
  </tr>
</table>

### Interface Options

1. **Full Web Interface** - Complete dashboard with real-time updates via Socket.IO
   ```bash
   python run_web_app.py
   ```

2. **Simple Web Interface** - Streamlined interface without Socket.IO
   ```bash
   python simple_web_app.py
   # or
   start_simple_web_interface.bat
   ```

3. **Very Simple Web Interface** - Minimal interface for basic monitoring
   ```bash
   python very_simple_web_app.py
   ```

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
├── health_check.py        # Health check system for monitoring bot performance
├── utils.py               # Utility functions
├── web_interface.py       # Web interface for monitoring and control
├── run_web_app.py         # Script to run only the web interface
├── simple_web_app.py      # Simplified web interface version
├── test_macd_calculation.py # Test script for MACD calculation
├── test_websocket_reconnection.py # Test script for WebSocket reconnection
├── install_web_dependencies.py # Script to install web dependencies
├── start_simple_web_interface.bat # Batch file to start simple web interface
├── web_app/               # Web application package
│   ├── __init__.py        # Web app initialization
│   ├── main/              # Main routes
│   ├── api/               # API routes
│   └── auth/              # Authentication routes
├── cache/                 # Cached data for API responses
├── logs/                  # Log files
│   └── trading_bot.log    # Main log file
├── templates/             # HTML templates for web interface
│   ├── base.html          # Base template with common layout
│   ├── index.html         # Dashboard page
│   ├── login.html         # Login page
│   ├── settings.html      # Settings page
│   ├── trades.html        # Trade history page
│   ├── simple_index.html  # Simple interface dashboard
│   └── very_simple_index.html # Very simple interface dashboard
├── static/                # Static files for web interface
│   ├── css/               # CSS stylesheets
│   ├── js/                # JavaScript files
│   │   ├── api_v5.js      # Bybit API V5 integration
│   │   ├── chart-settings.js # Chart configuration
│   │   ├── ui-enhancements.js # UI improvements
│   │   └── micro-interactions.js # UI animations
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
- **Additional Indicators**: Implement more technical indicators for signal confirmation
- **Custom Strategy Builder**: Allow users to create and test custom strategies

### Risk Management Improvements
- **Dynamic Risk Adjustment**: Adjust risk based on market volatility
- **Trailing Stop-Loss**: Implement trailing stops to lock in profits
- **Partial Take-Profits**: Allow multiple take-profit levels
- **Drawdown Protection**: Reduce position sizes after consecutive losses

### System Enhancements
- **Performance Analytics**: Add detailed performance metrics and reporting
- **Multi-Exchange Support**: Extend to support multiple exchanges
- **Multi-Asset Trading**: Support trading multiple assets simultaneously
- **Distributed Architecture**: Scale the system across multiple servers

### Web Interface Improvements
- **User Management**: Multiple user accounts with different permission levels
- **Mobile Responsiveness**: Optimize for mobile devices
- **API Documentation**: Interactive API documentation
- **Strategy Builder**: Visual interface for creating custom strategies
- **Alerts System**: Customizable alerts for specific market conditions
- **Dark/Light Mode Toggle**: Add theme switching capability

### Backtesting Module
- **Historical Data Analysis**: Test strategy on historical data
- **Performance Metrics**: Calculate Sharpe ratio, drawdown, win rate, etc.
- **Parameter Optimization**: Find optimal parameters for the strategy
- **Monte Carlo Simulation**: Assess strategy robustness
</details>

## 🛠️ Recent Improvements

<details>
<summary>Click to view recent enhancements</summary>

### Health Check System
- **System Monitoring**: Added comprehensive health check system to monitor bot performance
- **Component Status Tracking**: Real-time tracking of all bot components' health status
- **Performance Metrics**: Detailed metrics for CPU, memory, API response times, and trading performance
- **Health Dashboard**: Interactive web dashboard for visualizing system health
- **Automatic Issue Detection**: Proactive detection and reporting of potential issues

### WebSocket Improvements
- **Robust Reconnection Logic**: Added exponential backoff for WebSocket reconnection
- **Subscription Tracking**: Improved tracking of subscribed topics for automatic resubscription
- **Error Handling**: Better handling of "already subscribed" errors
- **Connection Monitoring**: Enhanced monitoring of WebSocket connection status

### Technical Analysis Enhancements
- **Optimized MACD Calculation**: Added support for pandas_ta library for faster and more accurate MACD calculation
- **Partial Data Updates**: Improved handling of partial dataframe updates for better performance
- **Fallback Mechanisms**: Added fallback to manual calculation if pandas_ta is not available

### Error Handling & Logging
- **Enhanced Error Context**: Added function name and line number to error logs
- **Categorized Error Handling**: Better categorization of retryable vs. non-retryable errors
- **System Information**: Added system information logging for critical errors
- **Exponential Backoff**: Improved retry logic with proper exponential backoff

### Code Cleanup
- **Removed CCXT References**: Cleaned up code by removing all references to CCXT
- **Simplified Timeframe Conversion**: Updated timeframe conversion to focus only on Bybit formats
- **Improved Code Documentation**: Enhanced docstrings and comments
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