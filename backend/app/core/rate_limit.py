from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int


class InMemorySlidingWindowRateLimiter:
    """基于滑动窗口的轻量级内存限流器。"""

    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max(1, int(max_requests))
        self._window_seconds = max(1, int(window_seconds))
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    def hit(self, key: str) -> RateLimitResult:
        now = monotonic()
        safe_key = (key or "").strip() or "__default__"
        with self._lock:
            queue = self._events.setdefault(safe_key, deque())
            self._prune(queue=queue, now=now)
            if len(queue) >= self._max_requests:
                retry_after = max(1, int(self._window_seconds - (now - queue[0])))
                return RateLimitResult(allowed=False, retry_after_seconds=retry_after)
            queue.append(now)
            return RateLimitResult(allowed=True, retry_after_seconds=0)

    def _prune(self, *, queue: deque[float], now: float) -> None:
        threshold = now - self._window_seconds
        while queue and queue[0] <= threshold:
            queue.popleft()
