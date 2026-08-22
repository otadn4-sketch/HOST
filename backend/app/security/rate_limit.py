from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def allow(self, key: str, *, limit: int, window_seconds: float) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._events[key]
            cutoff = now - window_seconds
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


limiter = SlidingWindowLimiter()
