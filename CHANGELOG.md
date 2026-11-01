# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Each minor version matches one week of the BuildLab program.

## [Unreleased]

Nothing yet.

## [0.3.0] - 2026-11-01

Week 3. Tests, observability, and continuous integration.

### Added

- A Vercel entrypoint in `index.py` and a `vercel.json` with the FastAPI framework preset.
- An OpenAPI snapshot in `openapi.json` and a script that regenerates it.
- A CI step that fails when the snapshot and the code disagree.
- Community files: license, contribution guide, security policy, issue forms, and a pull request template.
- A pytest suite with 132 tests and 94 percent line coverage.
- A test harness that applies the migrations to a separate database, truncates the tables, and rolls back each test in a transaction.
- Unit tests for the services and contract tests for the adapters.
- A database-backed rate limiter with a fixed window, in `src/middleware/rate_limit.py` and `src/integrations/rate_limit.py`.
- Separate limits for login, signup, upload, and every other route, and the `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, and `Retry-After` headers.
- An in-memory rate limit store for tests and for a single worker.
- A request identifier middleware and the `X-Request-ID` response header.
- Text logs in development and JSON logs in production, with the request identifier on each line.
- A 4 MB upload limit, checked before the route reads the body.
- The `GET /health` route, which reports the state of the application and the database.
- A configurable storage directory through `STORAGE_DIR`.
- Ruff configuration for lint and format, and a formatted codebase.
- A production Docker image.
- The `Lint`, `Test`, `Docker`, and `CI gate` jobs.
- The `Deploy`, `Rollback`, `Release`, and `Monitor` workflows.

### Changed

- The rate limit counters live in PostgreSQL, so a restart does not reset them.
- The health route answers `503` when the database is not reachable.
- The README now documents the test suite, the rate limits, the health route, the CI workflows, and the deployment plan.
- The lint configuration covers `scripts/`, so the seed and export scripts follow the same rules.

## [0.2.0] - 2026-10-24

Week 2. Authentication and guarded file delivery.

### Added

- Signup and login routes with Argon2 password hashing and a signed JWT access token.
- Role checks that read the user from the database on each request, so a role change or a deactivated account takes effect at once.
- An authenticated `GET /api/v1/books/{id}/file` route that streams the PDF and writes one `BookAccess` row.
- The `GET /api/v1/users/me/access-history` route with cursor pagination.
- The course code filter on the book list.
- CORS middleware with origins from `CORS_ALLOW_ORIGINS`.
- A stable error code on every handled error.

### Changed

- `PATCH` replaces `PUT` for books and profiles, because the handlers update a subset of the fields.
- The book response no longer exposes sensitive account fields.
- Search terms are matched literally, so `%` and `_` are not wildcards.

### Fixed

- Routes that must stay public no longer require a token.

## [0.1.0] - 2026-10-16

Week 1. The first working API.

### Added

- The FastAPI application with a domain-driven layout: `core`, `integrations`, `middleware`, `modules`, and `schema`.
- PostgreSQL persistence through SQLAlchemy 2.1, with Alembic migrations.
- The users, departments, and books modules, each with data, repository, service, and router files.
- Admin upload of a PDF through `POST /api/v1/books`, with a SHA-256 file hash and a `UNIQUE` constraint that rejects a duplicate with `409`.
- Book update and delete routes.
- Search on the book name, the department filter, and cursor pagination on the book list.
- Access recording and the reading history route for the current user.
- Local PDF storage with a PDF signature check, served from the `/static/books` mount.
- A development admin identity, so the admin routes could be exercised before authentication.
- A development seed script with departments, two accounts, and three dummy PDFs.
- A Docker Compose service for PostgreSQL 17.
- The setup guide and the request and response examples in the README.

### Changed

- Invalid input returns `400` with the field names and the messages, not `422`.
- An unexpected error returns `500` without a stack trace.
- The docs routes are disabled in production.
