# BuildLab Library: School Digital Library API

## PROBLEM DEFINITION
A digital library for a school where admins upload course materials (PDFs), students search, filter by department, course code and open them.

| | |
|---|---|
| **Programme** | BuildLab Stage 1, Backend Development |
| **Idea** | School digital library: admins upload course materials, students browse them |
| **Goal** | A simple well designed API |
| **Stack** | FastAPI · Pydantic (response models) · PostgreSQL · SQLAlchemy (ORM) · Argon2 · JWT · Docker Compose |

## Core behaviour

| Area | Rule |
|---|---|
| Accounts | Signup creates a student account. Login returns a signed JWT access token |
| Uploads | Admin only |
| Duplicate files | SHA-256 hash the file and insert directly. `file_hash` is **UNIQUE**, so the database rejects duplicates and the API returns **409 Conflict** |
| File delivery | `GET /books/{id}/file` requires a valid token. It streams the PDF and records the access in one step |
| Search | Simple text search on book name. Wildcard characters are escaped |
| Filtering | By department and by course code |
| Pagination | Cursor-based on the book listing and on the access history |
| Storage | Real PDFs on local disk (`Storage/`, git-ignored). The API checks the `%PDF-` signature |
| Identity | The token subject is the user id. `/users/me` reads the user from the database on each request |
| Browser access | CORS origins come from `CORS_ALLOW_ORIGINS` |
| Columns | snake_case |

## Data models

| Model | Purpose | Fields |
|---|---|---|
| **User** | Account holder (admin or student) | id, first_name, last_name, email, password_hash (Argon2), role (`admin`\|`user`, default `user`), is_active, department_id (FK, nullable), created_at, updated_at |
| **Book** | An uploaded course material | id, name, course_name, topic, course_code, file_hash (unique), file_path, uploaded_by (FK User), department_id (FK Department), created_at, updated_at |
| **Department** | Groups users and books | id, name, created_at, updated_at |
| **BookAccess** | History of books a user opens | id, user_id (FK), book_id (FK), accessed_at, created_at, updated_at |

**UserResponse**: the only user fields ever returned: `id, first_name, last_name, email, role, is_active, department_id`. The password hash never leaves the database.

**file_url is derived, not stored.** `BookResponse` and the history items return `/api/v1/books/{id}/file`, and the route builds this link from the book id. The database stores only `file_path`.

## Relationships

![ERD: data models and relationships](./ERD.jpeg)

| From → To | Cardinality | Notes |
|---|---|---|
| User → Book | one-to-many | Upload and delete only |
| User → Department | many-to-one | Many users share one department |
| User → BookAccess | one-to-many | Reading history |
| Book → User | many-to-one | The uploader |
| Book → Department | many-to-one | Many books share one department |
| Book → BookAccess | one-to-many | Open events |
| BookAccess → User | many-to-one | |
| BookAccess → Book | many-to-one | |
| Department → User | one-to-many | |
| Department → Book | one-to-many | |

Reading a book is not a stored relationship. Opening the file writes a `BookAccess` row.

## Architecture and source layout

The application uses a domain-driven clean architecture organized around resources. Each resource is a module under `src/modules/` and keeps its schemas, business rules, persistence concerns, and API routes in separate files:

```text
src/
├── core/                   # Settings, exceptions, and adapter contracts
├── dependencies.py         # Shared dependency wiring
├── integrations/           # Database, file storage, password hashing, and tokens
├── middleware/             # CORS and other application middleware
└── modules/                # Resource-oriented application modules
    ├── auth/
    │   ├── data.py          # Signup, login, and token schemas
    │   ├── repository.py    # Account lookup and creation
    │   ├── router.py        # Signup and login routes
    │   └── service.py       # Registration and login use cases
    ├── books/               # Book CRUD, file delivery, and access history
    ├── departments/         # Department listing
    └── users/               # Profile and reading history
```

Resource services depend on the contracts in `src/core/repository.py`. `src/integrations/` holds the adapters: `database.py`, `file_storage.py`, and `security.py`. `src/middleware/` holds the middleware and `register_middleware()` attaches it. `src/dependencies.py` builds the services for the routers and resolves the current user.

## API endpoints

All routes are served under the `/api/v1` prefix. Interactive docs: `/docs` (Swagger) and `/redoc`. Both are disabled in production, including `/openapi.json`.

