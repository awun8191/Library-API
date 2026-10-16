# BuildLab Library — School Digital Library API

## PROBLEM DEFINITION
A digital library for a school where admins upload course materials (PDFs), students search, filter by department, course code and open them.

| | |
|---|---|
| **Programme** | BuildLab Stage 1 — Backend Development |
| **Idea** | School digital library: admins upload course materials, students browse them |
| **Goal** | A simple well designed API |
| **Stack** | FastAPI · Pydantic (response models) · PostgreSQL · SQLAlchemy (ORM) · Argon2 · Docker Compose |

## Core behaviour

| Area | Rule |
|---|---|
| Uploads | Admin only |
| Duplicate files | SHA-256 hash the file and insert directly. `file_hash` is **UNIQUE**, so the database rejects duplicates and the API returns **409 Conflict** thus allowing us to bypass indexing the hashes and keeping the logic simpler |
| Search | Simple text search on book name (indexed) |
| Filtering | By department |
| Pagination | Cursor-based, on the book listing (`GET /books`) and the access-history listing (`GET /users/me/access-history`) |
| File storage | Real PDFs stored on local disk (`Storage/`, git-ignored) and served at `/static/books`; dummy PDFs only — upload the same file twice to demo the 409 |
| Identity | `/api/v1/users/me` is resolved from the auth token — no user IDs in URLs |
| Columns | snake_case |

## Data models

| Model | Purpose | Fields |
|---|---|---|
| **User** | Account holder (admin or student) | id, first_name, last_name, email, password_hash (Argon2), role (`admin`\|`user`, default `user`), is_active (default true), department_id (FK, nullable), created_at, updated_at |
| **Book** | An uploaded course material | id, name, course_name, topic, course_code, file_hash (unique), file_url (URL to the stored file), file_path (resource path — lets the URL be reconstructed), uploaded_by (FK User), department_id (FK Department), created_at, updated_at |
| **Department** | Groups users and books | id, name, created_at, updated_at |
| **BookAccess** | History of books a user opens | id, user_id (FK), book_id (FK), accessed_at, created_at, updated_at |

**UserResponse** — the only user fields ever returned: `id, first_name, last_name, email, role, is_active, department_id`.

## Relationships

![ERD — data models and relationships](./ERD.jpeg)

| From → To | Cardinality | Notes |
|---|---|---|
| User → Book | one-to-many | Upload and delete only |
| User → Department | **many-to-one** | Many users share one department |
| User → BookAccess | one-to-many | Reading history |
| Book → User | many-to-one | The uploader |
| Book → Department | **many-to-one** | Many books share one department |
| Book → BookAccess | one-to-many | Open events |
| BookAccess → User | many-to-one | |
| BookAccess → Book | many-to-one | |
| Department → User | one-to-many | |
| Department → Book | one-to-many | |

Reading a book is a plain query — not a modeled relationship. BookAccess reaches Department through Book.

## Architecture and source layout

The application uses a domain-driven clean architecture organized around resources. Each resource is a module under `src/modules/` and keeps its data models/schemas, business rules, persistence concerns, and API routes in separate files:

```text
src/
├── core/                   # Application settings and configuration
├── dependencies.py         # Shared dependency wiring
├── integrations/           # Adapters to databases and external services
└── modules/                # Resource-oriented application modules
    ├── auth/
    │   ├── data.py          # Authentication request and response schemas
    │   ├── repository.py    # Persistence interfaces and queries
    │   ├── router.py        # Signup and login routes
    │   └── service.py       # Authentication use cases
    ├── books/
    │   ├── data.py          # Book and access history data models and schemas
    │   ├── repository.py    # Book and access persistence interfaces and queries
    │   ├── router.py        # Routes for book CRUD, access recording, and history
    │   └── service.py       # Book and access business rules and use cases
    ├── departments/         # Same data/repository/service/router layout
    └── users/               # Same data/repository/service/router layout
```

Keep resource business rules in services and persistence details in repositories. The `auth` module owns signup and login; authenticated-user resolution and authorization dependencies are shared through `dependencies.py`. Each `router.py` defines the resource's FastAPI routes; the application entrypoint (`src/main.py`) builds the app with `initialize_app()`, registers every resource router, and mounts uploaded PDFs at `/static/books`. Integrations implement infrastructure-facing adapters; configuration and `dependencies.py` provide settings and wire implementations into the application. Resource services should depend on repository contracts rather than framework or database details, keeping the domain logic isolated and testable.

