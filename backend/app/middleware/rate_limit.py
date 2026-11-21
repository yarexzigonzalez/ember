from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

from app.config import settings


class InMemoryRateLimiter:
    """Fixed-window counter in this process only. Multiple servers do not share it."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def allow(self, key: str, max_hits: int, window_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            recent = [stamp for stamp in self._hits[key] if now - stamp < window_seconds]
            if len(recent) >= max_hits:
                self._hits[key] = recent
                return False
            recent.append(now)
            self._hits[key] = recent
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = InMemoryRateLimiter()


def client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host


def limit_auth_endpoints(request: Request) -> None:
    key = f"auth:{client_ip(request)}"
    if limiter.allow(key, settings.auth_rate_limit, settings.auth_rate_window_seconds):
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many attempts. Try again later.",
        headers={"Retry-After": str(settings.auth_rate_window_seconds)},
    )
