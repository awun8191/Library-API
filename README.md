# BuildLab Library API

A small FastAPI service that gives a school one place to keep course PDFs: admins upload, students search and download, and every download lands in the reading history.

[![CI](https://github.com/awun8191/Library-API/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/awun8191/Library-API/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)

## What it does

A school library keeps lecture notes and past questions in many places. This API puts the PDFs behind one small contract:

- An admin uploads a PDF with a name, course name, topic, course code, and department.
- Anyone can list and search books, and filter by department or course code.
- A signed-in student downloads the PDF from one authenticated route.
- The same request that serves the file writes one history row, so a student can return to the books they opened.

The problem statement is deliberately short. The value is in a clear contract, a tested error shape, and a codebase that a reader can follow.

## Features

| Feature | Detail |
|---|---|
| Admin upload | Multipart form. PDF signature check. SHA-256 hash with a `UNIQUE` constraint |
| Duplicate guard | A second upload of the same bytes returns `409` with the book that holds the file |
| Search | Literal match on the book name. `%` and `_` are not wildcards |
| Filters | Department id and course code, combined with the search |
| Pagination | Cursor based on the book list and on the reading history |
| Authenticated download | One route streams the PDF and records the access in one step |
| Access history | Newest first, cursor paginated |
| Rate limits | Four rules, counters in PostgreSQL |
| Request ids | `X-Request-ID` on every response and on every log line |
| Health route | `GET /health` reports the application and the database |
| Structured logs | Text in development, one JSON object per line in production |
| Tests | 132 tests, 94 percent line coverage |

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.14 |
| Framework | FastAPI with Pydantic v2 response models |
| ORM | SQLAlchemy 2.1 |
| Database | PostgreSQL 17 |
| Migrations | Alembic |
| Passwords | Argon2id through `argon2-cffi` |
| Tokens | JWT (HS256) through PyJWT |
| Package manager | uv |
| Lint and format | ruff |
| Tests | pytest with coverage |
| Containers | Docker, with a production image and Compose for the database |
| Automation | GitHub Actions |
| Deployment target | Vercel with a Neon PostgreSQL database |

## Quickstart in five minutes

You need Python 3.14, [uv](https://docs.astral.sh/uv/), and Docker.

```bash
git clone https://github.com/awun8191/Library-API.git
cd Library-API
uv sync
cp .env.example .env
```

Start PostgreSQL. The default local port is `5432`:

```bash
docker run -d --name buildlab-db \
  -e POSTGRES_DB=buildlab \
  -e POSTGRES_USER=buildlab \
  -e POSTGRES_PASSWORD=buildlab_dev_password \
  -p 5432:5432 postgres:17-alpine
```

If port `5432` is taken, change the left side of `-p` and change the port in `DATABASE_URL` in `.env` to the same value. The workspace used to build this project maps the database to `5435`, so its `DATABASE_URL` ends in `@localhost:5435/buildlab`. `docker compose up -d db` starts the same service from `docker-compose.yml`.

Create the tables and load the development data:

```bash
uv run alembic upgrade head
uv run python scripts/seed.py
```

Run the API from the repository root, so the application finds `.env`:

```bash
uv run uvicorn main:app --app-dir src --reload
```

Open <http://localhost:8000/docs> and try every route. The docs routes answer only while `ENVIRONMENT` is `development`.

The seed script prints the development logins:

| Account | Email | Password | Role |
|---|---|---|---|
| Admin | `admin@school.edu` | `dev-password-123` | `admin` |
| Student | `student@school.edu` | `dev-password-123` | `user` |

Both accounts use an Argon2 hash. The script is safe to run more than once, and it reuses an existing row instead of a duplicate.

## API summary

All routes except `/health` sit under the `/api/v1` prefix. "Authenticated" means a valid bearer token. "Admin" means a valid token whose database role is `admin`.

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| GET | `/health` | Public | Application and database state | 200, 503 |
| POST | `/api/v1/auth/signup` | Public | Create a student account | 201, 400, 404, 409, 429 |
| POST | `/api/v1/auth/login` | Public | Get an access token | 200, 401, 403, 429 |
| GET | `/api/v1/users/me` | Authenticated | Current profile | 200, 401, 403, 404 |
| PATCH | `/api/v1/users/me` | Authenticated | Update own profile | 200, 400, 401, 403, 404 |
| GET | `/api/v1/users/me/access-history` | Authenticated | Books the current user opened | 200, 400, 401, 403 |
| GET | `/api/v1/books` | Public | Search, filter, and page the book list | 200, 400 |
| GET | `/api/v1/books/{id}` | Public | One book | 200, 404 |
| GET | `/api/v1/books/{id}/file` | Authenticated | Stream the PDF and record the access | 200, 401, 403, 404 |
| POST | `/api/v1/books` | Admin | Upload a PDF | 201, 400, 401, 403, 404, 409, 413, 429 |
| PATCH | `/api/v1/books/{id}` | Admin | Update book details | 200, 400, 401, 403, 404 |
| DELETE | `/api/v1/books/{id}` | Admin | Delete the book and its file | 204, 401, 403, 404 |
| GET | `/api/v1/departments` | Public | Departments for filtering | 200 |

`GET /health` answers `503` with `{"status": "error", "database": "error", "version": "v1"}` when the database does not answer.

The repository stores the full schema in [`openapi.json`](./openapi.json). Regenerate it after a route or a model change:

```bash
uv run python scripts/export_openapi.py
```

## Authentication

1. **Signup** creates a student account. The role is always `user`. A duplicate email returns `409`.
2. **Login** checks the password against the Argon2 hash and returns a signed access token.
3. **Every guarded request** sends the token as `Authorization: Bearer <token>`.
4. **The API reads the user from the database** on each request. A role change, a deactivation, or a deleted account takes effect at once, and a token cannot outlive it.

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@school.edu","password":"dev-password-123"}'
```

```json
{ "access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer", "expires_in": 3600 }
```

Token contents:

| Claim | Value |
|---|---|
| `sub` | The user id as a string |
| `iat` | Issue time |
| `exp` | Expiry, after `ACCESS_TOKEN_EXPIRE_MINUTES` (60 by default) |
| `iss` | `library-api` |

The token carries no role. `require_admin` reads `role` from the `users` row, so a token minted for a student cannot reach an admin route even after a hand edit. The decoder requires `exp` and `sub`, and it accepts only `JWT_ALGORITHM`.

## Rate limits

The middleware counts each client address on each rule. The counters live in PostgreSQL, so a restart does not reset them, and a second worker sees the same counts. `RATE_LIMIT_ENABLED=false` turns every rule off.

| Rule | Route | Limit | Window | Setting |
|---|---|---|---|---|
| Login | `POST /api/v1/auth/login` | 5 requests | 1 minute | `RATE_LIMIT_LOGIN_PER_MINUTE` |
| Signup | `POST /api/v1/auth/signup` | 5 requests | 1 hour | `RATE_LIMIT_SIGNUP_PER_HOUR` |
| Upload | `POST /api/v1/books` | 30 requests | 1 hour | `RATE_LIMIT_UPLOAD_PER_HOUR` |
| Default | Every other route | 120 requests | 1 minute | `RATE_LIMIT_DEFAULT_PER_MINUTE` |

Every limited response carries these headers:

| Header | Meaning |
|---|---|
| `X-RateLimit-Limit` | The limit of the rule |
| `X-RateLimit-Remaining` | The requests left in the window |
| `X-RateLimit-Reset` | The seconds until the window ends |
| `Retry-After` | The same seconds value, on a `429` only |

A refused request returns `429` with this body:

```json
{ "message": "Too many requests. Try again later.", "code": "RATE_LIMITED" }
```

The middleware reads the client address from the socket. Set `TRUST_PROXY_HEADERS=true` only behind a proxy that overwrites `X-Real-IP` or `X-Forwarded-For`. Vercel is such a proxy.

## Errors

Every handled error returns one envelope, with the status code of the error:

```json
{ "message": "Book not found", "code": "BOOK_NOT_FOUND" }
```

An invalid request adds one entry for each bad field:

```json
{
  "message": "Invalid request data",
  "code": "INVALID_REQUEST",
  "errors": [ { "field": "password", "error": "String should have at least 8 characters" } ]
}
```

An unexpected error returns `500` without a stack trace, and it carries the request id:

```json
{ "message": "Internal server error", "code": "INTERNAL_ERROR", "request_id": "9f2c1d7e4b8a4c3f9e1d0b6a5c4e3f21" }
```

| Code | Status | Meaning |
|---|---|---|
| `INVALID_REQUEST` | 400 | A field failed validation |
| `USER_CREATION_FAILED` | 400 | The account could not be stored |
| `FILE_UPLOAD_FAILED` | 400 | The upload is not a usable PDF |
| `UNAUTHENTICATED` | 401 | The token is missing, invalid, or expired |
| `INVALID_CREDENTIALS` | 401 | The email and the password do not match |
| `FORBIDDEN` | 403 | The role or the account state does not allow the request |
| `USER_NOT_FOUND` | 404 | No such user |
| `BOOK_NOT_FOUND` | 404 | No such book |
| `DEPARTMENT_NOT_FOUND` | 404 | No such department |
| `FILE_NOT_FOUND` | 404 | The row exists but the stored file is gone |
| `DUPLICATE_FILE` | 409 | The same bytes are already stored |
| `USER_ALREADY_EXISTS` | 409 | The email is taken |
| `FILE_TOO_LARGE` | 413 | The upload is over `MAX_UPLOAD_MB` |
| `RATE_LIMITED` | 429 | The client passed a rate limit |
| `INTERNAL_ERROR` | 500 | An unhandled fault. The details stay in the log |

A `401` also sends `WWW-Authenticate: Bearer`.

**Request ids.** Every response carries `X-Request-ID`. A client value passes through when it matches `^[A-Za-z0-9._-]{1,64}$`. Any other value is replaced with a fresh uuid4 hex. The id appears on every log line of the request and in the body of a `500`, so a user report and a log line meet.

## Architecture

The code follows a domain-driven layout. Each resource owns its schemas, its rules, its persistence, and its routes.

```text
src/
├── core/
│   ├── config.py           # Settings, from the environment and .env
│   ├── exceptions.py       # The error classes and the handlers
│   ├── logging.py          # Text and JSON formatters
│   └── repository.py       # The adapter contracts (Protocol classes)
├── dependencies.py         # Service wiring and the current user
├── integrations/
│   ├── database.py         # Engine, session factory, session dependency
│   ├── file_storage.py     # Local PDF storage
│   ├── rate_limit.py       # PostgreSQL and memory counter stores
│   └── security.py         # Argon2 hasher and JWT issuer
├── middleware/
│   ├── body_size.py        # Upload size guard
│   ├── cors.py             # Allowed browser origins
│   ├── rate_limit.py       # Rules, headers, and the 429
│   └── request_id.py       # X-Request-ID
├── modules/
│   ├── auth/               # data, repository, service, router
│   ├── books/              # data, repository, service, router
│   ├── departments/        # data, repository, service, router
│   ├── health/             # data, service, router
│   └── users/              # data, repository, service, router
├── schema/
│   ├── base.py             # Declarative base and timestamps
│   └── models.py           # User, Book, Department, BookAccess
└── main.py                 # Application factory and router registration
```

`src/core/repository.py` holds the contracts that the services use: `FileStorageRepository`, `PasswordHasher`, `TokenIssuer`, and `RateLimitStore` with its `RateLimitHit` record. `src/integrations/` holds the adapters that implement them. A service never imports an adapter, so a test passes a fake through the same seam.

`src/middleware/` holds one file per concern, and `register_middleware()` attaches them in a fixed order. CORS is outermost, so a browser reads the headers of a `429` and of a `413`.

`src/dependencies.py` builds the services for the routers, resolves the current user from the bearer token, and enforces the admin role.

Data model and relationships:

![ERD: data models and relationships](./ERD.jpeg)

## Testing

```bash
export TEST_DATABASE_URL=postgresql+psycopg://buildlab:buildlab_dev_password@localhost:5432/buildlab_test
uv run pytest --cov=src --cov-report=term-missing
```

| Item | Value |
|---|---|
| Tests | 132 |
| Line coverage | 94 percent |
| CI threshold | 80 percent, enforced by `--cov-fail-under=80` |
| Test database | `TEST_DATABASE_URL`, a separate database |

The harness in `tests/conftest.py` does four things:

1. Stops at once when `TEST_DATABASE_URL` is missing. It never falls back to the development database.
2. Applies `alembic upgrade head` to the test database once per session, then truncates every table except `alembic_version`.
3. Binds each test to a transaction and rolls it back, so tests share a database and stay independent.
4. Points `STORAGE_DIR` at a temporary folder, turns rate limiting off, and gives the limiter a fake store with a clock that a test can move.

The suite covers the services on their own, the routes through `TestClient`, the error contract, the rate limit headers, the request id, the upload limit, and the PostgreSQL counter store.

## CI/CD

Five workflows run from `.github/workflows/`:

| Workflow | Trigger | What it does |
|---|---|---|
| CI (`ci.yml`) | Push to `main` or `week-*`, pull request, manual | Four jobs: **Lint** (ruff check, ruff format check, OpenAPI snapshot check), **Test** (pytest against a PostgreSQL 17 service, coverage gate, coverage artifact), **Docker** (build the image), and **CI gate** (fail when a needed job did not succeed) |
| Deploy (`deploy.yml`) | Push to `main`, manual | **Migrate** runs `alembic upgrade head` against production first, then **Deploy** builds and ships the Vercel deployment, then **Smoke** calls `/health` and the public book list |
| Rollback (`rollback.yml`) | Manual, with a confirmation input | Rolls production back to the previous Vercel deployment and checks `/health` |
| Release (`release.yml`) | Push of a `week-*` tag | Creates a GitHub release with generated notes. A re-run does nothing |
| Monitor (`monitor.yml`) | Every 15 minutes, manual | Calls `/health`. On a failure it opens one incident issue and adds a comment on a repeat. On recovery it closes the issue |

The deploy workflow needs these repository secrets and variables:

| Name | Kind | Use |
|---|---|---|
| `PRODUCTION_DATABASE_URL` | Secret | The Neon connection string for the migration job |
| `VERCEL_TOKEN` | Secret | Vercel API access |
| `VERCEL_ORG_ID` | Secret | Vercel team or user |
| `VERCEL_PROJECT_ID` | Secret | Vercel project |
| `PRODUCTION_URL` | Variable | The base URL for the smoke test and the monitor |
| `DEPLOY_ENABLED` | Variable | `true` turns the deployment on |

## Deployment

The target is Vercel for the application and Neon for PostgreSQL. **The deployment is prepared but it has not run yet.** No live URL exists. The repository holds `index.py` (the entrypoint that puts `src` on the import path and exposes `app`) and `vercel.json` (the FastAPI framework preset).

The pipeline works in this order: CI passes, the **Migrate** job applies `alembic upgrade head` to the production database, the **Deploy** job builds and ships the Vercel deployment, and the **Smoke** job calls `/health`.

Vercel limits that shape the design:

| Limit | Effect on this project |
|---|---|
| 4.5 MB request body | The application refuses an upload over 4 MB first, so the user gets a clear `413` instead of a platform error |
| No persistent disk | A file written to `STORAGE_DIR` does not survive a redeploy or a cold start. A production file store is a later change |
| Runtime Python may be below 3.14 | The runtime that Vercel selects can be older than the local version. Check the version in the Vercel project settings before the first deploy |

No `requirements.txt` is committed. The deploy step generates one for the runtime it finds, so the dependency list stays in `pyproject.toml` and `uv.lock`.

Environment variables for the production project:

| Name | Value |
|---|---|
| `DATABASE_URL` | The Neon connection string, with `?sslmode=require` |
| `SECRET_KEY` | At least 32 random characters, different from the development value |
| `ENVIRONMENT` | `production`. This also turns off `/docs`, `/redoc`, and `/openapi.json` |
| `CORS_ALLOW_ORIGINS` | The real frontend origins, comma separated. Never `*` |
| `TRUST_PROXY_HEADERS` | `true`, because Vercel sits in front of the function |
| `STORAGE_DIR` | A writable path, if the platform offers one |
| `RATE_LIMIT_BACKEND` | `postgres`, so the limits survive a restart |

## Known limitations

| Limitation | Detail |
|---|---|
| No refresh tokens | The access token is the only token. A client logs in again after it expires |
| No admin management endpoint | The seed script creates the admin. A promotion needs a database change |
| PDFs up to 4 MB | `MAX_UPLOAD_MB` defaults to 4, below the 4.5 MB Vercel body limit |
| One uploaded file per book | A new edition means a new book row. The book holds one `file_path` |
| No email verification | A signup is active at once, and any address is accepted |
| No malware scan | The API checks the `%PDF-` signature only. It does not inspect the content |
| In-memory rate limit only for tests | `RATE_LIMIT_BACKEND=memory` suits tests and one worker. Production uses the PostgreSQL store |

## Roadmap

| Week | Scope | State |
|---|---|---|
| Week 1 | Data model, migrations, books CRUD, search, filters, pagination, seed data | Done |
| Week 2 | Signup, login, JWT, role checks, guarded file delivery, access history, CORS | Done |
| Week 3 | Tests, rate limits, request ids, logs, upload limit, health route, CI, Docker, Vercel entrypoint | Done |
| Next | The first production deployment on Vercel and Neon, then a file store that survives a redeploy | Planned |

The full history is in the [changelog](./CHANGELOG.md).

## Decisions

| # | Decision | Outcome |
|---|---|---|
| 1 | Distinctiveness | File-hash duplicate rule (DB `UNIQUE` gives `409`) and department-scoped browsing |
| 2 | File-heavy risk | Store real PDFs locally, check the PDF signature, cap the size at 4 MB |
| 3 | Unique email | `users.email` is `UNIQUE`. Signup returns `409` for a duplicate |
| 4 | Token contents | Only `sub`, `iat`, `exp`, and `iss`. The role comes from the database, not the token |
| 5 | File delivery | One authenticated route streams the PDF and writes the history row. No public static mount |
| 6 | Partial updates | `PATCH` for books and profiles. `PUT` implied a full replace, which the handlers did not do |
| 7 | `file_url` | Derived from the book id in the response. One stored location, `file_path` |
| 8 | Rate limiting in PostgreSQL | A fixed window with one atomic upsert per hit. A restart and a second worker keep the same counts. The memory store stays for tests |
| 9 | Request ids and JSON logs | Every request gets an id, and production writes one JSON object per line with that id. A user report and a log line meet without a search |
| 10 | The 4 MB cap | `MAX_UPLOAD_MB` sits below the 4.5 MB Vercel body limit, so the API answers `413` before the platform rejects the request |
| 11 | Health route | `GET /health` runs `SELECT 1` and reports the database. The deploy smoke test and the monitor use it, so a broken database fails a deploy instead of a user |

## Contributing and License

Read [CONTRIBUTING.md](./CONTRIBUTING.md) for the local setup, the test command, and the commit rule. Report a vulnerability through [SECURITY.md](./SECURITY.md), not a public issue.

This project uses the MIT license. See [LICENSE](./LICENSE).
