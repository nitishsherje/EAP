"""Reliability primitives (Layer 0): retry/backoff and circuit breaker.

Kept dependency-free and synchronous for MVP1. Timeouts are delegated to the
adapters (which own the transport client). Bulkheads/idempotency can be layered
on later where justified.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from eap.common.errors import EapError, ErrorCode

T = TypeVar("T")


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 0.1
    max_delay: float = 2.0
    backoff_factor: float = 2.0

    def delay_for(self, attempt: int) -> float:
        return min(self.base_delay * (self.backoff_factor ** (attempt - 1)), self.max_delay)


def retry_call(
    fn: Callable[[], T],
    policy: RetryPolicy | None = None,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``fn`` with retries and exponential backoff."""
    policy = policy or RetryPolicy()
    last_exc: Exception | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return fn()
        except retry_on as exc:  # noqa: PERF203
            last_exc = exc
            if attempt == policy.max_attempts:
                break
            sleep(policy.delay_for(attempt))
    assert last_exc is not None
    raise last_exc


class CircuitOpenError(EapError):
    default_code = ErrorCode.PROVIDER_ERROR


class CircuitBreaker:
    """Simple circuit breaker: opens after N consecutive failures for a cooldown."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 30.0) -> None:
        self._threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        # After the cooldown the breaker is half-open: allow a trial call.
        return (time.monotonic() - self._opened_at) < self._reset_timeout

    def call(self, fn: Callable[[], T]) -> T:
        if self.is_open:
            raise CircuitOpenError("circuit breaker is open")
        try:
            result = fn()
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result

    def _record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = time.monotonic()

    def _record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
