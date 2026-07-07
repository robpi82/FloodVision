"""Pytest configuration: make the project root importable.

The application is imported as ``src.<module>`` but is not installed as
a package, so the project root must be on ``sys.path`` for test runs
from any working directory. This is the entire purpose of this file --
shared fixtures should only move here once several test modules
actually need them.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
