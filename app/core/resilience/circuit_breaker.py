"""Circuit breaker pattern for third-party services and unstable external providers."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """Raised when an execution attempt is blocked by an open circuit breaker."""

    pass


class CircuitBreaker:
    """Monitors external service errors and trips open to prevent cascading failure."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_time_sec: float = 30.0,
        recovery_timeout: float | None = None,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_time_sec = (
            recovery_timeout if recovery_timeout is not None else recovery_time_sec
        )
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()

    async def call(
        self,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Executes coroutine protected by circuit breaker state rules."""
        now = time.time()

        if self.state == CircuitState.OPEN:
            if now - self.last_state_change > self.recovery_time_sec:
                logger.info("Circuit breaker %s entered HALF_OPEN state (probing)", self.name)
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
            else:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker {self.name} is OPEN (cooldown remaining)"
                )

        try:
            result = await func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker %s probe succeeded, resetting to CLOSED", self.name)
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.last_state_change = now
            return result
        except Exception as exc:
            self.failure_count += 1
            logger.warning(
                "Circuit breaker %s observed failure (%d/%d): %s",
                self.name,
                self.failure_count,
                self.failure_threshold,
                exc,
            )
            if self.failure_count >= self.failure_threshold:
                logger.error("Circuit breaker %s tripped to OPEN state", self.name)
                self.state = CircuitState.OPEN
                self.last_state_change = now
            raise exc


_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name)
    return _breakers[name]
