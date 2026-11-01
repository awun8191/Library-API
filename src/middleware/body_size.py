"""Upload size guard middleware.

Vercel rejects a request body over 4.5 MB before the function runs. The
application keeps a smaller limit of its own. The middleware compares the
declared length only. It never reads the body.
"""
from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from core.config import get_settings
from core.exceptions import FileTooLargeException


def _declared_length(request: Request) -> int | None:
    """Return the Content-Length of the request. Return None when it is absent."""
    raw = request.headers.get("content-length")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Refuse an oversized upload before the route reads the body."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        if request.method == "POST" and request.url.path == f"{settings.api_prefix}/books":
            limit = settings.max_upload_mb * 1024 * 1024
            declared = _declared_length(request)
            if declared is not None and declared > limit:
                error = FileTooLargeException()
                return JSONResponse(
                    status_code=error.status_code,
                    content={"message": error.message, "code": error.code},
                )
        return await call_next(request)


def add_body_size_middleware(app: FastAPI) -> None:
    """Attach the upload size guard to the application."""
    app.add_middleware(BodySizeLimitMiddleware)
