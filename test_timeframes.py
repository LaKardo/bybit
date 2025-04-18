"""
Test script for timeframe conversion and display in the web interface.
"""

import os
import sys
import time
from utils import convert_timeframe

def test_timeframe_conversion():
    """Test timeframe conversion between different formats."""
    print("\nTesting timeframe conversion...")
    
    # Test Bybit V5 to human-readable format
    bybit_v5_timeframes = ['1', '3', '5', '15', '30', '60', '120', '240', '360', '720', 'D', 'W', 'M']
    for tf in bybit_v5_timeframes:
        human_tf = convert_timeframe(tf, from_format='bybit_v5', to_format='human')
        print(f"Bybit V5: {tf} -> Human: {human_tf}")
    
    print("\nTesting human-readable to Bybit V5 format...")
    # Test human-readable to Bybit V5 format
    human_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w', '1M']
    for tf in human_timeframes:
        bybit_tf = convert_timeframe(tf, from_format='human', to_format='bybit_v5')
        print(f"Human: {tf} -> Bybit V5: {bybit_tf}")
    
    print("\nTesting round-trip conversion...")
    # Test round-trip conversion
    for tf in bybit_v5_timeframes:
        human_tf = convert_timeframe(tf, from_format='bybit_v5', to_format='human')
        back_to_bybit = convert_timeframe(human_tf, from_format='human', to_format='bybit_v5')
        print(f"Bybit V5: {tf} -> Human: {human_tf} -> Back to Bybit V5: {back_to_bybit}")
        assert tf == back_to_bybit, f"Round-trip conversion failed for {tf}"

if __name__ == "__main__":
    print("=" * 50)
    print("TIMEFRAME CONVERSION TEST")
    print("=" * 50)
    
    # Test timeframe conversion
    test_timeframe_conversion()
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 50)
