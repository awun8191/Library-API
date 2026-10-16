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
| Duplicate files | Hash the file and insert directly. `file_hash` is **UNIQUE**, so the database rejects duplicates and the API returns **409 Conflict** thus allowing us to bypass indexing the hashes and keeping the logic simpler |
| Search | Simple text search on book name (indexed) |
| Filtering | By department |
| Pagination | Cursor-based, on the book listing (`GET /books`) and the access-history listing (`GET /users/me/access-history`) |
| File storage | Real files stored; the repo ships only dummy PDFs, including deliberate duplicates to demo the 409 |
| Identity | `/users/me` is resolved from the auth token — no user IDs in URLs |
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

Keep resource business rules in services and persistence details in repositories. The `auth` module owns signup and login; authenticated-user resolution and authorization dependencies are shared through `dependencies.py`. Each `router.py` defines the resource's FastAPI routes; the application entrypoint (`src/main.py`) will include each resource router when the API is implemented. Integrations implement infrastructure-facing adapters; configuration and `dependencies.py` provide settings and wire implementations into the application. Resource services should depend on repository contracts rather than framework or database details, keeping the domain logic isolated and testable.

## API endpoints

Status codes: **200** OK · **201** Created · **204** No Content · **400** Bad request · **401** Unauthenticated · **403** Forbidden (admin only) · **404** Not found · **409** Conflict (duplicate file hash)

**Auth**

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| POST | `/auth/signup` | Public | Create an account | 201 · 400 |
| POST | `/auth/login` | Public | Get an auth token | 200 · 401 |

**Users**

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| GET | `/users/me` | Authenticated | Current user profile | 200 · 401 |
| PUT | `/users/me` | Authenticated | Update own profile | 200 · 400 · 401 |
| GET | `/users/me/access-history` | Authenticated | Books the current user has opened — cursor-based pagination | 200 · 400 · 401 |

**Books**

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| POST | `/books` | Admin | Upload a book (PDF) | 201 · 400 · 401 · 403 · 409 |
| GET | `/books` | Authenticated | List — search, department filter, cursor-based pagination | 200 · 400 · 401 |
| GET | `/books/{id}` | Authenticated | One book | 200 · 401 · 404 |
| PUT | `/books/{id}` | Admin | Update a book | 200 · 400 · 401 · 403 · 404 |
| DELETE | `/books/{id}` | Admin | Delete a book | 204 · 401 · 403 · 404 |
| POST | `/books/{id}/access` | Authenticated | Record that the user opened the book | 201 · 401 · 404 |

**Departments**

| Method | Path | Access | Purpose | Status codes |
|---|---|---|---|---|
| GET | `/departments` | Authenticated | List departments (for filtering) | 200 · 401 |

## Running and testing

Start the PostgreSQL development database with Docker Compose:

```bash
cp .env.example .env
docker compose up -d db
```

The database is available on `localhost:5432` by default. Compose persists its data in the `postgres_data` volume; stop the service with `docker compose down`. To discard the database and its data, run `docker compose down -v`. The credentials in `.env.example` are for local development only. The API is not yet included as a Compose service.

| Item | Detail |
|---|---|
| Services | Docker Compose: PostgreSQL development database |
| Config | `.env.example` holds dummy dev values; no real `.env` is committed |
| Tests | Upload success, duplicate → 409, plus the 400 / 401 / 403 / 404 cases |
| Test PDFs | Generated in a pytest fixture (proposed, not confirmed) |
| Rate limiting | Proposed, not confirmed: in-memory `slowapi` on auth routes only |
| Caching | None — no Redis |

## Open decisions

| # | Decision | Notes |
|---|---|---|
| 1 | Distinctiveness | Strongest options: department-scoped visibility and the file-hash duplicate rule |
| 2 | File-heavy risk | Keep real storage with strict limits, or store a link/checksum instead |
| 3 | Unique email | Suggested, not yet confirmed |
| 4 | Week 1 remaining | One-pager, work plan, ERD drawing, request/response bodies, repo |
