import os
import time
import json
import threading
import sqlite3
from datetime import datetime, timedelta
from collections import deque
class MetricsCollector:
    def __init__(self, bot=None, logger=None):
        self.bot = bot
        self.logger = logger
        self.metrics = {}
        self.metrics_history = {}
        self.collection_interval = 10
        self.retention_period = 7
        self.max_points = 10000
        self.db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data',
            'metrics.db'
        )
        self._initialize_database()
        self.running = False
        self.collection_thread = None
        self._initialize_metrics()
        if self.logger:
            self.logger.info("Metrics collector initialized")
    def _initialize_database(self):
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    tags TEXT
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics (timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_category_name ON metrics (category, name)')
            conn.commit()
            conn.close()
            if self.logger:
                self.logger.debug(f"Metrics database initialized at {self.db_path}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error initializing metrics database: {e}")
    def _initialize_metrics(self):
        self.metrics = {
            'system': {
                'cpu_usage': 0,
                'memory_usage': 0,
                'disk_usage': 0
            },
            'api': {
                'calls_total': 0,
                'calls_successful': 0,
                'calls_failed': 0,
                'latency_avg': 0,
                'latency_max': 0,
                'rate_limit_hits': 0
            },
            'websocket': {
                'messages_received': 0,
                'messages_sent': 0,
                'reconnects': 0,
                'latency': 0
            },
            'trading': {
                'trades_total': 0,
                'trades_successful': 0,
                'trades_failed': 0,
                'profit_loss': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0
            },
            'strategy': {
                'signals_generated': 0,
                'signals_executed': 0,
                'calculation_time': 0
            },
            'performance': {
                'loop_time': 0,
                'data_processing_time': 0,
                'strategy_time': 0,
                'order_management_time': 0
            }
        }
        for category in self.metrics:
            self.metrics_history[category] = {}
            for metric in self.metrics[category]:
                self.metrics_history[category][metric] = deque(maxlen=self.max_points)
    def start(self):
        if self.running:
            if self.logger:
                self.logger.warning("Metrics collector already running")
            return
        self.running = True
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        if self.logger:
            self.logger.info("Metrics collector started")
    def stop(self):
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=1.0)
            self.collection_thread = None
        if self.logger:
            self.logger.info("Metrics collector stopped")
    def _collection_loop(self):
        psutil_available = self._check_psutil()
        while self.running:
            try:
                if psutil_available:
                    self._collect_system_metrics()
                if self.bot:
                    self._collect_bot_metrics()
                self._store_metrics()
                self._cleanup_old_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in metrics collection: {e}")
                time.sleep(self.collection_interval)

    def _check_psutil(self):
        try:
            import psutil
            return True
        except ImportError:
            if self.logger:
                self.logger.warning("psutil library not found. System metrics will not be collected. Install with 'pip install psutil'")
            return False

    def _collect_system_metrics(self):
        # This function now assumes psutil is available
        try:
            import psutil # Import again within the function scope
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            self.update_metric('system', 'cpu_usage', cpu_usage)
            self.update_metric('system', 'memory_usage', memory_usage)
            self.update_metric('system', 'disk_usage', disk_usage)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error collecting system metrics: {e}")
    def _collect_bot_metrics(self):
        try:
            if hasattr(self.bot, 'bybit_client') and self.bot.bybit_client:
                if hasattr(self.bot.bybit_client, 'rate_limiter') and self.bot.bybit_client.rate_limiter:
                    rate_limiter = self.bot.bybit_client.rate_limiter
                    rate_limit_stats = rate_limiter.get_stats()
                    self.update_metric('api', 'calls_total', sum(rate_limit_stats.values()))
                    self.update_metric('api', 'rate_limit_hits', rate_limit_stats.get('rate_limit_hits', 0))
                if hasattr(self.bot.bybit_client, 'circuit_breaker_registry') and self.bot.bybit_client.circuit_breaker_registry:
                    circuit_breaker_registry = self.bot.bybit_client.circuit_breaker_registry
                    circuit_breaker_states = circuit_breaker_registry.get_all_states()
                    open_circuits = sum(1 for state in circuit_breaker_states.values() if state == 'OPEN')
                    self.update_metric('api', 'open_circuits', open_circuits)
            if hasattr(self.bot, 'bybit_client') and self.bot.bybit_client and hasattr(self.bot.bybit_client, 'ws_client'):
                self.update_metric('websocket', 'reconnects', getattr(self.bot.bybit_client, 'ws_reconnect_attempts', 0))
                ws_connected = self.bot.bybit_client.check_websocket_health() if hasattr(self.bot.bybit_client, 'check_websocket_health') else False
                self.update_metric('websocket', 'connected', 1 if ws_connected else 0)
            if hasattr(self.bot, 'trade_history'):
                trade_history = self.bot.trade_history
                trades_total = len(trade_history)
                trades_successful = sum(1 for trade in trade_history if trade.get('pnl', 0) > 0)
                trades_failed = sum(1 for trade in trade_history if trade.get('pnl', 0) <= 0)
                profit_loss = sum(trade.get('pnl', 0) for trade in trade_history)
                win_rate = (trades_successful / trades_total * 100) if trades_total > 0 else 0
                profits = [trade.get('pnl', 0) for trade in trade_history if trade.get('pnl', 0) > 0]
                losses = [trade.get('pnl', 0) for trade in trade_history if trade.get('pnl', 0) < 0]
                avg_profit = sum(profits) / len(profits) if profits else 0
                avg_loss = sum(losses) / len(losses) if losses else 0
                self.update_metric('trading', 'trades_total', trades_total)
                self.update_metric('trading', 'trades_successful', trades_successful)
                self.update_metric('trading', 'trades_failed', trades_failed)
                self.update_metric('trading', 'profit_loss', profit_loss)
                self.update_metric('trading', 'win_rate', win_rate)
                self.update_metric('trading', 'avg_profit', avg_profit)
                self.update_metric('trading', 'avg_loss', avg_loss)
            if hasattr(self.bot, 'strategy') and self.bot.strategy:
                self.update_metric('strategy', 'signals_generated', getattr(self.bot.strategy, 'signals_generated', 0))
                self.update_metric('strategy', 'signals_executed', getattr(self.bot.strategy, 'signals_executed', 0))
                self.update_metric('strategy', 'calculation_time', getattr(self.bot.strategy, 'calculation_time', 0))
            if hasattr(self.bot, 'performance_metrics'):
                for metric, value in self.bot.performance_metrics.items():
                    self.update_metric('performance', metric, value)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error collecting bot metrics: {e}")
    def update_metric(self, category, name, value, tags=None):
        try:
            if category not in self.metrics:
                self.metrics[category] = {}
                self.metrics_history[category] = {}
            if name not in self.metrics[category]:
                self.metrics[category][name] = 0
                self.metrics_history[category][name] = deque(maxlen=self.max_points)
            self.metrics[category][name] = value
            timestamp = datetime.now().isoformat()
            self.metrics_history[category][name].append((timestamp, value))
            self._store_metric(category, name, value, timestamp, tags)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error updating metric {category}.{name}: {e}")
    def _store_metric(self, category, name, value, timestamp, tags=None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            tags_json = json.dumps(tags) if tags else None
            cursor.execute(
                'INSERT INTO metrics (category, name, value, timestamp, tags) VALUES (?, ?, ?, ?, ?)',
                (category, name, value, timestamp, tags_json)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error storing metric {category}.{name} in database: {e}")
    def _store_metrics(self):
        try:
            timestamp = datetime.now().isoformat()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for category, metrics in self.metrics.items():
                for name, value in metrics.items():
                    cursor.execute(
                        'INSERT INTO metrics (category, name, value, timestamp, tags) VALUES (?, ?, ?, ?, ?)',
                        (category, name, value, timestamp, None)
                    )
            conn.commit()
            conn.close()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error storing metrics in database: {e}")
    def _cleanup_old_metrics(self):
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_period)
            cutoff_timestamp = cutoff_date.isoformat()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM metrics WHERE timestamp < ?', (cutoff_timestamp,))
            conn.commit()
            conn.close()
            if self.logger and cursor.rowcount > 0:
                self.logger.debug(f"Cleaned up {cursor.rowcount} old metrics")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error cleaning up old metrics: {e}")
    def get_metrics(self, category=None):
        if category:
            return self.metrics.get(category, {})
        else:
            return self.metrics
    def get_metric_history(self, category, name, limit=100):
        try:
            if category in self.metrics_history and name in self.metrics_history[category]:
                history = list(self.metrics_history[category][name])
                return history[-limit:] if limit else history
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT timestamp, value FROM metrics WHERE category = ? AND name = ? ORDER BY timestamp DESC LIMIT ?',
                (category, name, limit)
            )
            results = cursor.fetchall()
            conn.close()
            return list(reversed(results))
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting metric history for {category}.{name}: {e}")
            return []
    def get_metrics_by_timerange(self, category, name, start_time, end_time):
        try:
            start_timestamp = start_time.isoformat()
            end_timestamp = end_time.isoformat()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT timestamp, value FROM metrics WHERE category = ? AND name = ? AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp',
                (category, name, start_timestamp, end_timestamp)
            )
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting metrics by time range for {category}.{name}: {e}")
            return []
    def get_metric_statistics(self, category, name, period='1d'):
        try:
            now = datetime.now()
            if period == '1h':
                start_time = now - timedelta(hours=1)
            elif period == '1d':
                start_time = now - timedelta(days=1)
            elif period == '7d':
                start_time = now - timedelta(days=7)
            elif period == '30d':
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(days=1)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT MIN(value), MAX(value), AVG(value), COUNT(value) FROM metrics WHERE category = ? AND name = ? AND timestamp >= ?',
                (category, name, start_time.isoformat())
            )
            min_val, max_val, avg_val, count = cursor.fetchone()
            conn.close()
            return {
                'min': min_val,
                'max': max_val,
                'avg': avg_val,
                'count': count,
                'period': period
            }
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting metric statistics for {category}.{name}: {e}")
            return {
                'min': 0,
                'max': 0,
                'avg': 0,
                'count': 0,
                'period': period
            }
    def export_metrics(self, file_path=None, format='json'):
        if file_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'data',
                f'metrics_export_{timestamp}.{format}'
            )
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT category, name, value, timestamp, tags FROM metrics ORDER BY timestamp')
            results = cursor.fetchall()
            conn.close()
            if format == 'json':
                metrics_data = [
                    {
                        'category': category,
                        'name': name,
                        'value': value,
                        'timestamp': timestamp,
                        'tags': json.loads(tags) if tags else None
                    }
                    for category, name, value, timestamp, tags in results
                ]
                with open(file_path, 'w') as f:
                    json.dump(metrics_data, f, indent=4)
            elif format == 'csv':
                import csv
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['category', 'name', 'value', 'timestamp', 'tags'])
                    for row in results:
                        writer.writerow(row)
            else:
                if self.logger:
                    self.logger.error(f"Unsupported export format: {format}")
                return None
            if self.logger:
                self.logger.info(f"Metrics exported to {file_path}")
            return file_path
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error exporting metrics: {e}")
            return None
