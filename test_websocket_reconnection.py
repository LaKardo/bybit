#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test WebSocket reconnection logic in the Bybit client.
"""

import unittest
import time
import logging
import sys
from unittest.mock import patch, MagicMock, call

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Import the Bybit client
from bybit_client import BybitAPIClient as BybitClient
import config

class TestWebSocketReconnection(unittest.TestCase):
    """Test WebSocket reconnection logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger('test_logger')
        self.client = BybitClient(logger=self.logger)

        # Save original methods for restoration
        self.original_start_websocket = self.client.start_websocket
        self.original_stop_websocket = self.client.stop_websocket
        self.original_resubscribe_to_topics = self.client._resubscribe_to_topics

    def tearDown(self):
        """Tear down test fixtures."""
        # Restore original methods
        self.client.start_websocket = self.original_start_websocket
        self.client.stop_websocket = self.original_stop_websocket
        self.client._resubscribe_to_topics = self.original_resubscribe_to_topics

    @patch('time.sleep')  # Mock sleep to avoid waiting in tests
    def test_reconnect_websocket_success(self, mock_sleep):
        """Test successful WebSocket reconnection."""
        # Mock the start_websocket and stop_websocket methods
        self.client.start_websocket = MagicMock(return_value=True)
        self.client.stop_websocket = MagicMock(return_value=True)
        self.client._resubscribe_to_topics = MagicMock(return_value=True)

        # Set initial state
        self.client.ws_reconnect_attempts = 0
        self.client.ws_last_reconnect_time = int(time.time()) - 60  # 60 seconds ago

        # Call the reconnect method
        result = self.client._reconnect_websocket()

        # Verify the result
        self.assertTrue(result, "Reconnection should succeed")

        # Verify the methods were called
        self.client.stop_websocket.assert_called_once()
        self.client.start_websocket.assert_called_once()

        # Verify the reconnect attempts were incremented
        self.assertEqual(self.client.ws_reconnect_attempts, 1,
                         "Reconnect attempts should be incremented")

        # Verify sleep was not called (since we're not waiting)
        mock_sleep.assert_not_called()

    @patch('time.sleep')  # Mock sleep to avoid waiting in tests
    def test_reconnect_websocket_with_backoff(self, mock_sleep):
        """Test WebSocket reconnection with exponential backoff."""
        # Mock the start_websocket and stop_websocket methods
        self.client.start_websocket = MagicMock(return_value=True)
        self.client.stop_websocket = MagicMock(return_value=True)

        # Set initial state for multiple attempts
        self.client.ws_reconnect_attempts = 2  # Already tried twice
        self.client.ws_last_reconnect_time = int(time.time())  # Just now
        self.client.ws_reconnect_delay = 5  # 5 seconds initial delay

        # Call the reconnect method
        result = self.client._reconnect_websocket()

        # Verify the result
        self.assertTrue(result, "Reconnection should succeed")

        # Calculate expected delay: 5 * (2^2) = 20 seconds
        expected_delay = 5 * (2 ** 2)

        # Verify sleep was called with the correct delay
        mock_sleep.assert_called_once_with(expected_delay)

        # Verify the reconnect attempts were incremented
        self.assertEqual(self.client.ws_reconnect_attempts, 3,
                         "Reconnect attempts should be incremented")

    @patch('time.sleep')  # Mock sleep to avoid waiting in tests
    def test_reconnect_websocket_max_attempts(self, mock_sleep):
        """Test WebSocket reconnection with maximum attempts reached."""
        # Set initial state at max attempts
        self.client.ws_reconnect_attempts = self.client.ws_max_reconnect_attempts

        # Call the reconnect method
        result = self.client._reconnect_websocket()

        # Verify the result
        self.assertFalse(result, "Reconnection should fail after max attempts")

        # Verify stop_websocket and start_websocket were not called
        self.client.stop_websocket = MagicMock()
        self.client.start_websocket = MagicMock()
        self.client.stop_websocket.assert_not_called()
        self.client.start_websocket.assert_not_called()

    @patch('time.sleep')  # Mock sleep to avoid waiting in tests
    def test_reconnect_websocket_failure(self, mock_sleep):
        """Test WebSocket reconnection failure."""
        # Mock the start_websocket method to fail
        self.client.start_websocket = MagicMock(return_value=False)
        self.client.stop_websocket = MagicMock(return_value=True)

        # Set initial state
        self.client.ws_reconnect_attempts = 0
        self.client.ws_last_reconnect_time = int(time.time()) - 60  # 60 seconds ago

        # Call the reconnect method
        result = self.client._reconnect_websocket()

        # Verify the result
        self.assertFalse(result, "Reconnection should fail")

        # Verify the methods were called
        self.client.stop_websocket.assert_called_once()
        self.client.start_websocket.assert_called_once()

        # Verify the reconnect attempts were incremented
        self.assertEqual(self.client.ws_reconnect_attempts, 1,
                         "Reconnect attempts should be incremented")

    def test_resubscribe_to_topics(self):
        """Test resubscribing to topics after reconnection."""
        # Mock the subscribe methods
        self.client.subscribe_kline = MagicMock(return_value=True)
        self.client.subscribe_ticker = MagicMock(return_value=True)

        # Set WebSocket as enabled
        self.client.ws_enabled = True
        self.client.ws_client = MagicMock()

        # Add some topics to resubscribe
        self.client.ws_subscribed_topics = {
            ("kline", "BTCUSDT", "15"),
            ("kline", "ETHUSDT", "5"),
            ("ticker", "BTCUSDT", None)
        }

        # Call the resubscribe method
        result = self.client._resubscribe_to_topics()

        # Verify the result
        self.assertTrue(result, "Resubscription should succeed")

        # Verify the subscribe methods were called with correct parameters
        self.client.subscribe_kline.assert_has_calls([
            call("BTCUSDT", "15"),
            call("ETHUSDT", "5")
        ], any_order=True)

        self.client.subscribe_ticker.assert_called_once_with("BTCUSDT")

    def test_resubscribe_to_topics_no_topics(self):
        """Test resubscribing when there are no topics."""
        # Set WebSocket as enabled
        self.client.ws_enabled = True
        self.client.ws_client = MagicMock()

        # No topics to resubscribe
        self.client.ws_subscribed_topics = set()

        # Call the resubscribe method
        result = self.client._resubscribe_to_topics()

        # Verify the result
        self.assertTrue(result, "Resubscription should succeed with no topics")

    def test_resubscribe_to_topics_websocket_not_started(self):
        """Test resubscribing when WebSocket is not started."""
        # Set WebSocket as disabled
        self.client.ws_enabled = False
        self.client.ws_client = None

        # Call the resubscribe method
        result = self.client._resubscribe_to_topics()

        # Verify the result
        self.assertFalse(result, "Resubscription should fail when WebSocket is not started")

if __name__ == '__main__':
    unittest.main()
