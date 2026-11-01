"""Unit tests for the rate limit rules, the client address, and the stores."""

import pytest
from starlette.requests import Request

from core.config import get_settings
from integrations.rate_limit import (
    MemoryRateLimitStore,
    PostgresRateLimitStore,
    build_rate_limit_store,
)
from middleware.rate_limit import match_rule, resolve_client_ip

FIXED_TIME = 1_700_000_000.0


class MutableClock:
    """Hold the time that a store reads."""

    def __init__(self, value: float = FIXED_TIME) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def build_request(
    path: str = "/api/v1/books",
    method: str = "GET",
    headers: dict[str, str] | None = None,
    client: tuple[str, int] | None = ("10.0.0.1", 5000),
) -> Request:
    """Build a request with the given method, path, headers, and peer."""
    raw_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": b"",
        "headers": raw_headers,
        "client": client,
        "server": ("testserver", 80),
        "root_path": "",
    }
    return Request(scope)


def test_memory_store_counts_within_one_window() -> None:
    clock = MutableClock()
    store = MemoryRateLimitStore(now=clock)

    first = store.increment("login:10.0.0.1", 60)
    second = store.increment("login:10.0.0.1", 60)

    assert first.hits == 1
    assert second.hits == 2
    assert first.window_start == second.window_start
    assert first.window_seconds == 60


def test_memory_store_starts_a_new_count_in_the_next_window() -> None:
    clock = MutableClock()
    store = MemoryRateLimitStore(now=clock)
    store.increment("login:10.0.0.1", 60)
    store.increment("login:10.0.0.1", 60)

    clock.value += 61
    hit = store.increment("login:10.0.0.1", 60)

    assert hit.hits == 1


def test_memory_store_prune_removes_old_counters() -> None:
    clock = MutableClock()
    store = MemoryRateLimitStore(now=clock)
    store.increment("login:10.0.0.1", 3600)

    # The hour window is still open, so only the prune can remove the counter.
    clock.value += 120
    store.prune(older_than_seconds=60)
    hit = store.increment("login:10.0.0.1", 3600)

    assert hit.hits == 1


def test_memory_store_keeps_a_counter_that_is_not_old() -> None:
    clock = MutableClock()
    store = MemoryRateLimitStore(now=clock)
    store.increment("login:10.0.0.1", 60)

    store.prune(older_than_seconds=86400)
    hit = store.increment("login:10.0.0.1", 60)

    assert hit.hits == 2


def test_memory_store_reset_clears_the_counters() -> None:
    clock = MutableClock()
    store = MemoryRateLimitStore(now=clock)
    store.increment("login:10.0.0.1", 60)

    store.reset()
    hit = store.increment("login:10.0.0.1", 60)

    assert hit.hits == 1


def test_build_rate_limit_store_returns_the_memory_adapter() -> None:
    settings = get_settings().model_copy(update={"rate_limit_backend": "memory"})

    store = build_rate_limit_store(settings)

    assert isinstance(store, MemoryRateLimitStore)


def test_build_rate_limit_store_returns_the_postgres_adapter() -> None:
    settings = get_settings().model_copy(update={"rate_limit_backend": "postgres"})

    store = build_rate_limit_store(settings)

    assert isinstance(store, PostgresRateLimitStore)


def test_build_rate_limit_store_reuses_the_memory_store() -> None:
    settings = get_settings().model_copy(update={"rate_limit_backend": "memory"})

    first = build_rate_limit_store(settings)
    second = build_rate_limit_store(settings)

    assert first is second


@pytest.mark.parametrize(
    ("method", "path", "name", "window"),
    [
        ("POST", "/api/v1/auth/login", "login", 60),
        ("POST", "/api/v1/auth/signup", "signup", 3600),
        ("POST", "/api/v1/books", "upload", 3600),
    ],
)
def test_match_rule_picks_the_specific_route(
    method: str, path: str, name: str, window: int
) -> None:
    rule = match_rule(method, path)

    assert rule.name == name
    assert rule.window_seconds == window
    assert rule.path == path


def test_match_rule_falls_back_to_the_default_rule() -> None:
    rule = match_rule("GET", "/api/v1/books")

    assert rule.name == "default"
    assert rule.window_seconds == 60
    assert rule.method == "*"


def test_match_rule_ignores_a_trailing_slash() -> None:
    rule = match_rule("POST", "/api/v1/auth/login/")

    assert rule.name == "login"


def test_client_ip_uses_the_last_forwarded_hop() -> None:
    request = build_request(headers={"X-Forwarded-For": "203.0.113.7, 198.51.100.4, 10.0.0.9"})

    client_ip = resolve_client_ip(request, trust_proxy_headers=True)

    assert client_ip == "10.0.0.9"


def test_client_ip_prefers_the_real_ip_header() -> None:
    request = build_request(
        headers={
            "X-Real-IP": "203.0.113.7",
            "X-Forwarded-For": "198.51.100.4, 10.0.0.9",
        }
    )

    client_ip = resolve_client_ip(request, trust_proxy_headers=True)

    assert client_ip == "203.0.113.7"


def test_client_ip_ignores_proxy_headers_when_not_trusted() -> None:
    request = build_request(
        headers={
            "X-Real-IP": "203.0.113.7",
            "X-Forwarded-For": "198.51.100.4, 10.0.0.9",
        },
        client=("192.0.2.30", 5000),
    )

    client_ip = resolve_client_ip(request, trust_proxy_headers=False)

    assert client_ip == "192.0.2.30"


def test_client_ip_is_unknown_without_headers_and_peer() -> None:
    request = build_request(client=None)

    client_ip = resolve_client_ip(request, trust_proxy_headers=False)

    assert client_ip == "unknown"
