"""Write the OpenAPI schema of the API to openapi.json.

The script needs no database and no .env file. It sets safe defaults in the
environment before it imports the application, because the settings read the
environment at import time. It writes the file relative to the repository root,
so the command works from any folder.

Run from the repository root after a change to a route or a schema:

    uv run python scripts/export_openapi.py
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# The defaults only feed the settings object. No connection is opened here.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://buildlab:buildlab_dev_password@localhost:5432/buildlab",
)
os.environ.setdefault("SECRET_KEY", "openapi-snapshot-secret-key-for-the-buildlab-api")
# The schema route exists only in development, so the snapshot needs that mode.
os.environ.setdefault("ENVIRONMENT", "development")

from main import app  # noqa: E402

TARGET = ROOT / "openapi.json"


def main() -> None:
    """Write the schema and report the number of lines."""
    schema = app.openapi()
    TARGET.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {TARGET} with {len(TARGET.read_text(encoding='utf-8').splitlines())} lines.")


if __name__ == "__main__":
    main()
