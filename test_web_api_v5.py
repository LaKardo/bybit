"""
Test script for the web interface with Bybit API V5.
This script tests the web interface API endpoints with the new Bybit API V5 format.
"""

import os
import sys
import time
import json
import threading
from flask import Flask, jsonify
from flask_socketio import SocketIO
import config
from logger import Logger
from bybit_client import BybitAPIClient
from web_interface import WebInterface

class MockBot:
    """Mock trading bot for testing."""
    def __init__(self):
        self.logger = Logger(log_file="logs/test_web_api_v5.log", log_level="DEBUG")
        self.bybit_client = BybitAPIClient(logger=self.logger)
        self.symbol = config.SYMBOL
        self.timeframe = config.TIMEFRAME
        self.dry_run = True
        self.running = False
        self.use_websocket = True
        self.trade_history = []
        
    def run(self):
        """Start the bot."""
        self.running = True
        self.logger.info("Bot started")
        
    def shutdown(self):
        """Stop the bot."""
        self.running = False
        self.logger.info("Bot stopped")

def test_web_api_v5():
    """Test the web interface API endpoints with Bybit API V5."""
    print("\nTesting web interface API endpoints with Bybit API V5...")
    
    # Create mock bot
    bot = MockBot()
    
    # Initialize web interface
    web_interface = WebInterface(bot=bot, logger=bot.logger)
    
    # Start web interface in a separate thread
    web_thread = threading.Thread(
        target=web_interface.run,
        kwargs={
            'host': '127.0.0.1',
            'port': 5000,
            'debug': False
        }
    )
    web_thread.daemon = True
    web_thread.start()
    
    print("Web interface started on http://127.0.0.1:5000")
    print("Please open this URL in your browser to test the web interface")
    print("Press Ctrl+C to stop the test")
    
    try:
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTest stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    print("=" * 50)
    print("WEB INTERFACE API V5 TEST")
    print("=" * 50)
    
    # Test web interface API endpoints with Bybit API V5
    test_web_api_v5()
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED")
    print("=" * 50)
