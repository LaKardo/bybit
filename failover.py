import os
import time
import json
import threading
import traceback
from datetime import datetime, timedelta
from enum import Enum
import config


# Constants
STRATEGY_SIGNAL_TIMEOUT_SECONDS = 3600  # 1 hour


class FailoverState(Enum):
    NORMAL = 0
    DEGRADED = 1
    FAILOVER = 2
    RECOVERY = 3
    EMERGENCY = 4


class ComponentStatus(Enum):
    HEALTHY = 0
    WARNING = 1
    CRITICAL = 2
    FAILED = 3
    RECOVERING = 4


class FailoverManager:
    def __init__(self, bot=None, logger=None):
        self.bot = bot
        self.logger = logger
        self.state = FailoverState.NORMAL
        self.components = {}
        self.recovery_attempts = {}
        self.last_recovery_time = {}
        self.max_recovery_attempts = getattr(config, 'MAX_RECOVERY_ATTEMPTS', 3)
        self.recovery_backoff = getattr(config, 'RECOVERY_BACKOFF', 60)
        self.check_interval = getattr(config, 'FAILOVER_CHECK_INTERVAL', 30)
        self.failover_config = {
            'enabled': getattr(config, 'FAILOVER_ENABLED', True),
            'auto_recovery': getattr(config, 'AUTO_RECOVERY_ENABLED', True),
            'max_recovery_attempts': getattr(config, 'MAX_RECOVERY_ATTEMPTS', 3),
            'recovery_backoff': getattr(config, 'RECOVERY_BACKOFF', 60),
            'emergency_shutdown': getattr(config, 'EMERGENCY_SHUTDOWN', True),
            'notification_enabled': getattr(config, 'FAILOVER_NOTIFICATION_ENABLED', True)
        }
        self._initialize_components()
        self.running = False
        self.failover_thread = None
        if self.logger:
            self.logger.info("Failover manager initialized")

    def _initialize_components(self):
        self.components = {
            'api_client': {
                'status': ComponentStatus.HEALTHY,
                'critical': True,
                'recovery_function': self._recover_api_client,
                'check_function': self._check_api_client,
                'last_check': None,
                'last_failure': None,
                'failure_count': 0
            },
            'websocket': {
                'status': ComponentStatus.HEALTHY,
                'critical': False,
                'recovery_function': self._recover_websocket,
                'check_function': self._check_websocket,
                'last_check': None,
                'last_failure': None,
                'failure_count': 0
            },
            'database': {
                'status': ComponentStatus.HEALTHY,
                'critical': False,
                'recovery_function': self._recover_database,
                'check_function': self._check_database,
                'last_check': None,
                'last_failure': None,
                'failure_count': 0
            },
            'strategy': {
                'status': ComponentStatus.HEALTHY,
                'critical': True,
                'recovery_function': self._recover_strategy,
                'check_function': self._check_strategy,
                'last_check': None,
                'last_failure': None,
                'failure_count': 0
            },
            'order_manager': {
                'status': ComponentStatus.HEALTHY,
                'critical': True,
                'recovery_function': self._recover_order_manager,
                'check_function': self._check_order_manager,
                'last_check': None,
                'last_failure': None,
                'failure_count': 0
            }
        }
        for component in self.components:
            self.recovery_attempts[component] = 0
            self.last_recovery_time[component] = 0

    def start(self):
        if not self.failover_config['enabled']:
            if self.logger:
                self.logger.info("Failover manager is disabled in configuration")
            return
        if self.running:
            if self.logger:
                self.logger.warning("Failover manager already running")
            return
        self.running = True
        self.failover_thread = threading.Thread(target=self._failover_loop, daemon=True)
        self.failover_thread.start()
        if self.logger:
            self.logger.info("Failover manager started")

    def stop(self):
        if not self.running:
            if self.logger:
                self.logger.warning("Failover manager not running")
            return
        self.running = False
        if self.failover_thread:
            # Define a constant for the join timeout if it's used elsewhere or needs clarity
            # THREAD_JOIN_TIMEOUT = 1.0 
            self.failover_thread.join(timeout=1.0) # Using 1.0 directly as it's a simple, common timeout value
            self.failover_thread = None
        if self.logger:
            self.logger.info("Failover manager stopped")

    def _failover_loop(self):
        while self.running:
            try:
                self._check_components()
                self._update_state()
                self._handle_failover()
                time.sleep(self.check_interval)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in failover loop: {e}")
                    self.logger.error(traceback.format_exc())
                time.sleep(self.check_interval)

    def _check_components(self):
        for component_name, component in self.components.items():
            try:
                if not component['check_function']:
                    continue
                status = component['check_function']()
                component['status'] = status
                component['last_check'] = datetime.now()
                if status == ComponentStatus.HEALTHY:
                    component['failure_count'] = 0
                    component['last_failure'] = None
                else:
                    component['failure_count'] += 1
                    if component['last_failure'] is None:
                        component['last_failure'] = datetime.now()
                if self.logger:
                    self.logger.debug(f"Component {component_name} status: {status.name}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error checking component {component_name}: {e}")
                    self.logger.error(traceback.format_exc())
                component['status'] = ComponentStatus.FAILED
                component['failure_count'] += 1
                if component['last_failure'] is None:
                    component['last_failure'] = datetime.now()

    def _update_state(self):
        critical_failures = any(
            component['status'] in [ComponentStatus.CRITICAL, ComponentStatus.FAILED] and component['critical']
            for component in self.components.values()
        )
        warnings = any(
            component['status'] == ComponentStatus.WARNING
            for component in self.components.values()
        )
        recovering = any(
            component['status'] == ComponentStatus.RECOVERING
            for component in self.components.values()
        )
        if critical_failures:
            new_state = FailoverState.EMERGENCY
        elif recovering:
            new_state = FailoverState.RECOVERY
        elif warnings:
            new_state = FailoverState.DEGRADED
        else:
            new_state = FailoverState.NORMAL
        if new_state != self.state:
            if self.logger:
                self.logger.info(f"Failover state changed from {self.state.name} to {new_state.name}")
            if self.failover_config['notification_enabled']:
                self._send_notification(f"Failover state changed from {self.state.name} to {new_state.name}")
        self.state = new_state

    def _handle_failover(self):
        if self.state == FailoverState.NORMAL:
            return
        if self.state == FailoverState.DEGRADED:
            self._handle_degraded()
        elif self.state == FailoverState.FAILOVER:
            self._handle_failover_state()
        elif self.state == FailoverState.RECOVERY:
            self._handle_recovery()
        elif self.state == FailoverState.EMERGENCY:
            self._handle_emergency()

    def _handle_degraded(self):
        for component_name, component in self.components.items():
            if component['status'] == ComponentStatus.WARNING:
                self._attempt_recovery(component_name)

    def _handle_failover_state(self):
        for component_name, component in self.components.items():
            if component['critical'] and component['status'] in [ComponentStatus.CRITICAL, ComponentStatus.FAILED]:
                self._use_backup_system(component_name)

    def _handle_recovery(self):
        for component_name, component in self.components.items():
            if component['status'] == ComponentStatus.RECOVERING:
                self._continue_recovery(component_name)

    def _handle_emergency(self):
        if self.logger:
            self.logger.critical("System in EMERGENCY state - critical components have failed")
        critical_components = [
            component_name for component_name, component in self.components.items()
            if component['critical'] and component['status'] in [ComponentStatus.CRITICAL, ComponentStatus.FAILED]
        ]
        for component_name in critical_components:
            self._attempt_recovery(component_name)
        if self.failover_config['emergency_shutdown'] and all(
            self.recovery_attempts[component_name] >= self.failover_config['max_recovery_attempts']
            for component_name in critical_components
        ):
            if self.logger:
                self.logger.critical("Emergency shutdown initiated - critical components could not be recovered")
            if self.failover_config['notification_enabled']:
                self._send_notification("EMERGENCY: Trading bot shutting down due to critical component failures")
            if self.bot and hasattr(self.bot, 'shutdown'):
                self.bot.shutdown()

    def _attempt_recovery(self, component_name):
        component = self.components.get(component_name)
        if not component:
            return False
        if not self.failover_config['auto_recovery']:
            if self.logger:
                self.logger.warning(f"Auto recovery disabled - not attempting recovery for {component_name}")
            return False
        if not component['recovery_function']:
            if self.logger:
                self.logger.warning(f"No recovery function for component {component_name}")
            return False
        if self.recovery_attempts[component_name] >= self.failover_config['max_recovery_attempts']:
            if self.logger:
                self.logger.warning(f"Max recovery attempts reached for component {component_name}")
            return False
        current_time = time.time()
        if current_time - self.last_recovery_time[component_name] < self.failover_config['recovery_backoff']:
            if self.logger:
                self.logger.debug(f"Recovery backoff time not elapsed for component {component_name}")
            return False
        try:
            if self.logger:
                self.logger.info(f"Attempting recovery for component {component_name} (attempt {self.recovery_attempts[component_name] + 1})")
            component['status'] = ComponentStatus.RECOVERING
            success = component['recovery_function']()
            self.recovery_attempts[component_name] += 1
            self.last_recovery_time[component_name] = current_time
            if success:
                if self.logger:
                    self.logger.info(f"Recovery successful for component {component_name}")
                self.recovery_attempts[component_name] = 0
                component['status'] = ComponentStatus.HEALTHY
                component['failure_count'] = 0
                component['last_failure'] = None
            else:
                if self.logger:
                    self.logger.warning(f"Recovery failed for component {component_name}")
                component['status'] = ComponentStatus.FAILED
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during recovery for component {component_name}: {e}")
                self.logger.error(traceback.format_exc())
            self.recovery_attempts[component_name] += 1
            self.last_recovery_time[component_name] = current_time
            component['status'] = ComponentStatus.FAILED
            return False

    def _continue_recovery(self, component_name):
        component = self.components.get(component_name)
        if not component or component['status'] != ComponentStatus.RECOVERING:
            return
        status = component['check_function']() if component['check_function'] else ComponentStatus.FAILED
        if status == ComponentStatus.HEALTHY:
            if self.logger:
                self.logger.info(f"Component {component_name} has recovered")
            self.recovery_attempts[component_name] = 0
            component['status'] = ComponentStatus.HEALTHY
            component['failure_count'] = 0
            component['last_failure'] = None
        else:
            self._attempt_recovery(component_name)

    def _use_backup_system(self, component_name):
        if self.logger:
            self.logger.info(f"Using backup system for component {component_name}")
        if component_name == 'api_client' and self.bot and hasattr(self.bot, 'bybit_client'):
            pass

    def _send_notification(self, message):
        if self.logger:
            self.logger.info(f"Notification: {message}")
        if hasattr(self.bot, 'telegram_notifier') and self.bot.telegram_notifier:
            try:
                self.bot.telegram_notifier.send_message(message)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error sending Telegram notification: {e}")

    def _check_api_client(self):
        if not self.bot or not hasattr(self.bot, 'bybit_client') or not self.bot.bybit_client:
            return ComponentStatus.FAILED
        try:
            if not self.bot.bybit_client:
                return ComponentStatus.FAILED
            server_time = self.bot.bybit_client.get_server_time()
            if server_time is None:
                return ComponentStatus.CRITICAL
            if hasattr(self.bot.bybit_client, 'circuit_breaker_registry') and self.bot.bybit_client.circuit_breaker_registry:
                circuit_breaker_states = self.bot.bybit_client.circuit_breaker_registry.get_all_states()
                if any(state == 'OPEN' for state in circuit_breaker_states.values()):
                    return ComponentStatus.WARNING
            return ComponentStatus.HEALTHY
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking API client: {e}")
            return ComponentStatus.FAILED

    def _check_websocket(self):
        if not self.bot or not hasattr(self.bot, 'bybit_client') or not self.bot.bybit_client:
            return ComponentStatus.FAILED
        try:
            if not getattr(self.bot.bybit_client, 'ws_enabled', False):
                return ComponentStatus.HEALTHY
            if not hasattr(self.bot.bybit_client, 'check_websocket_health'):
                return ComponentStatus.WARNING
            ws_healthy = self.bot.bybit_client.check_websocket_health()
            if not ws_healthy:
                return ComponentStatus.CRITICAL
            if hasattr(self.bot.bybit_client, 'ws_last_message_time'):
                last_message_time = self.bot.bybit_client.ws_last_message_time
                if last_message_time and (datetime.now() - last_message_time).total_seconds() > 60:
                    return ComponentStatus.WARNING
            return ComponentStatus.HEALTHY
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking WebSocket: {e}")
            return ComponentStatus.FAILED

    def _check_database(self):
        # TODO: Implement actual database health check logic
        return ComponentStatus.HEALTHY

    def _check_strategy(self):
        if not self.bot or not hasattr(self.bot, 'strategy') or not self.bot.strategy:
            return ComponentStatus.FAILED
        try:
            if not self.bot.strategy:
                return ComponentStatus.FAILED
            if hasattr(self.bot.strategy, 'last_signal_time'):
                last_signal_time = self.bot.strategy.last_signal_time
                if last_signal_time and (datetime.now() - last_signal_time).total_seconds() > STRATEGY_SIGNAL_TIMEOUT_SECONDS:
                    return ComponentStatus.WARNING
            return ComponentStatus.HEALTHY
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking strategy: {e}")
            return ComponentStatus.FAILED

    def _check_order_manager(self):
        if not self.bot or not hasattr(self.bot, 'order_manager') or not self.bot.order_manager:
            return ComponentStatus.FAILED
        try:
            if not self.bot.order_manager:
                return ComponentStatus.FAILED
            if hasattr(self.bot.order_manager, 'can_place_orders'):
                can_place_orders = self.bot.order_manager.can_place_orders()
                if not can_place_orders:
                    return ComponentStatus.CRITICAL
            return ComponentStatus.HEALTHY
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking order manager: {e}")
            return ComponentStatus.FAILED

    def _recover_api_client(self):
        if not self.bot or not hasattr(self.bot, 'bybit_client'):
            return False
        try:
            if hasattr(self.bot, 'initialize_api_client'):
                self.bot.initialize_api_client()
                server_time = self.bot.bybit_client.get_server_time()
                if server_time is None:
                    return False
                return True
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error recovering API client: {e}")
            return False

    def _recover_websocket(self):
        if not self.bot or not hasattr(self.bot, 'bybit_client'):
            return False
        try:
            if hasattr(self.bot.bybit_client, 'restart_websocket'):
                self.bot.bybit_client.restart_websocket()
                time.sleep(5)
                if hasattr(self.bot.bybit_client, 'check_websocket_health'):
                    ws_healthy = self.bot.bybit_client.check_websocket_health()
                    return ws_healthy
                return True
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error recovering WebSocket: {e}")
            return False

    def _recover_database(self):
        return True

    def _recover_strategy(self):
        if not self.bot or not hasattr(self.bot, 'strategy'):
            return False
        try:
            if hasattr(self.bot, 'initialize_strategy'):
                self.bot.initialize_strategy()
                return True
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error recovering strategy: {e}")
            return False

    def _recover_order_manager(self):
        if not self.bot or not hasattr(self.bot, 'order_manager'):
            return False
        try:
            if hasattr(self.bot, 'initialize_order_manager'):
                self.bot.initialize_order_manager()
                return True
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error recovering order manager: {e}")
            return False

    def get_failover_status(self):
        return {
            'state': self.state.name,
            'components': {
                component_name: {
                    'status': component['status'].name,
                    'critical': component['critical'],
                    'failure_count': component['failure_count'],
                    'last_check': component['last_check'].isoformat() if component['last_check'] else None,
                    'last_failure': component['last_failure'].isoformat() if component['last_failure'] else None
                }
                for component_name, component in self.components.items()
            },
            'recovery_attempts': self.recovery_attempts,
            'config': self.failover_config
        }

    def get_component_status(self, component_name):
        component = self.components.get(component_name)
        if not component:
            return None
        return {
            'status': component['status'].name,
            'critical': component['critical'],
            'failure_count': component['failure_count'],
            'last_check': component['last_check'].isoformat() if component['last_check'] else None,
            'last_failure': component['last_failure'].isoformat() if component['last_failure'] else None,
            'recovery_attempts': self.recovery_attempts.get(component_name, 0)
        }

    def reset_component(self, component_name):
        component = self.components.get(component_name)
        if not component:
            return False
        try:
            component['status'] = ComponentStatus.HEALTHY
            component['failure_count'] = 0
            component['last_failure'] = None
            self.recovery_attempts[component_name] = 0
            if self.logger:
                self.logger.info(f"Component {component_name} reset")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error resetting component {component_name}: {e}")
            return False

    def update_failover_config(self, config):
        try:
            for key, value in config.items():
                if key in self.failover_config:
                    self.failover_config[key] = value
            self.max_recovery_attempts = self.failover_config['max_recovery_attempts']
            self.recovery_backoff = self.failover_config['recovery_backoff']
            if self.logger:
                self.logger.info(f"Failover configuration updated: {self.failover_config}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error updating failover configuration: {e}")
            return False