Status codes: **200** OK · **201** Created · **204** No Content · **400** Bad request · **401** Unauthenticated · **403** Forbidden · **404** Not found · **409** Conflict

**Auth**

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| POST | `/api/v1/auth/signup` | Public | Create a student account | 201 · 400 · 404 · 409 |
| POST | `/api/v1/auth/login` | Public | Get an access token | 200 · 401 · 403 |

**Users**

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| GET | `/api/v1/users/me` | Authenticated | Current user profile | 200 · 401 · 403 · 404 |
| PATCH | `/api/v1/users/me` | Authenticated | Update own profile | 200 · 400 · 401 · 403 · 404 |
| GET | `/api/v1/users/me/access-history` | Authenticated | Books the current user opened, cursor paginated | 200 · 400 · 401 · 403 |

**Books**

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| POST | `/api/v1/books` | Admin | Upload a book (PDF, multipart form) | 201 · 400 · 401 · 403 · 404 · 409 |
| GET | `/api/v1/books` | Public | List with search, filters, and cursor pagination | 200 · 400 |
| GET | `/api/v1/books/{id}` | Public | One book | 200 · 404 |
| GET | `/api/v1/books/{id}/file` | Authenticated | Stream the PDF and record the access | 200 · 401 · 403 · 404 |
| PATCH | `/api/v1/books/{id}` | Admin | Update a book | 200 · 400 · 401 · 403 · 404 |
| DELETE | `/api/v1/books/{id}` | Admin | Delete a book and its file | 204 · 401 · 403 · 404 |

**Departments**

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| GET | `/api/v1/departments` | Public | List departments for filtering | 200 |

## Authentication

Signup and login return a JSON Web Token. Send it as `Authorization: Bearer <token>`. The token holds the user id in `sub`, and it expires after `ACCESS_TOKEN_EXPIRE_MINUTES`.

The API reads the user from the database on each request. A role change or a deactivated account takes effect at once, and the token cannot outlive it.

**Signup**

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Ada","last_name":"Obi","email":"ada@school.edu","password":"strong-password"}'
```

`201 Created`
```json
{
  "id": 3,
  "first_name": "Ada",
  "last_name": "Obi",
  "email": "ada@school.edu",
  "role": "user",
  "is_active": true,
  "department_id": null
}
```

A duplicate email returns `409` with `{"message": "An account with this email already exists", "code": "USER_ALREADY_EXISTS"}`. A password shorter than 8 characters returns `400`.

**Login**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@school.edu","password":"dev-password-123"}'
```

`200 OK`
```json
{ "access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer", "expires_in": 3600 }
```

## Request and response examples

Use the token from login:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@school.edu","password":"dev-password-123"}' | jq -r .access_token)
```

**Upload a book** — `POST /api/v1/books` (multipart/form-data)

```bash
curl -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer $TOKEN" \
  -F name="Intro to Algorithms Notes" -F course_name="Data Structures" \
  -F topic="Sorting" -F course_code="CSC201" -F department_id=1 \
  -F file=@./csc201-sorting.pdf
