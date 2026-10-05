"""Shared pytest configuration for the backend test suite.

Adds the backend directory to sys.path so that "from app.services import ..."
works no matter which directory pytest is launched from.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
