"""Rate limit middleware.

The middleware counts the requests of each client on each rule. The store owns
the window. The settings and the store are read on each request, so a test can
change them at runtime.
"""

from __future__ import annotations

import contextlib
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Request, status
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from core.config import AppSettings, get_settings
from core.exceptions import RateLimitedException
from core.repository import RateLimitHit
from integrations.rate_limit import build_rate_limit_store

PRUNE_OLDER_THAN_SECONDS = 86400


@dataclass(frozen=True)
class RateLimitRule:
    """Describe one limited route."""

    name: str
    method: str
    path: str
    limit_setting: str
    window_seconds: int


# The order matters. The first rule that matches wins.
RATE_LIMIT_RULES: tuple[RateLimitRule, ...] = (
    RateLimitRule(
        name="login",
        method="POST",
        path="/api/v1/auth/login",
        limit_setting="rate_limit_login_per_minute",
        window_seconds=60,
    ),
    RateLimitRule(
        name="signup",
        method="POST",
        path="/api/v1/auth/signup",
        limit_setting="rate_limit_signup_per_hour",
        window_seconds=3600,
    ),
    RateLimitRule(
        name="upload",
        method="POST",
        path="/api/v1/books",
        limit_setting="rate_limit_upload_per_hour",
        window_seconds=3600,
    ),
    RateLimitRule(
        name="default",
        method="*",
        path="",
        limit_setting="rate_limit_default_per_minute",
        window_seconds=60,
    ),
)


def match_rule(method: str, path: str) -> RateLimitRule:
    """Return the most specific rule for the method and the path."""
    normalized = path.rstrip("/") or "/"
    for rule in RATE_LIMIT_RULES:
        if rule.method != "*" and rule.method != method.upper():
            continue
        if rule.path and rule.path != normalized:
            continue
        return rule
    return RATE_LIMIT_RULES[-1]


def resolve_client_ip(request: Request, trust_proxy_headers: bool) -> str:
    """Return the address of the client. Trust a proxy header only when configured."""
    if trust_proxy_headers:
        real_ip = request.headers.get("x-real-ip")
        if real_ip and real_ip.strip():
            return real_ip.strip()

        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
            if hops:
                # The last hop is the one that the closest proxy added.
                return hops[-1]

    client = request.client
    if client is not None and client.host:
        return client.host
    return "unknown"


def _seconds_until_window_end(hit: RateLimitHit) -> int:
    """Return the whole seconds left in the window of a hit. The value is at least 0."""
    window_start = hit.window_start
    if window_start.tzinfo is None:
        window_start = window_start.replace(tzinfo=UTC)
    window_end = window_start + timedelta(seconds=hit.window_seconds)
    seconds_left = (window_end - datetime.now(UTC)).total_seconds()
    return max(0, math.ceil(seconds_left))


def _rate_limit_headers(limit: int, hit: RateLimitHit, reset_seconds: int) -> dict[str, str]:
    """Build the headers that describe the state of the counter."""
    remaining = max(0, limit - hit.hits)
    return {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset_seconds),
    }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Count the requests of each client and refuse the ones over the limit."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings: AppSettings = get_settings()
        if not settings.rate_limit_enabled:
            return await call_next(request)

        rule = match_rule(request.method, request.url.path)
        limit = int(getattr(settings, rule.limit_setting))
        client_ip = resolve_client_ip(request, settings.trust_proxy_headers)
        store = build_rate_limit_store(settings)

        # The increment must fail loudly. A silent skip would remove the limit.
        hit = await run_in_threadpool(
            store.increment, f"{rule.name}:{client_ip}", rule.window_seconds
        )

        if hit.hits == 1:
            # A prune failure must not fail the request. The next hit tries again.
            with contextlib.suppress(Exception):
                await run_in_threadpool(store.prune, PRUNE_OLDER_THAN_SECONDS)

        reset_seconds = _seconds_until_window_end(hit)
        headers = _rate_limit_headers(limit, hit, reset_seconds)

        if hit.hits > limit:
            error = RateLimitedException()
            headers["Retry-After"] = str(max(1, reset_seconds))
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"message": error.message, "code": error.code},
                headers=headers,
            )

        response = await call_next(request)
        response.headers.update(headers)
        return response


def add_rate_limit_middleware(app: FastAPI) -> None:
    """Attach the rate limit middleware to the application."""
    app.add_middleware(RateLimitMiddleware)
