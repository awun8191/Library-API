"""Rate limit counter stores.

The stores keep one counter for each key and each window. The window math is
shared. A window starts at the floor of the current time divided by the window
length.
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from core.config import AppSettings
from core.repository import RateLimitHit, RateLimitStore
from integrations.database import get_db_manager

INCREMENT_SQL = text(
    """
    INSERT INTO rate_limit_counters (key, window_start, hits)
    VALUES (
        :key,
        to_timestamp(
            floor(extract(epoch from now()) / CAST(:window AS double precision)) * :window
        ),
        1
    )
    ON CONFLICT (key) DO UPDATE
    SET hits = CASE
            WHEN rate_limit_counters.window_start = EXCLUDED.window_start
            THEN rate_limit_counters.hits + 1
            ELSE 1
        END,
        window_start = EXCLUDED.window_start
    RETURNING hits, window_start
    """
)

PRUNE_SQL = text("DELETE FROM rate_limit_counters WHERE window_start < :cutoff")


def _window_start_from_epoch(epoch: float, window_seconds: int) -> float:
    """Return the start of the window that holds the given epoch time."""
    return math.floor(epoch / window_seconds) * window_seconds


class PostgresRateLimitStore:
    """Keep the counters in a database table."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def increment(self, key: str, window_seconds: int) -> RateLimitHit:
        """Add one hit with one atomic upsert and return the new counter state."""
        with self._session_factory() as session:
            row = session.execute(INCREMENT_SQL, {"key": key, "window": window_seconds}).one()
            session.commit()

        return RateLimitHit(
            hits=int(row.hits),
            window_start=row.window_start,
            window_seconds=window_seconds,
        )

    def prune(self, older_than_seconds: int) -> None:
        """Delete the counters whose window started before the cutoff."""
        cutoff = datetime.now(UTC) - timedelta(seconds=older_than_seconds)
        with self._session_factory() as session:
            session.execute(PRUNE_SQL, {"cutoff": cutoff})
            session.commit()


class MemoryRateLimitStore:
    """Keep the counters in this process. Use it for tests and for one worker."""

    def __init__(self, now: Callable[[], float] = time.time) -> None:
        self._now = now
        self._lock = threading.Lock()
        # Each value holds the hit count and the start of its window.
        self._counters: dict[str, tuple[int, float]] = {}

    def increment(self, key: str, window_seconds: int) -> RateLimitHit:
        """Add one hit to the counter of the key and return the new state."""
        with self._lock:
            window_start = _window_start_from_epoch(self._now(), window_seconds)
            hits, stored_start = self._counters.get(key, (0, window_start))
            if stored_start != window_start:
                # The old window ended. Start a new count.
                hits = 0
            hits += 1
            self._counters[key] = (hits, window_start)

        return RateLimitHit(
            hits=hits,
            window_start=datetime.fromtimestamp(window_start, tz=UTC),
            window_seconds=window_seconds,
        )

    def prune(self, older_than_seconds: int) -> None:
        """Delete the counters whose window started before the cutoff."""
        with self._lock:
            cutoff = self._now() - older_than_seconds
            stale = [key for key, (_, start) in self._counters.items() if start < cutoff]
            for key in stale:
                del self._counters[key]

    def reset(self) -> None:
        """Forget every counter."""
        with self._lock:
            self._counters.clear()


@lru_cache
def _memory_store() -> MemoryRateLimitStore:
    """Return the one memory store of this process."""
    return MemoryRateLimitStore()


@lru_cache
def _postgres_store() -> PostgresRateLimitStore:
    """Return the one database store of this process."""
    return PostgresRateLimitStore(get_db_manager().session_factory)


def build_rate_limit_store(settings: AppSettings) -> RateLimitStore:
    """Return the store for the configured backend."""
    if settings.rate_limit_backend == "memory":
        return _memory_store()
    return _postgres_store()


def clear_rate_limit_stores() -> None:
    """Drop the cached stores. A new memory store starts with no counters."""
    _memory_store.cache_clear()
    _postgres_store.cache_clear()
