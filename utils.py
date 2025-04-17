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
