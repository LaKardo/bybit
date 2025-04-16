"""
Bot Integration Module - Provides integration between the trading bot and web interface
"""
import logging
from datetime import datetime
from flask_socketio import emit
from web_app import socketio

# Configure logging
logger = logging.getLogger(__name__)

# Global reference to the bot instance
bot_instance = None

def set_bot_instance(bot):
    """Set the global bot instance for use in the web interface"""
    global bot_instance
    bot_instance = bot
    logger.info("Bot instance registered with web interface")
    return bot_instance

def get_bot_instance():
    """Get the global bot instance"""
    return bot_instance

def emit_log(message, level="info"):
    """Emit a log message to connected clients"""
    if socketio:
        socketio.emit('log', {
            'message': message,
            'level': level,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

def emit_status_update(data):
    """Emit a status update to connected clients"""
    if socketio:
        socketio.emit('status_update', data)

def emit_trade(data):
    """Emit trade information to connected clients"""
    if socketio:
        socketio.emit('trade', data)

def emit_health_update(data):
    """Emit health check information to connected clients"""
    if socketio:
        socketio.emit('health_update', data)

def emit_metrics_update(data):
    """Emit metrics information to connected clients"""
    if socketio:
        socketio.emit('metrics_update', data)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.debug("Client connected to SocketIO")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.debug("Client disconnected from SocketIO")
