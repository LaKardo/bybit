#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Health check system for monitoring the trading bot's performance and status.
"""

import time
import threading
import logging
import psutil
import os
import json
from datetime import datetime, timedelta
from collections import deque

class HealthCheck:
    """Health check system for monitoring the trading bot."""

    def __init__(self, logger=None, check_interval=60, history_size=100):
        """
        Initialize the health check system.

        Args:
            logger (Logger, optional): Logger instance.
            check_interval (int, optional): Interval between health checks in seconds.
            history_size (int, optional): Number of health check records to keep.
        """
        self.logger = logger
        self.check_interval = check_interval
        self.history_size = history_size
        self.history = deque(maxlen=history_size)
        self.start_time = datetime.now()
        self.last_check_time = None
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()
        
        # Performance thresholds
        self.cpu_threshold = 80  # CPU usage percentage
        self.memory_threshold = 80  # Memory usage percentage
        self.disk_threshold = 90  # Disk usage percentage
        self.response_time_threshold = 5000  # API response time in ms
        
        # Component status
        self.components = {
            "api_client": {"status": "unknown", "last_success": None, "failures": 0},
            "websocket": {"status": "unknown", "last_success": None, "failures": 0},
            "strategy": {"status": "unknown", "last_success": None, "failures": 0},
            "order_manager": {"status": "unknown", "last_success": None, "failures": 0},
            "risk_manager": {"status": "unknown", "last_success": None, "failures": 0},
            "web_interface": {"status": "unknown", "last_success": None, "failures": 0}
        }
        
        # Trading metrics
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
        
        # API metrics
        self.api_metrics = {
            "calls_total": 0,
            "calls_successful": 0,
            "calls_failed": 0,
            "avg_response_time": 0.0,
            "max_response_time": 0.0
        }
        
        # Create health check directory if it doesn't exist
        self.health_dir = "health_checks"
        if not os.path.exists(self.health_dir):
            os.makedirs(self.health_dir)
            
        if self.logger:
            self.logger.info("Health check system initialized")

    def start(self):
        """Start the health check system."""
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
        """Stop the health check system."""
        if not self.is_running:
            if self.logger:
                self.logger.warning("Health check system not running")
            return False
            
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None
            
        if self.logger:
            self.logger.info("Health check system stopped")
            
        return True

    def _run(self):
        """Run the health check loop."""
        while self.is_running:
            try:
                self.check_health()
                time.sleep(self.check_interval)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in health check: {e}")
                time.sleep(self.check_interval)

    def check_health(self):
        """
        Perform a health check and record the results.
        
        Returns:
            dict: Health check results.
        """
        current_time = datetime.now()
        self.last_check_time = current_time
        
        # System metrics
        system_metrics = self._get_system_metrics()
        
        # Create health check record
        health_record = {
            "timestamp": current_time.isoformat(),
            "uptime_seconds": (current_time - self.start_time).total_seconds(),
            "system": system_metrics,
            "components": self.components.copy(),
            "trading": self.trading_metrics.copy(),
            "api": self.api_metrics.copy()
        }
        
        # Add to history
        with self.lock:
            self.history.append(health_record)
            
        # Save to file
        self._save_health_record(health_record)
        
        # Check for issues
        self._check_for_issues(health_record)
        
        return health_record

    def _get_system_metrics(self):
        """
        Get system metrics.
        
        Returns:
            dict: System metrics.
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Process info
            process = psutil.Process(os.getpid())
            process_cpu = process.cpu_percent(interval=1)
            process_memory = process.memory_info().rss / (1024 * 1024)  # MB
            
            # Network info
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
        """
        Save health record to file.
        
        Args:
            health_record (dict): Health check record.
        """
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.health_dir}/health_{timestamp}.json"
            
            # Save to file
            with open(filename, 'w') as f:
                json.dump(health_record, f, indent=2)
                
            # Clean up old files if there are too many
            self._cleanup_old_files()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error saving health record: {e}")

    def _cleanup_old_files(self):
        """Clean up old health check files."""
        try:
            files = [os.path.join(self.health_dir, f) for f in os.listdir(self.health_dir) 
                    if f.startswith("health_") and f.endswith(".json")]
            
            # Sort by modification time (oldest first)
            files.sort(key=lambda x: os.path.getmtime(x))
            
            # Remove oldest files if there are too many
            max_files = self.history_size * 2  # Keep twice as many files as history size
            if len(files) > max_files:
                for file in files[:len(files) - max_files]:
                    os.remove(file)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error cleaning up old health check files: {e}")

    def _check_for_issues(self, health_record):
        """
        Check for issues in the health record.
        
        Args:
            health_record (dict): Health check record.
        """
        issues = []
        
        # Check system metrics
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
                
        # Check component status
        for component, status in health_record["components"].items():
            if status["status"] == "error":
                issues.append(f"Component {component} is in error state")
                
        # Check API metrics
        api = health_record["api"]
        if api["avg_response_time"] > self.response_time_threshold:
            issues.append(f"High API response time: {api['avg_response_time']} ms")
            
        # Log issues
        if issues and self.logger:
            for issue in issues:
                self.logger.warning(f"Health check issue: {issue}")
                
        return issues

    def update_component_status(self, component, status, details=None):
        """
        Update the status of a component.
        
        Args:
            component (str): Component name.
            status (str): Status ('ok', 'warning', 'error', 'unknown').
            details (dict, optional): Additional details.
        """
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
        """
        Update trading metrics.
        
        Args:
            metrics (dict): Trading metrics to update.
        """
        with self.lock:
            self.trading_metrics.update(metrics)

    def update_api_metrics(self, success=True, response_time=None):
        """
        Update API metrics.
        
        Args:
            success (bool): Whether the API call was successful.
            response_time (float, optional): API response time in milliseconds.
        """
        with self.lock:
            self.api_metrics["calls_total"] += 1
            
            if success:
                self.api_metrics["calls_successful"] += 1
            else:
                self.api_metrics["calls_failed"] += 1
                
            if response_time is not None:
                # Update average response time
                current_avg = self.api_metrics["avg_response_time"]
                current_total = self.api_metrics["calls_total"]
                
                if current_total > 1:
                    new_avg = ((current_avg * (current_total - 1)) + response_time) / current_total
                    self.api_metrics["avg_response_time"] = new_avg
                else:
                    self.api_metrics["avg_response_time"] = response_time
                    
                # Update max response time
                if response_time > self.api_metrics["max_response_time"]:
                    self.api_metrics["max_response_time"] = response_time

    def get_health_summary(self):
        """
        Get a summary of the current health status.
        
        Returns:
            dict: Health summary.
        """
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
            
            # Determine overall status
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
        """
        Get health check history for the specified time period.
        
        Args:
            hours (int): Number of hours of history to retrieve.
            
        Returns:
            list: Health check history.
        """
        with self.lock:
            if not self.history:
                return []
                
            cutoff_time = datetime.now() - timedelta(hours=hours)
            return [record for record in self.history 
                   if datetime.fromisoformat(record["timestamp"]) >= cutoff_time]

    def get_performance_metrics(self):
        """
        Get performance metrics.
        
        Returns:
            dict: Performance metrics.
        """
        with self.lock:
            if not self.history:
                return {
                    "cpu_avg": 0,
                    "memory_avg": 0,
                    "api_response_time_avg": 0,
                    "api_success_rate": 0
                }
                
            # Calculate averages from history
            cpu_values = [record["system"].get("cpu_percent", 0) for record in self.history 
                         if "system" in record and "cpu_percent" in record["system"]]
            
            memory_values = [record["system"].get("memory_percent", 0) for record in self.history 
                            if "system" in record and "memory_percent" in record["system"]]
            
            # Calculate API success rate
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

# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger()
    
    # Create health check system
    health_check = HealthCheck(logger=logger, check_interval=5)
    
    # Start health check system
    health_check.start()
    
    # Update component status
    health_check.update_component_status("api_client", "ok")
    health_check.update_component_status("websocket", "ok")
    health_check.update_component_status("strategy", "ok")
    
    # Update API metrics
    health_check.update_api_metrics(success=True, response_time=150)
    health_check.update_api_metrics(success=True, response_time=200)
    health_check.update_api_metrics(success=False, response_time=500)
    
    # Update trading metrics
    health_check.update_trading_metrics({
        "trades_total": 10,
        "trades_successful": 7,
        "trades_failed": 3,
        "profit_loss": 120.5,
        "win_rate": 70.0
    })
    
    # Wait for a few health checks
    time.sleep(15)
    
    # Get health summary
    summary = health_check.get_health_summary()
    print("Health Summary:")
    print(json.dumps(summary, indent=2))
    
    # Get performance metrics
    metrics = health_check.get_performance_metrics()
    print("\nPerformance Metrics:")
    print(json.dumps(metrics, indent=2))
    
    # Stop health check system
    health_check.stop()
