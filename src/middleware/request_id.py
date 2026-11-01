"""Request identifier middleware.

The middleware gives each request one identifier. A log line and an error
response can then point to the same request.
"""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

# The default covers a log line that no request produced.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the identifier of the current request. Return '-' outside a request."""
    return request_id_var.get()


def is_valid_request_id(value: str) -> bool:
    """Return True when the client value is safe to echo."""
    return REQUEST_ID_PATTERN.fullmatch(value) is not None


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Read or create the request identifier and put it on the response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if is_valid_request_id(incoming) else uuid.uuid4().hex

        # The request state also serves the handler for an unexpected error.
        # That handler runs outside this middleware, after the reset below.
        request.state.request_id = request_id

        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            request_id_var.reset(token)


def add_request_id_middleware(app: FastAPI) -> None:
    """Attach the request identifier middleware to the application."""
    app.add_middleware(RequestIdMiddleware)