## API endpoints

All routes are served under the `/api/v1` prefix. Interactive docs: `/docs` (Swagger) and `/redoc`.

Status codes: **200** OK · **201** Created · **204** No Content · **400** Bad request · **401** Unauthenticated · **403** Forbidden (admin only) · **404** Not found · **409** Conflict (duplicate file hash)

**Auth**

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| POST | `/api/v1/auth/signup` | Public | Create an account | 201 · 400 |
| POST | `/api/v1/auth/login` | Public | Get an auth token | 200 · 401 |

**Users**

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| GET | `/api/v1/users/me` | Authenticated | Current user profile | 200 · 401 · 404 |
| PUT | `/api/v1/users/me` | Authenticated | Update own profile | 200 · 400 · 401 · 404 |
| GET | `/api/v1/users/me/access-history` | Authenticated | Books the current user has opened — cursor-based pagination | 200 · 400 · 401 |

**Books**

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| POST | `/api/v1/books` | Admin | Upload a book (PDF, multipart form) | 201 · 400 · 401 · 403 · 404 · 409 |
| GET | `/api/v1/books` | Authenticated | List — search, department filter, cursor-based pagination | 200 · 400 · 401 |
| GET | `/api/v1/books/{id}` | Authenticated | One book | 200 · 401 · 404 |
| PUT | `/api/v1/books/{id}` | Admin | Update a book | 200 · 400 · 401 · 403 · 404 |
| DELETE | `/api/v1/books/{id}` | Admin | Delete a book | 204 · 401 · 403 · 404 |
| POST | `/api/v1/books/{id}/access` | Authenticated | Record that the user opened the book | 201 · 401 · 404 |

**Departments**

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| GET | `/api/v1/departments` | Authenticated | List departments (for filtering) | 200 · 401 |

## Request / response examples

The Week 1 build uses a development identity: any `Authorization: Bearer <token>` header resolves to the seeded admin user (id `1`). Real signup, login and JWT verification arrive in Week 2.

**Upload a book** — `POST /api/v1/books` (multipart/form-data)

```bash
curl -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer dev" \
  -F name="Intro to Algorithms Notes" -F course_name="Data Structures" \
  -F topic="Sorting" -F course_code="CSC201" -F department_id=1 \
  -F file=@./csc201-sorting.pdf
```

`201 Created`
```json
{
  "id": 1,
  "name": "Intro to Algorithms Notes",
  "course_name": "Data Structures",
  "topic": "Sorting",
  "course_code": "CSC201",
  "file_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "file_url": "/static/books/3f2a9c1e7b4d4e0f9a6b2c8d1e5f7a90.pdf",
  "file_path": "Storage/3f2a9c1e7b4d4e0f9a6b2c8d1e5f7a90.pdf",
  "uploaded_by": 1,
  "department_id": 1,
  "created_at": "2026-10-16T15:00:00Z",
  "updated_at": "2026-10-16T15:00:00Z"
}
```

Uploading the same file again → `409 Conflict` (duplicate `file_hash`). A non-PDF or missing field → `400`. An unknown `department_id` → `404`.

**List / search books** — `GET /api/v1/books?q=algorithms&department_id=1&limit=10&cursor=0`

`200 OK`
```json
{
  "items": [ { "id": 1, "name": "Intro to Algorithms Notes", "course_code": "CSC201", "department_id": 1, "...": "..." } ],
  "next_cursor": null,
  "has_more": false
}
```
Pass the returned `next_cursor` as `cursor` to fetch the next page.

**Update a book** — `PUT /api/v1/books/1` (all fields optional)

```json
{ "topic": "Sorting and Searching", "course_code": "CSC202" }
```
`200 OK` with the updated book · `404` if the book or department does not exist.

**Delete a book** — `DELETE /api/v1/books/1` → `204 No Content` (the stored PDF is removed too).

**Record that a book was opened** — `POST /api/v1/books/1/access`

`201 Created`
```json
{ "id": 1, "user_id": 1, "book_id": 1, "accessed_at": "2026-10-16T15:05:00Z" }
```

