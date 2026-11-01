"""Unit tests for the log formatters and the log setup."""
import json
import logging
from datetime import datetime
from typing import Generator

import pytest

from core.config import AppSettings
from core.logging import JsonFormatter, TextFormatter, configure_logging


def build_settings(**overrides: object) -> AppSettings:
    """Build settings that do not depend on the test environment."""
    values: dict[str, object] = {
        "database_url": "postgresql+psycopg://user:password@localhost:5432/example",
        "secret_key": "a-secret-key-for-the-logging-unit-tests-0001",
        "environment": "development",
    }
    values.update(overrides)
    return AppSettings(**values)


def build_record(message: str = "A test line") -> logging.LogRecord:
    """Build one INFO record for the formatters."""
    return logging.LogRecord(
        name="core.example",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def app_handlers() -> list[logging.Handler]:
    """Return the handlers that configure_logging added to the root logger."""
    return [
        handler
        for handler in logging.getLogger().handlers
        if isinstance(handler.formatter, (JsonFormatter, TextFormatter))
    ]


@pytest.fixture
def restore_logging() -> Generator[None, None, None]:
    """Put the application log setup back after a test that changes it."""
    root = logging.getLogger()
    level = root.level
    yield
    configure_logging(build_settings())
    root.setLevel(level)


def test_the_json_formatter_writes_the_required_fields() -> None:
    payload = json.loads(JsonFormatter().format(build_record("The upload failed")))

    assert {"ts", "level", "logger", "message", "request_id"} <= set(payload)
    assert payload["level"] == "INFO"
    assert payload["logger"] == "core.example"
    assert payload["message"] == "The upload failed"
    assert payload["request_id"] == "-"
    assert payload["ts"].endswith("Z")
    # The timestamp must parse as an ISO 8601 value.
    assert datetime.fromisoformat(payload["ts"].replace("Z", "+00:00")).tzinfo is not None


def test_configure_logging_twice_leaves_one_handler(restore_logging: None) -> None:
    settings = build_settings()

    configure_logging(settings)
    configure_logging(settings)

    assert len(app_handlers()) == 1


def test_the_formatter_follows_the_environment_and_the_flag(restore_logging: None) -> None:
    configure_logging(build_settings(environment="production"))
    assert isinstance(app_handlers()[0].formatter, JsonFormatter)

    configure_logging(build_settings(log_json=True))
    assert isinstance(app_handlers()[0].formatter, JsonFormatter)

    configure_logging(build_settings())
    assert isinstance(app_handlers()[0].formatter, TextFormatter)


def test_configure_logging_applies_the_level(restore_logging: None) -> None:
    configure_logging(build_settings(log_level="ERROR"))

    assert logging.getLogger().level == logging.ERROR
