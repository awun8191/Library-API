# Contributing to the BuildLab Library API

Thank you for your interest in this project. This page holds the steps to set
up the project, to run the checks, and to send a change.

## Local setup

You need Python 3.14, [uv](https://docs.astral.sh/uv/), and Docker.

```bash
git clone https://github.com/awun8191/Library-API.git
cd Library-API
uv sync
cp .env.example .env
```

Start PostgreSQL with Docker:

```bash
docker compose up -d db
```

The Compose service listens on port 5432. If another process uses 5432, set
`POSTGRES_PORT` in `.env` and change the port in `DATABASE_URL` to match.

Apply the migrations and load the development data:

```bash
uv run alembic upgrade head
uv run python scripts/seed.py
```

The seed script prints the development logins.

## Tests

The tests use a separate PostgreSQL database. They apply the migrations to it
and truncate the tables. They never touch the development database.

Set `TEST_DATABASE_URL` in `.env`:

```env
TEST_DATABASE_URL=postgresql+psycopg://buildlab:buildlab_dev_password@localhost:5432/buildlab_test
```

Create that database once:

```bash
docker compose exec db createdb -U buildlab buildlab_test
```

Run the suite with the environment variable exported, because the harness stops
when the variable is missing:

```bash
export TEST_DATABASE_URL=postgresql+psycopg://buildlab:buildlab_dev_password@localhost:5432/buildlab_test
uv run pytest --cov=src --cov-report=term-missing
```

## Lint and format

```bash
uv run ruff check .
uv run ruff format .
```

Run `uv run ruff format` before you commit. Continuous integration fails on an
unformatted file.

## OpenAPI snapshot

The repository stores the API schema in `openapi.json`. Regenerate it after a
change to a route, a response model, or a description:

```bash
uv run python scripts/export_openapi.py
```

Commit the result with the change. Continuous integration fails when the file
does not match the code.

## Commit messages

Use the Conventional Commits format. The project uses these types: `feat`,
`fix`, `docs`, `test`, `build`, `ci`, `chore`, and `refactor`.

```text
feat(rate-limit): add a database-backed fixed window limiter
docs(readme): add the deployment section
```

Write the subject in the imperative mood. Keep it under 72 characters. Add a
body when the reason for the change is not clear from the subject.

## Pull request checklist

- [ ] The branch starts from the current `main`.
- [ ] The change does one thing.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run ruff format --check .` passes.
- [ ] `uv run pytest` passes with `TEST_DATABASE_URL` exported.
- [ ] The change adds or updates a test when it changes behavior.
- [ ] `uv run python scripts/export_openapi.py` gives no diff.
- [ ] The change updates the documentation when a route, a setting, or a rule changes.
- [ ] The commit messages follow the Conventional Commits format.

Open the pull request against `main`. Describe the problem and the change. The
CI gate must pass before a review starts.
