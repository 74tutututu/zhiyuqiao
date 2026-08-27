from __future__ import annotations

from collections import defaultdict, deque
import hmac
import os
import secrets
from threading import Lock
import time

from fastapi import Request


CSRF_COOKIE_NAME = "zhiyuqiao_csrf"


def secure_cookies_enabled() -> bool:
    return os.getenv("ZHIYUQIAO_SECURE_COOKIES", "0") == "1"


def ensure_csrf_token(request: Request) -> str:
    state_token = str(getattr(request.state, "csrf_token", "")).strip()
    if state_token:
        return state_token
    token = str(request.cookies.get(CSRF_COOKIE_NAME, "")).strip()
    if not token:
        token = secrets.token_urlsafe(32)
    request.state.csrf_token = token
    return token


def validate_csrf_token(request: Request, supplied_token: str | None) -> bool:
    cookie_token = str(request.cookies.get(CSRF_COOKIE_NAME, "")).strip()
    supplied = str(supplied_token or "").strip()
    return bool(cookie_token and supplied and hmac.compare_digest(cookie_token, supplied))


def client_key(request: Request) -> str:
    forwarded = str(request.headers.get("x-forwarded-for", "")).split(",", 1)[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


class SlidingWindowLimiter:
    """Small-process rate limiter; production can swap this for Redis without changing routes."""

    def __init__(self, *, limit: int, window_seconds: int):
        self.limit = max(1, int(limit))
        self.window_seconds = max(1, int(window_seconds))
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[str(key)]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - events[0])))
                return False, retry_after
            events.append(now)
            return True, 0
