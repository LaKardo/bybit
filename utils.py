"""
Utility functions for the Bybit Trading Bot.
"""

import os
from datetime import datetime

def format_number(number, precision=2):
    """
    Format number with specified precision.

    Args:
        number (float): Number to format.
        precision (int, optional): Decimal precision. Defaults to 2.

    Returns:
        str: Formatted number.
    """
    return f"{number:.{precision}f}"

def format_price(price):
    """
    Format price with appropriate precision based on magnitude.

    Args:
        price (float): Price to format.

    Returns:
        str: Formatted price.
    """
    if price >= 10000:
        return f"{price:.1f}"
    elif price >= 1000:
        return f"{price:.2f}"
    elif price >= 100:
        return f"{price:.3f}"
    elif price >= 10:
        return f"{price:.4f}"
    else:
        return f"{price:.5f}"

def format_timestamp(timestamp, format_str="%Y-%m-%d %H:%M:%S"):
    """
    Format timestamp.

    Args:
        timestamp (int): Timestamp in milliseconds.
        format_str (str, optional): Format string. Defaults to "%Y-%m-%d %H:%M:%S".

    Returns:
        str: Formatted timestamp.
    """
    return datetime.fromtimestamp(timestamp / 1000).strftime(format_str)

def create_directory(directory):
    """
    Create directory if it doesn't exist.

    Args:
        directory (str): Directory path.

    Returns:
        bool: Success or failure.
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception:
        return False

def calculate_pnl_percentage(entry_price, exit_price, side):
    """
    Calculate profit/loss percentage.

    Args:
        entry_price (float): Entry price.
        exit_price (float): Exit price.
        side (str): Position side (Buy or Sell).

    Returns:
        float: Profit/loss percentage.
    """
    if side.upper() == "BUY":
        return (exit_price - entry_price) / entry_price * 100
    else:
        return (entry_price - exit_price) / entry_price * 100

def is_invalid_api_key(api_key, api_secret):
    """
    Check if API keys are invalid or default values.

    Args:
        api_key (str): API key to check.
        api_secret (str): API secret to check.

    Returns:
        bool: True if keys are invalid, False otherwise.
    """
    # Check if keys are None or empty
    if not api_key or not api_secret:
        return True

    # Check for default/example values
    default_keys = [
        "your_bybit_api_key_here",
        "your_bybit_api_secret_here",
        "your_api_key_here",
        "your_api_secret_here",
        "test_api_key",
        "test_api_secret"
    ]

    if api_key in default_keys or api_secret in default_keys:
        return True

    # Check for minimum length requirements (but not too strict)
    # Bybit API keys are typically around 18-24 characters
    # Bybit API secrets are typically around 36-48 characters
    if len(api_key) < 10 or len(api_secret) < 10:
        return True

    return False


def convert_timeframe(timeframe, from_format='bybit_v5', to_format='human'):
    """
    Convert timeframe between different formats.

    Args:
        timeframe (str): Timeframe to convert.
        from_format (str): Source format ('bybit_v5', 'human', 'ccxt').
        to_format (str): Target format ('bybit_v5', 'human', 'ccxt').

    Returns:
        str: Converted timeframe.
    """
    # Mapping between formats
    # bybit_v5: Bybit API V5 format (1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M)
    # human: Human-readable format (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M)
    # ccxt: CCXT library format (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M)

    # Define mappings
    bybit_v5_to_human = {
        '1': '1m', '3': '3m', '5': '5m', '15': '15m', '30': '30m',
        '60': '1h', '120': '2h', '240': '4h', '360': '6h', '720': '12h',
        'D': '1d', 'W': '1w', 'M': '1M'
    }

    human_to_bybit_v5 = {v: k for k, v in bybit_v5_to_human.items()}

    # CCXT format is the same as human-readable format
    ccxt_to_human = {k: k for k in bybit_v5_to_human.values()}
    human_to_ccxt = {v: v for v in bybit_v5_to_human.values()}

    # Convert from source format to human format (intermediate step)
    if from_format == 'bybit_v5':
        human_tf = bybit_v5_to_human.get(timeframe, timeframe)
    elif from_format == 'ccxt':
        human_tf = ccxt_to_human.get(timeframe, timeframe)
    else:  # human format
        human_tf = timeframe

    # Convert from human format to target format
    if to_format == 'bybit_v5':
        return human_to_bybit_v5.get(human_tf, human_tf)
    elif to_format == 'ccxt':
        return human_to_ccxt.get(human_tf, human_tf)
    else:  # human format
        return human_tf