```

`201 Created`
```json
{
  "id": 4,
  "name": "Intro to Algorithms Notes",
  "course_name": "Data Structures",
  "topic": "Sorting",
  "course_code": "CSC201",
  "department_id": 1,
  "created_at": "2026-10-24T15:00:00Z",
  "updated_at": "2026-10-24T15:00:00Z",
  "file_url": "/api/v1/books/4/file"
}
```

Uploading the same file again returns `409` with the name of the book that already holds it. A non-PDF returns `400`. An unknown `department_id` returns `404`.

**List and search** — `GET /api/v1/books?q=algorithms&department_id=1&course_code=CSC201&limit=10`

`200 OK`
```json
{
  "items": [
    { "id": 4, "name": "Intro to Algorithms Notes", "course_code": "CSC201", "department_id": 1, "file_url": "/api/v1/books/4/file" }
  ],
  "next_cursor": null,
  "has_more": false
}
```

Pass `next_cursor` as `cursor` to fetch the next page. Search terms are matched literally, so `%` and `_` do not act as wildcards.

**Download a book** — `GET /api/v1/books/4/file`

```bash
curl -L -H "Authorization: Bearer $TOKEN" -o book.pdf http://localhost:8000/api/v1/books/4/file
```

The response is the PDF stream. The same request writes one `BookAccess` row for the current user. Response headers include `Cache-Control: private, no-store`.

**Update a book** — `PATCH /api/v1/books/4` (all fields optional)

```json
{ "topic": "Sorting and Searching", "course_code": "CSC202" }
```

**Delete a book** — `DELETE /api/v1/books/4` returns `204 No Content` and removes the stored PDF.

**Reading history** — `GET /api/v1/users/me/access-history?limit=10` (newest first)

`200 OK`
```json
{
  "items": [
    {
      "id": 5,
      "book_id": 4,
      "book_name": "Intro to Algorithms Notes",
      "course_code": "CSC201",
      "accessed_at": "2026-10-24T15:05:00Z",
      "file_url": "/api/v1/books/4/file"
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```

**Departments** — `GET /api/v1/departments`

```json
[ { "id": 1, "name": "Computer Science" } ]
```

**Error shape**: every handled error returns `{"message": "...", "code": "..."}` with the matching status code. A `401` also sends `WWW-Authenticate: Bearer`. Invalid input returns `400` with a `errors` list of field names and messages.

## Setup and run

You need **Python 3.14**, **[uv](https://docs.astral.sh/uv/)**, and **PostgreSQL**, either through Docker or installed on your machine.

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

**3. Create the tables and dummy data**

```bash
uv run alembic upgrade head      # tables and the development admin
uv run python scripts/seed.py    # 3 departments, 2 accounts, 3 dummy PDFs, history
```

The seed script prints the development logins: `admin@school.edu` and `student@school.edu`, password `dev-password-123`. Both passwords are Argon2 hashes.

**4. Run the API** (from the repo root, so `.env` is found)

```bash
uv run uvicorn main:app --app-dir src --reload
```

Open **http://localhost:8000/docs** to try every endpoint.

**Troubleshooting**
- `connection refused`: PostgreSQL is not running, or the port in `DATABASE_URL` is wrong.
- `password authentication failed`: the user or password in `DATABASE_URL` does not match your database.
- `database_url Field required`: there is no `.env` in the folder you ran the command from. Run from the repo root.
- `secret_key String should have at least 32 characters`: set `SECRET_KEY` in `.env` to 32 characters or more.

**Notes**
- Invalid input returns `400` with `{"message": "Invalid request data", "errors": [...]}`. Unexpected errors return `500` without a stack trace.
- Uploaded PDFs are saved in `Storage/` (git-ignored). Only `GET /books/{id}/file` serves them.
- `docker compose down -v` wipes the Docker database. Afterwards, rerun step 3.

| Item | Detail |
|---|---|
| Migrations | Alembic: initial schema, development seed, Week 2 auth changes |
| Dummy data | `scripts/seed.py` is safe to run repeatedly |
| Config | `.env.example` holds dummy dev values. No real `.env` is committed |
| Tests | Week 3 |

## CORS

`CORS_ALLOW_ORIGINS` holds a comma separated list of browser origins. The default `*` is for development only. Set the real frontend origins in production.

```env
CORS_ALLOW_ORIGINS=http://localhost:5173,https://library.school.edu
```

The API uses bearer tokens, not cookies, so `allow_credentials` stays false. The `WWW-Authenticate` header is exposed so the client can read it.

## Week 2 status

| Area | Status |
|---|---|
| Signup and login on PostgreSQL | Done |
| Argon2 password hashing | Done |
| JWT issuing and verification | Done |
| Real role checks from the database | Done |
| Inactive accounts rejected | Done |
| PDF delivery behind authentication | Done |
| Access history written when the file is served | Done |
| Course code filter, literal search, PATCH semantics | Done |
| CORS through `src/middleware/` | Done |
| Error codes on every handled error | Done |
| Tests, deployment, final docs | Week 3 |

## Decisions

| # | Decision | Outcome |
|---|---|---|
| 1 | Distinctiveness | File-hash duplicate rule (DB `UNIQUE` → 409) and department-scoped browsing |
| 2 | File-heavy risk | Store real PDFs locally, PDF signature check, size limits to be added later |
| 3 | Unique email | `users.email` is `UNIQUE`. Signup returns 409 for a duplicate |
| 4 | Token contents | Only `sub`, `iat`, `exp`, and `iss`. The role comes from the database, not the token |
| 5 | File delivery | One authenticated route streams the PDF and writes the history row. No public static mount |
| 6 | Partial updates | `PATCH` for books and profiles. `PUT` implied a full replace, which the handlers did not do |
| 7 | `file_url` | Derived from the book id in the response. One stored location, `file_path` |
