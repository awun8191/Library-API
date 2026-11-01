"""Vercel entrypoint for the Library API.

Vercel looks for a module level object named ``app`` at the repository root.
The application lives in ``src``, so this module puts that folder on the
import path first.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

# The path insert above must run before this import. That is why E402 is off here.
from main import app  # noqa: E402

__all__ = ["app"]
