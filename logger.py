import logging
import os
import sys
import json
import time
import traceback
import platform
import threading
import socket
from datetime import datetime
import config
try:
    from web_app.bot_integration import emit_log
except ImportError:
    def emit_log(message, level="info"):
        pass
class StructuredFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%', use_json=False):
        super().__init__(fmt, datefmt, style)
        self.use_json = use_json
    def format(self, record):
        record.threadName = threading.current_thread().name
        record.hostname = socket.gethostname()
        formatted_message = super().format(record)
        if self.use_json:
            log_entry = {
                'timestamp': self.formatTime(record, self.datefmt),
                'level': record.levelname,
                'message': record.getMessage(),
                'logger': record.name,
                'thread': record.threadName,
                'hostname': record.hostname,
                'path': record.pathname,
                'line': record.lineno,
                'function': record.funcName
            }
            if record.exc_info:
                log_entry['exception'] = self.formatException(record.exc_info)
            if hasattr(record, 'custom_fields'):
                log_entry.update(record.custom_fields)
            return json.dumps(log_entry)
        else:
            return formatted_message
class Logger:
    def __init__(self, log_file=None, log_level=None):
        self.log_file = log_file or config.LOG_FILE
        self.log_level = log_level or config.LOG_LEVEL
        self.use_json = getattr(config, 'LOG_JSON_FORMAT', False)
        self.log_rotation = getattr(config, 'LOG_ROTATION', True)
        self.max_log_size = getattr(config, 'MAX_LOG_SIZE_MB', 10) * 1024 * 1024
        self.backup_count = getattr(config, 'LOG_BACKUP_COUNT', 5)
        self.performance_tracking = getattr(config, 'PERFORMANCE_TRACKING', True)
        self.performance_data = {}
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        self.logger = logging.getLogger("TradingBot")
        self.logger.setLevel(self._get_log_level(self.log_level))
        self.logger.handlers = []
        if self.log_rotation:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_log_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
        else:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(self._get_log_level(self.log_level))
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._get_log_level(self.log_level))
        standard_format = '[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s'
        detailed_format = '[%(asctime)s] [%(levelname)s] [%(threadName)s] [%(pathname)s:%(lineno)d] %(message)s'
        file_formatter = StructuredFormatter(
            detailed_format if self._get_log_level(self.log_level) <= logging.DEBUG else standard_format,
            datefmt='%Y-%m-%d %H:%M:%S',
            use_json=self.use_json
        )
        console_formatter = StructuredFormatter(
            standard_format,
            datefmt='%Y-%m-%d %H:%M:%S',
            use_json=False
        )
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        if self.performance_tracking:
            perf_log_file = os.path.join(os.path.dirname(self.log_file), 'performance.log')
            perf_handler = logging.FileHandler(perf_log_file, encoding='utf-8')
            perf_handler.setLevel(logging.INFO)
            perf_formatter = StructuredFormatter(
                '[%(asctime)s] [PERFORMANCE] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                use_json=self.use_json
            )
            perf_handler.setFormatter(perf_formatter)
            self.perf_logger = logging.getLogger("TradingBot.Performance")
            self.perf_logger.setLevel(logging.INFO)
            self.perf_logger.handlers = []
            self.perf_logger.addHandler(perf_handler)

    def get_logs(self, limit=100):
        """Retrieve the last N log lines from the log file."""
        try:
            if not os.path.exists(self.log_file):
                return []
            
            lines = []
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # Read all lines efficiently
                all_lines = f.readlines()
                # Get the last 'limit' lines
                lines = all_lines[-limit:]
            
            # Reverse lines to show newest first, if desired by the frontend
            # Or keep as is (oldest first within the limit)
            return [line.strip() for line in lines]
        except Exception as e:
            self.error(f"Error reading log file: {e}")
            return []
            self.perf_logger.propagate = False
        self._log_system_info()
        self.info(f"Enhanced logger initialized with level: {self.log_level}")
    def _log_system_info(self):
        try:
            import psutil
            memory_info = f"{psutil.virtual_memory().percent}% used"
            cpu_info = f"{psutil.cpu_percent()}% used"
            disk_info = f"{psutil.disk_usage('/').percent}% used"
        except ImportError:
            memory_info = "psutil not available"
            cpu_info = "psutil not available"
            disk_info = "psutil not available"
        system_info = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "hostname": socket.gethostname(),
            "memory": memory_info,
            "cpu": cpu_info,
            "disk": disk_info,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": time.tzname
        }
        self.logger.info(f"System information: {system_info}")
    def start_performance_tracking(self, operation_name):
        if not self.performance_tracking:
            return None
        tracking_id = f"{operation_name}_{time.time()}"
        self.performance_data[tracking_id] = {
            "operation": operation_name,
            "start_time": time.time(),
            "checkpoints": []
        }
        return tracking_id
    def add_performance_checkpoint(self, tracking_id, checkpoint_name):
        if not self.performance_tracking or tracking_id not in self.performance_data:
            return
        self.performance_data[tracking_id]["checkpoints"].append({
            "name": checkpoint_name,
            "time": time.time()
        })
    def end_performance_tracking(self, tracking_id, additional_info=None):
        if not self.performance_tracking or tracking_id not in self.performance_data:
            return
        end_time = time.time()
        perf_data = self.performance_data[tracking_id]
        start_time = perf_data["start_time"]
        total_time = end_time - start_time
        checkpoints = perf_data["checkpoints"]
        checkpoint_durations = []
        prev_time = start_time
        for checkpoint in checkpoints:
            checkpoint_time = checkpoint["time"]
            duration = checkpoint_time - prev_time
            checkpoint_durations.append({
                "name": checkpoint["name"],
                "duration": duration,
                "percentage": (duration / total_time) * 100 if total_time > 0 else 0
            })
            prev_time = checkpoint_time
        if checkpoints:
            final_duration = end_time - prev_time
            checkpoint_durations.append({
                "name": "final",
                "duration": final_duration,
                "percentage": (final_duration / total_time) * 100 if total_time > 0 else 0
            })
        log_data = {
            "operation": perf_data["operation"],
            "total_time": total_time,
            "checkpoints": checkpoint_durations
        }
        if additional_info:
            log_data["additional_info"] = additional_info
        if hasattr(self, 'perf_logger'):
            self.perf_logger.info(f"Performance data for {perf_data['operation']}: {json.dumps(log_data)}")
        else:
            self.logger.info(f"Performance data for {perf_data['operation']}: {json.dumps(log_data)}")
        del self.performance_data[tracking_id]
        return log_data
    def log_api_call(self, method, endpoint, params=None, response=None, status_code=None, error=None, duration=None):
        log_entry = {
            "method": method,
            "endpoint": endpoint,
            "params": params,
            "status_code": status_code,
            "duration_ms": round(duration * 1000, 2) if duration else None,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        if error:
            log_entry["error"] = str(error)
            self.logger.error(f"API call failed: {json.dumps(log_entry)}")
        else:
            self.logger.debug(f"API call: {json.dumps(log_entry)}")
        if response and self.logger.isEnabledFor(logging.DEBUG):
            response_str = str(response)
            if len(response_str) > 1000:
                response_str = response_str[:1000] + "... [truncated]"
            self.logger.debug(f"API response: {response_str}")
    def _get_log_level(self, level_str):
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return levels.get(level_str.upper(), logging.INFO)
    def debug(self, message, extra=None):
        self._log(message, "debug", extra)
    def info(self, message, extra=None):
        self._log(message, "info", extra)
    def warning(self, message, extra=None):
        self._log(message, "warning", extra)
    def error(self, message, extra=None, exc_info=False):
        self._log(message, "error", extra, exc_info)
    def critical(self, message, extra=None, exc_info=True):
        self._log(message, "critical", extra, exc_info)
    def _log(self, message, level, extra=None, exc_info=False):
        if extra:
            extra_copy = extra.copy() if extra else {}
            if not hasattr(logging, 'custom_fields'):
                extra_copy['custom_fields'] = extra
            if level == "debug":
                self.logger.debug(message, extra=extra_copy, exc_info=exc_info)
            elif level == "info":
                self.logger.info(message, extra=extra_copy, exc_info=exc_info)
            elif level == "warning":
                self.logger.warning(message, extra=extra_copy, exc_info=exc_info)
            elif level == "error":
                self.logger.error(message, extra=extra_copy, exc_info=exc_info)
            elif level == "critical":
                self.logger.critical(message, extra=extra_copy, exc_info=exc_info)
        else:
            if level == "debug":
                self.logger.debug(message, exc_info=exc_info)
            elif level == "info":
                self.logger.info(message, exc_info=exc_info)
            elif level == "warning":
                self.logger.warning(message, exc_info=exc_info)
            elif level == "error":
                self.logger.error(message, exc_info=exc_info)
            elif level == "critical":
                self.logger.critical(message, exc_info=exc_info)
        emit_log(message, level)
    def trade(self, action, symbol, side, quantity, price, sl=None, tp=None, extra_info=None):
        trade_data = {
            "action": action,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "trade_id": f"{action}_{symbol}_{side}_{int(time.time())}"
        }
        if sl:
            trade_data["stop_loss"] = sl
        if tp:
            trade_data["take_profit"] = tp
        if extra_info and isinstance(extra_info, dict):
            trade_data.update(extra_info)
        message = f"TRADE: {action} {side} {quantity} {symbol} @ {price}"
        if sl:
            message += f", SL: {sl}"
        if tp:
            message += f", TP: {tp}"
        self.info(message, extra=trade_data)
    def signal(self, symbol, timeframe, signal_type, indicators=None, extra_info=None):
        signal_data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "signal_type": signal_type,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "signal_id": f"{signal_type}_{symbol}_{timeframe}_{int(time.time())}"
        }
        if indicators and isinstance(indicators, dict):
            signal_data["indicators"] = indicators
        if extra_info and isinstance(extra_info, dict):
            signal_data.update(extra_info)
        message = f"SIGNAL: {signal_type} on {symbol} ({timeframe})"
        if indicators:
            message += f", Indicators: {indicators}"
        self.info(message, extra=signal_data)
    def balance(self, available_balance, wallet_balance, unrealized_pnl=None, extra_info=None):
        balance_data = {
            "available_balance": available_balance,
            "wallet_balance": wallet_balance,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        if unrealized_pnl is not None:
            balance_data["unrealized_pnl"] = unrealized_pnl
        if extra_info and isinstance(extra_info, dict):
            balance_data.update(extra_info)
        message = f"BALANCE: Available: {available_balance}, Wallet: {wallet_balance}"
        if unrealized_pnl is not None:
            message += f", Unrealized PnL: {unrealized_pnl}"
        self.info(message, extra=balance_data)
    def position(self, symbol, side, size, entry_price, liq_price=None, unrealized_pnl=None, extra_info=None):
        position_data = {
            "symbol": symbol,
            "side": side,
            "size": size,
            "entry_price": entry_price,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "position_id": f"{symbol}_{side}_{int(time.time())}"
        }
        if liq_price:
            position_data["liquidation_price"] = liq_price
        if unrealized_pnl is not None:
            position_data["unrealized_pnl"] = unrealized_pnl
        if extra_info and isinstance(extra_info, dict):
            position_data.update(extra_info)
        message = f"POSITION: {side} {size} {symbol} @ {entry_price}"
        if liq_price:
            message += f", Liq: {liq_price}"
        if unrealized_pnl is not None:
            message += f", PnL: {unrealized_pnl}"
        self.info(message, extra=position_data)
    def log_error_with_context(self, error, context=None, exc_info=True):
        """
        Enhanced error logging with context using Python 3.11's improved exception handling.

        Python 3.11 provides more detailed exception information including better error messages
        and more precise error locations.
        """
        if isinstance(error, Exception):
            error_message = str(error)
            error_type = error.__class__.__name__

            # Python 3.11+ provides more detailed exception information
            if sys.version_info >= (3, 11):
                # Get exception notes if available (Python 3.11+)
                notes = getattr(error, "__notes__", [])
                if notes:
                    error_message += " | Notes: " + "; ".join(notes)

                # Check for exception group (Python 3.11+)
                if hasattr(error, "__cause__") and error.__cause__:
                    error_message += f" | Caused by: {error.__cause__.__class__.__name__}: {error.__cause__}"
        else:
            error_message = str(error)
            error_type = "Unknown"

        error_data = {
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "error_id": f"{error_type}_{int(time.time())}"
        }

        if exc_info and isinstance(error, Exception):
            # Get enhanced traceback information
            try:
                # Python 3.11+ provides more detailed traceback with better formatting
                tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
                error_data["stack_trace"] = tb_str
            except Exception:
                error_data["stack_trace"] = traceback.format_exc()

        if context and isinstance(context, dict):
            error_data["context"] = context

        message = f"ERROR: {error_message}"
        if context:
            message += f" (Context: {context})"

        self.error(message, extra=error_data, exc_info=exc_info)
