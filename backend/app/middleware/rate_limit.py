from __future__ import annotations

import logging
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

from app.config import settings

logger = logging.getLogger("ember.rate_limit")


class InMemoryRateLimiter:
    """Sliding window counter that lives in this process only.

    Two API instances would each have their own counts. For one Render box
    that's fine; Redis is the move if it ever scales out.
    """

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


def resolve_client_ip(peer: str | None, forwarded_for: str | None, trusted_hops: int) -> str:
    """Figure out who's actually on the other end.

    Every proxy appends the address it got the request from to
    X-Forwarded-For. With N proxies we trust, the real client is the Nth entry
    from the right. Anything further left came from the client, so it could be
    made up and we skip it.

    If the chain is shorter than expected, the request skipped a proxy, so we
    take the leftmost entry (the closest thing to a real peer we've got).
    """
    if trusted_hops <= 0 or not forwarded_for:
        return peer or "unknown"
    chain = [part.strip() for part in forwarded_for.split(",") if part.strip()]
    if not chain:
        return peer or "unknown"
    if len(chain) >= trusted_hops:
        return chain[-trusted_hops]
    return chain[0]


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    resolved = resolve_client_ip(peer, forwarded, settings.trusted_proxy_hops)
    if settings.log_client_ip:
        logger.warning("client ip: peer=%s xff=%r hops=%s -> %s", peer, forwarded,
                       settings.trusted_proxy_hops, resolved)
    return resolved


def rate_limit(bucket: str, max_hits: int, window_seconds: int):
    """Build a FastAPI dependency that limits one bucket per client IP."""

    def dependency(request: Request) -> None:
        key = f"{bucket}:{client_ip(request)}"
        if limiter.allow(key, max_hits, window_seconds):
            return
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Give it a few minutes.",
            headers={"Retry-After": str(window_seconds)},
        )

    return dependency


def limit_auth_endpoints(request: Request) -> None:
    # Read settings at call time so tests can shrink the limit.
    rate_limit("auth", settings.auth_rate_limit, settings.auth_rate_window_seconds)(request)
