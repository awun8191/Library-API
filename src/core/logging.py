"""Application logging.

The formatter writes one JSON object per line when the application runs in
production. A local run gets one short text line instead.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from core.config import AppSettings

# The handlers that this module added to the root logger.
_installed_handlers: list[logging.Handler] = []


def _current_request_id() -> str:
    """Return the identifier of the current request.

    The import stays in this function. A module level import would close a
    cycle with the middleware package.
    """
    from middleware.request_id import get_request_id

    return get_request_id()


def _format_timestamp(record: logging.LogRecord) -> str:
    """Return the record time as an ISO 8601 string in UTC."""
    moment = datetime.fromtimestamp(record.created, tz=timezone.utc)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _record_request_id(record: logging.LogRecord) -> str:
    """Return the request id of the record.

    The handler for an unexpected error runs after the reset, so it can pass
    the id on the record instead.
    """
    return getattr(record, "request_id", None) or _current_request_id()


class JsonFormatter(logging.Formatter):
    """Write one log record as one JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": _format_timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _record_request_id(record),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, default=str)


class TextFormatter(logging.Formatter):
    """Write one log record as one short text line."""

    def format(self, record: logging.LogRecord) -> str:
        line = (
            f"{_format_timestamp(record)} {record.levelname} {record.name} "
            f"request_id={_record_request_id(record)} {record.getMessage()}"
        )
        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        return line


def _resolve_level(name: str) -> int:
    """Return the level for a name. Use INFO for an unknown name."""
    level = logging.getLevelNamesMapping().get(name.strip().upper())
    return level if isinstance(level, int) else logging.INFO


def _remove_installed_handlers(root: logging.Logger) -> None:
    """Remove and close the handlers that an earlier call added."""
    while _installed_handlers:
        handler = _installed_handlers.pop()
        root.removeHandler(handler)
        handler.close()


def configure_logging(settings: AppSettings) -> None:
    """Attach the application log handler.

    A second call removes the handler of the first call. A reload then leaves
    one handler, and a test cannot stack them.
    """
    root = logging.getLogger()
    _remove_installed_handlers(root)

    handler = logging.StreamHandler(stream=sys.stdout)
    if settings.environment == "production" or settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(TextFormatter())

    root.addHandler(handler)
    root.setLevel(_resolve_level(settings.log_level))
    _installed_handlers.append(handler)
