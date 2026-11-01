## What does this change do?

<!-- One paragraph. Link the issue when one exists. -->

## Why is the change needed?

<!-- The problem, not the patch. -->

## Checklist

- [ ] The change does one thing.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run ruff format --check .` passes.
- [ ] `uv run pytest` passes with `TEST_DATABASE_URL` exported.
- [ ] A behavior change comes with a test.
- [ ] `uv run python scripts/export_openapi.py` gives no diff.
- [ ] The documentation covers a new route, setting, or rule.
- [ ] The commit messages follow the Conventional Commits format.
- [ ] The change has no secret, token, or database connection string.

## Notes for the reviewer

<!-- Anything that is easy to miss: a migration, a setting, a deployment effect. -->
