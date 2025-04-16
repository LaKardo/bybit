"""
Utility functions for the Bybit Trading Bot.
"""

import time
import os
from datetime import datetime

def retry(func, max_retries=3, retry_delay=5, logger=None):
    """
    Retry a function with exponential backoff.
    
    Args:
        func (callable): Function to retry.
        max_retries (int, optional): Maximum number of retries. Defaults to 3.
        retry_delay (int, optional): Initial delay between retries in seconds. Defaults to 5.
        logger (Logger, optional): Logger instance.
        
    Returns:
        Any: Function result or None on failure.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries - 1:
                if logger:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}, retrying in {retry_delay}s")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                if logger:
                    logger.error(f"All {max_retries} attempts failed: {e}")
                return None

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
