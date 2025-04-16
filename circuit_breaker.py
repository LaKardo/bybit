import time
import threading
import enum
from collections import defaultdict


class CircuitState(enum.Enum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2


class CircuitBreaker:
    def __init__(self, name, error_threshold=5, error_timeout=60, circuit_timeout=300, logger=None):
        self.name = name
        self.error_threshold = error_threshold
        self.error_timeout = error_timeout
        self.circuit_timeout = circuit_timeout
        self.logger = logger
        self.state = CircuitState.CLOSED
        self.error_count = 0
        self.last_error_time = 0
        self.open_time = 0
        self.lock = threading.RLock()
    def record_success(self):
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self._close_circuit()
    def record_error(self):
        with self.lock:
            now = time.time()
            if self.state == CircuitState.OPEN:
                if self.logger:
                    self.logger.debug(f"Circuit '{self.name}' is open, error recorded but ignored")
                return
            if self.state == CircuitState.HALF_OPEN:
                self._open_circuit()
                return
            if now - self.last_error_time > self.error_timeout:
                if self.error_count > 0 and self.logger:
                    self.logger.debug(f"Circuit '{self.name}' error timeout elapsed, resetting error count from {self.error_count} to 0")
                self.error_count = 0
            self.error_count += 1
            self.last_error_time = now
            if self.logger:
                self.logger.debug(f"Circuit '{self.name}' error count: {self.error_count}/{self.error_threshold}")
            if self.error_count >= self.error_threshold:
                self._open_circuit()
    def allow_request(self):
        with self.lock:
            now = time.time()
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                if now - self.open_time > self.circuit_timeout:
                    if self.logger:
                        self.logger.info(f"Circuit '{self.name}' timeout elapsed, moving to half-open state")
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            if self.state == CircuitState.HALF_OPEN:
                return True
            return False
    def _open_circuit(self):
        self.state = CircuitState.OPEN
        self.open_time = time.time()
        self.error_count = 0
        if self.logger:
            self.logger.warning(f"Circuit '{self.name}' opened due to excessive errors")
    def _close_circuit(self):
        self.state = CircuitState.CLOSED
        self.error_count = 0
        if self.logger:
            self.logger.info(f"Circuit '{self.name}' closed, resuming normal operation")
    def get_state(self):
        with self.lock:
            return self.state
    def reset(self):
        with self.lock:
            self.state = CircuitState.CLOSED
            self.error_count = 0
            self.last_error_time = 0
            self.open_time = 0
            if self.logger:
                self.logger.info(f"Circuit '{self.name}' manually reset to closed state")
class CircuitBreakerRegistry:
    def __init__(self, logger=None):
        self.logger = logger
        self.circuit_breakers = {}
        self.lock = threading.RLock()

    def get_circuit_breaker(self, name, error_threshold=None, error_timeout=None, circuit_timeout=None):
        with self.lock:
            if name not in self.circuit_breakers:
                import config
                _error_threshold = error_threshold or getattr(config, 'ERROR_THRESHOLD', 5)
                _error_timeout = error_timeout or getattr(config, 'ERROR_TIMEOUT', 60)
                _circuit_timeout = circuit_timeout or getattr(config, 'CIRCUIT_TIMEOUT', 300)
                self.circuit_breakers[name] = CircuitBreaker(
                    name=name,
                    error_threshold=_error_threshold,
                    error_timeout=_error_timeout,
                    circuit_timeout=_circuit_timeout,
                    logger=self.logger
                )
                if self.logger:
                    self.logger.debug(f"Created new circuit breaker '{name}'")
            return self.circuit_breakers[name]

    def reset_all(self):
        with self.lock:
            for circuit_breaker in self.circuit_breakers.values():
                circuit_breaker.reset()
            if self.logger:
                self.logger.info(f"Reset all circuit breakers ({len(self.circuit_breakers)})")

    def get_all_states(self):
        with self.lock:
            states = {}
            for name, circuit_breaker in self.circuit_breakers.items():
                states[name] = circuit_breaker.get_state().name
            return states