**Reading history** — `GET /api/v1/users/me/access-history?limit=10` (newest first)

`200 OK`
```json
{
  "items": [ { "id": 1, "book_id": 1, "book_name": "Intro to Algorithms Notes", "course_code": "CSC201", "accessed_at": "2026-10-16T15:05:00Z" } ],
  "next_cursor": null,
  "has_more": false
}
```

**Departments** — `GET /api/v1/departments`

`200 OK`
```json
[ { "id": 1, "name": "Computer Science" } ]
```

**Error shape** — every handled error returns `{"message": "..."}` with the matching status code, e.g. `404` for a missing book.

## Setup and run

You need **Python 3.13+**, **[uv](https://docs.astral.sh/uv/)**, and **PostgreSQL**, either through Docker or installed on your machine.

**1. Clone and install**

```bash
git clone https://github.com/awun8191/Library-API.git
cd Library-API
uv sync
cp .env.example .env
```

**2. Connect PostgreSQL** (pick one)

*Option A: Docker (easiest).* The values in `.env.example` already match the Compose database.

```bash
docker compose up -d db
```

*Option B: PostgreSQL already on your machine.* Create a user and database, then point `DATABASE_URL` in `.env` at them:

```bash
psql -U postgres -c "CREATE USER buildlab WITH PASSWORD 'buildlab_dev_password';"
psql -U postgres -c "CREATE DATABASE buildlab OWNER buildlab;"
```

```env
DATABASE_URL=postgresql+psycopg://buildlab:buildlab_dev_password@localhost:5432/buildlab
```

If you'd rather use an existing user or database, change the user, password, port or database name in that URL to match.

**3. Create the tables and dummy data**

```bash
uv run alembic upgrade head      # tables + dev admin (id 1)
uv run python scripts/seed.py    # 3 departments, a student, 3 dummy PDFs, reading history
```

**4. Run the API** (from the repo root, so `.env` is found)

```bash
uv run uvicorn main:app --app-dir src --reload
```

Open **http://localhost:8000/docs** to try every endpoint. For Week 1, send any bearer token (for example `Authorization: Bearer dev`). It resolves to the seeded admin.

**Troubleshooting**
- `connection refused`: PostgreSQL isn't running, or the port in `DATABASE_URL` is wrong.
- `password authentication failed`: the user or password in `DATABASE_URL` doesn't match your database.
- `database_url Field required`: there's no `.env` in the folder you ran the command from. Run from the repo root.

**Notes**
- Invalid input returns `400` with `{"message": "Invalid request data", "errors": [...]}`, and unexpected errors return `500` without a stack trace.
- Uploaded PDFs are saved in `Storage/` (git-ignored) and served at `/static/books`.
- `docker compose down -v` wipes the Docker database. Afterwards, rerun step 3.

| Item | Detail |
|---|---|
| Migrations | Alembic: initial schema + dev admin seed |
| Dummy data | `scripts/seed.py` is safe to run repeatedly |
| Config | `.env.example` holds dummy dev values; no real `.env` is committed |
| Tests | Planned for Week 3 |

## Week 1 status

| Area | Status |
|---|---|
| Problem definition, data models, ERD | Done |
| Alembic migrations + dummy seed data | Done |
| Invalid input → 400, no stack traces | Done |
| Books CRUD on PostgreSQL (upload, list, get, update, delete) | Done |
| Search, department filter, cursor pagination | Done |
| Duplicate file → 409, missing record → 404 | Done |
| Access recording + reading history | Done |
| Departments list, users `GET/PUT /me` on PostgreSQL | Done |
| Signup, login, JWT, real role checks | Week 2 (Week 1 uses a dev admin identity) |
| Tests, deployment, final docs | Week 3 |

## Decisions

| # | Decision | Outcome |
|---|---|---|
| 1 | Distinctiveness | File-hash duplicate rule (DB `UNIQUE` → 409) and department-scoped browsing |
| 2 | File-heavy risk | Store real PDFs locally, PDF-only, dummy files only; size limits to be added in Week 2 |
| 3 | Unique email | Confirmed: `users.email` is `UNIQUE` |
| 4 | Auth scope for Week 1 | Deferred to Week 2; a development admin identity is used so admin routes can be exercised |
