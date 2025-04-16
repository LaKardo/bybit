import time
import threading
import logging
import psutil
import os
import json
from datetime import datetime, timedelta
from collections import deque


class HealthCheck:
    def __init__(self, logger=None, check_interval=60, history_size=100):
        self.logger = logger
        self.check_interval = check_interval
        self.history_size = history_size
        self.history = deque(maxlen=history_size)
        self.start_time = datetime.now()
        self.last_check_time = None
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()
        # Load thresholds from config or use defaults
        self.cpu_threshold = getattr(config, 'HEALTH_CPU_THRESHOLD', 80)
        self.memory_threshold = getattr(config, 'HEALTH_MEMORY_THRESHOLD', 80)
        self.disk_threshold = getattr(config, 'HEALTH_DISK_THRESHOLD', 90)
        self.response_time_threshold = getattr(config, 'HEALTH_API_RESPONSE_THRESHOLD_MS', 5000)
        self.components = {
            "api_client": {"status": "unknown", "last_success": None, "failures": 0},
            "websocket": {"status": "unknown", "last_success": None, "failures": 0},
            "strategy": {"status": "unknown", "last_success": None, "failures": 0},
            "order_manager": {"status": "unknown", "last_success": None, "failures": 0},
            "risk_manager": {"status": "unknown", "last_success": None, "failures": 0},
            "web_interface": {"status": "unknown", "last_success": None, "failures": 0}
        }
        self.trading_metrics = {
            "trades_total": 0,
            "trades_successful": 0,
            "trades_failed": 0,
            "profit_loss": 0.0,
            "win_rate": 0.0,
            "avg_profit": 0.0,
            "avg_loss": 0.0,
            "largest_profit": 0.0,
            "largest_loss": 0.0
        }
        self.api_metrics = {
            "calls_total": 0,
            "calls_successful": 0,
            "calls_failed": 0,
            "avg_response_time": 0.0,
            "max_response_time": 0.0
        }
        self.health_dir = "health_checks"
        if not os.path.exists(self.health_dir):
            os.makedirs(self.health_dir)
        if self.logger:
            self.logger.info("Health check system initialized")

    def start(self):
        if self.is_running:
            if self.logger:
                self.logger.warning("Health check system already running")
            return False
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        if self.logger:
            self.logger.info("Health check system started")
        return True

    def stop(self):
        if not self.is_running:
            if self.logger:
                self.logger.warning("Health check system not running")
            return False
        self.is_running = False
        if self.thread:
            # Define a constant for the join timeout
            HEALTH_CHECK_THREAD_JOIN_TIMEOUT = 5
            self.thread.join(timeout=HEALTH_CHECK_THREAD_JOIN_TIMEOUT)
            self.thread = None
        if self.logger:
            self.logger.info("Health check system stopped")
        return True

    def _run(self):
        while self.is_running:
            try:
                self.check_health()
                time.sleep(self.check_interval)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in health check: {e}")
                time.sleep(self.check_interval)

    def check_health(self):
        current_time = datetime.now()
        self.last_check_time = current_time
        system_metrics = self._get_system_metrics()
        health_record = {
            "timestamp": current_time.isoformat(),
            "uptime_seconds": (current_time - self.start_time).total_seconds(),
            "system": system_metrics,
            "components": self.components.copy(),
            "trading": self.trading_metrics.copy(),
            "api": self.api_metrics.copy()
        }
        with self.lock:
            self.history.append(health_record)
        self._save_health_record(health_record)
        self._check_for_issues(health_record)
        return health_record

    def _get_system_metrics(self):
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            process = psutil.Process(os.getpid())
            process_cpu = process.cpu_percent(interval=1)
            # Define constant for byte conversion
            BYTES_PER_MEGABYTE = 1024 * 1024
            process_memory = process.memory_info().rss / BYTES_PER_MEGABYTE
            net_io = psutil.net_io_counters()
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "process_cpu_percent": process_cpu,
                "process_memory_mb": process_memory,
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting system metrics: {e}")
            return {
                "error": str(e)
            }

    def _save_health_record(self, health_record):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.health_dir}/health_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(health_record, f, indent=2)
            self._cleanup_old_files()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error saving health record: {e}")

    def _cleanup_old_files(self):
        try:
            files = [os.path.join(self.health_dir, f) for f in os.listdir(self.health_dir)
                    if f.startswith("health_") and f.endswith(".json")]
            files.sort(key=lambda x: os.path.getmtime(x))
            # Define a constant for the multiplier
            HEALTH_HISTORY_FILE_MULTIPLIER = 2
            max_files = self.history_size * HEALTH_HISTORY_FILE_MULTIPLIER
            if len(files) > max_files:
                for file in files[:len(files) - max_files]:
                    os.remove(file)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error cleaning up old health check files: {e}")

    def _check_for_issues(self, health_record):
        issues = []
        system = health_record["system"]
        if "error" in system:
            issues.append(f"Error getting system metrics: {system['error']}")
        else:
            if system["cpu_percent"] > self.cpu_threshold:
                issues.append(f"High CPU usage: {system['cpu_percent']}%")
            if system["memory_percent"] > self.memory_threshold:
                issues.append(f"High memory usage: {system['memory_percent']}%")
            if system["disk_percent"] > self.disk_threshold:
                issues.append(f"High disk usage: {system['disk_percent']}%")
        for component, status in health_record["components"].items():
            if status["status"] == "error":
                issues.append(f"Component {component} is in error state")
        api = health_record["api"]
        if api["avg_response_time"] > self.response_time_threshold:
            issues.append(f"High API response time: {api['avg_response_time']} ms")
        if issues and self.logger:
            for issue in issues:
                self.logger.warning(f"Health check issue: {issue}")
        return issues

    def update_component_status(self, component, status, details=None):
        if component not in self.components:
            if self.logger:
                self.logger.warning(f"Unknown component: {component}")
            return
        with self.lock:
            self.components[component]["status"] = status
            if status == "ok":
                self.components[component]["last_success"] = datetime.now().isoformat()
                self.components[component]["failures"] = 0
            elif status == "error":
                self.components[component]["failures"] += 1
            if details:
                self.components[component].update(details)

    def update_trading_metrics(self, metrics):
        with self.lock:
            self.trading_metrics.update(metrics)

    def update_api_metrics(self, success=True, response_time=None):
        with self.lock:
            self.api_metrics["calls_total"] += 1
            if success:
                self.api_metrics["calls_successful"] += 1
            else:
                self.api_metrics["calls_failed"] += 1
            if response_time is not None:
                current_avg = self.api_metrics["avg_response_time"]
                current_total = self.api_metrics["calls_total"]
                if current_total > 1:
                    new_avg = ((current_avg * (current_total - 1)) + response_time) / current_total
                    self.api_metrics["avg_response_time"] = new_avg
                else:
                    self.api_metrics["avg_response_time"] = response_time
                if response_time > self.api_metrics["max_response_time"]:
                    self.api_metrics["max_response_time"] = response_time

    def get_health_summary(self):
        with self.lock:
            if not self.history:
                return {
                    "status": "unknown",
                    "uptime": str(datetime.now() - self.start_time),
                    "last_check": None,
                    "components": self.components.copy(),
                    "issues": []
                }
            latest = self.history[-1]
            issues = self._check_for_issues(latest)
            if any(component["status"] == "error" for component in self.components.values()):
                status = "error"
            elif any(component["status"] == "warning" for component in self.components.values()):
                status = "warning"
            elif all(component["status"] == "ok" for component in self.components.values()):
                status = "ok"
            else:
                status = "unknown"
            return {
                "status": status,
                "uptime": str(datetime.now() - self.start_time),
                "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
                "components": self.components.copy(),
                "issues": issues
            }

    def get_health_history(self, hours=24):
        with self.lock:
            if not self.history:
                return []
            cutoff_time = datetime.now() - timedelta(hours=hours)
            return [record for record in self.history
                   if datetime.fromisoformat(record["timestamp"]) >= cutoff_time]

    def get_performance_metrics(self):
        with self.lock:
            if not self.history:
                return {
                    "cpu_avg": 0,
                    "memory_avg": 0,
                    "api_response_time_avg": 0,
                    "api_success_rate": 0
                }
            cpu_values = [record["system"].get("cpu_percent", 0) for record in self.history
                         if "system" in record and "cpu_percent" in record["system"]]
            memory_values = [record["system"].get("memory_percent", 0) for record in self.history
                            if "system" in record and "memory_percent" in record["system"]]
            api_calls_total = self.api_metrics["calls_total"]
            api_success_rate = 0
            if api_calls_total > 0:
                api_success_rate = (self.api_metrics["calls_successful"] / api_calls_total) * 100
            return {
                "cpu_avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                "memory_avg": sum(memory_values) / len(memory_values) if memory_values else 0,
                "api_response_time_avg": self.api_metrics["avg_response_time"],
                "api_success_rate": api_success_rate
            }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger()
    health_check = HealthCheck(logger=logger, check_interval=5)
    health_check.start()
    health_check.update_component_status("api_client", "ok")
    health_check.update_component_status("websocket", "ok")
    health_check.update_component_status("strategy", "ok")
    health_check.update_api_metrics(success=True, response_time=150)
    health_check.update_api_metrics(success=True, response_time=200)
    health_check.update_api_metrics(success=False, response_time=500)
    health_check.update_trading_metrics({
        "trades_total": 10,
        "trades_successful": 7,
        "trades_failed": 3,
        "profit_loss": 120.5,
        "win_rate": 70.0
    })
    time.sleep(15)
    summary = health_check.get_health_summary()
    print("Health Summary:")
    print(json.dumps(summary, indent=2))
    metrics = health_check.get_performance_metrics()
    print("\nPerformance Metrics:")
    print(json.dumps(metrics, indent=2))
    health_check.stop()
