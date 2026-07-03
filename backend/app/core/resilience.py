import asyncio
import time
from collections import deque
from typing import Awaitable, Callable, Deque, TypeVar

T = TypeVar("T")


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.failures = 0
        self.opened_at = 0.0

    @property
    def is_open(self) -> bool:
        if self.failures < self.failure_threshold:
            return False
        if time.monotonic() - self.opened_at > self.recovery_seconds:
            self.failures = 0
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = 0.0

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.monotonic()


class AsyncRateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls: Deque[float] = deque()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self.lock:
            now = time.monotonic()
            while self.calls and now - self.calls[0] > self.window_seconds:
                self.calls.popleft()

            if len(self.calls) >= self.max_calls:
                sleep_for = self.window_seconds - (now - self.calls[0])
                await asyncio.sleep(max(sleep_for, 0.0))

            self.calls.append(time.monotonic())


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    timeout: float = 20.0,
    breaker: CircuitBreaker | None = None,
) -> T:
    if breaker and breaker.is_open:
        raise RuntimeError("Provider circuit breaker is open")

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            result = await asyncio.wait_for(operation(), timeout=timeout)
            if breaker:
                breaker.record_success()
            return result
        except Exception as exc:
            last_error = exc
            if breaker:
                breaker.record_failure()
            if attempt < attempts - 1:
                await asyncio.sleep(base_delay * (2**attempt))

    raise last_error or RuntimeError("Operation failed")
