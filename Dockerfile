# syntax=docker/dockerfile:1

# Build stage. It installs the locked runtime dependencies into /app/.venv.
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# The dependency files come first, so Docker can cache this layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# The source follows, then the install completes with the project itself.
COPY . .
RUN uv sync --frozen --no-dev


# Runtime stage. It holds the venv and the source, and it runs as a non-root user.
FROM python:3.14-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    STORAGE_DIR=/app/Storage

# The image reads every secret from the environment. No .env file goes in.
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --home-dir /app --no-create-home app

WORKDIR /app

COPY --from=builder --chown=app:app /app /app

RUN mkdir -p /app/Storage && chown app:app /app/Storage

USER app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
