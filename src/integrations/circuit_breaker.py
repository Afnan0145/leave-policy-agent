"""
Circuit breaker pattern implementation for external service calls
Prevents cascading failures and enables graceful degradation
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps
import threading

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing recovery, allow one request
    
    Args:
        failure_threshold: Number of failures before opening circuit
        timeout: Seconds to wait before attempting recovery
        success_threshold: Successes needed in half-open to close circuit
        name: Identifier for this circuit breaker
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.name = name
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.RLock()
        
        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"failure_threshold={failure_threshold}, timeout={timeout}s"
        )
    
    @property
    def state(self) -> CircuitState:
        """Get current state"""
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN and self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
            
            return self._state
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self._last_failure_time is None:
            return False
        return time.time() - self._last_failure_time >= self.timeout
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception from func
        """
        current_state = self.state
        
        # Reject if circuit is open
        if current_state == CircuitState.OPEN:
            logger.warning(
                f"Circuit breaker '{self.name}' is OPEN, rejecting call"
            )
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is open. "
                f"Service unavailable, try again later."
            )
        
        # Attempt call
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            self._failure_count = 0
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.debug(
                    f"Circuit breaker '{self.name}' success in HALF_OPEN: "
                    f"{self._success_count}/{self.success_threshold}"
                )
                
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._success_count = 0
                    logger.info(f"Circuit breaker '{self.name}' closed - service recovered")
    
    def _on_failure(self):
        """Handle failed call"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            logger.warning(
                f"Circuit breaker '{self.name}' failure: "
                f"{self._failure_count}/{self.failure_threshold}"
            )
            
            # Open circuit if threshold reached
            if self._failure_count >= self.failure_threshold:
                if self._state != CircuitState.OPEN:
                    self._state = CircuitState.OPEN
                    logger.error(
                        f"Circuit breaker '{self.name}' opened after "
                        f"{self._failure_count} failures"
                    )
            
            # If in HALF_OPEN and still failing, back to OPEN
            elif self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._success_count = 0
                logger.error(
                    f"Circuit breaker '{self.name}' reopened during recovery attempt"
                )
    
    def reset(self):
        """Manually reset circuit breaker to closed state"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def get_stats(self) -> dict:
        """Get current statistics"""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "failure_threshold": self.failure_threshold,
                "timeout": self.timeout,
                "last_failure_time": self._last_failure_time
            }


def circuit_breaker(
    failure_threshold: int = 5,
    timeout: int = 60,
    success_threshold: int = 2,
    name: str = "default"
):
    """
    Decorator to add circuit breaker protection to a function
    
    Usage:
        @circuit_breaker(failure_threshold=3, timeout=30, name="my_service")
        def call_external_service():
            # your code here
            pass
    """
    # Create circuit breaker instance
    cb = CircuitBreaker(
        failure_threshold=failure_threshold,
        timeout=timeout,
        success_threshold=success_threshold,
        name=name
    )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        
        # Attach circuit breaker instance for access
        wrapper.circuit_breaker = cb
        return wrapper
    
    return decorator


# Global registry of circuit breakers
_circuit_breakers: dict[str, CircuitBreaker] = {}
_registry_lock = threading.RLock()


def get_circuit_breaker(name: str) -> Optional[CircuitBreaker]:
    """Get circuit breaker by name from registry"""
    with _registry_lock:
        return _circuit_breakers.get(name)


def register_circuit_breaker(name: str, circuit_breaker: CircuitBreaker):
    """Register a circuit breaker in global registry"""
    with _registry_lock:
        _circuit_breakers[name] = circuit_breaker
        logger.debug(f"Registered circuit breaker: {name}")


def get_all_circuit_breaker_stats() -> list[dict]:
    """Get stats for all registered circuit breakers"""
    with _registry_lock:
        return [cb.get_stats() for cb in _circuit_breakers.values()]