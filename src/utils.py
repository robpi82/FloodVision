"""Reusable, project-agnostic helper functions for FloodVision.

Rules for this module:

* Functions here must be *generic* utilities (logging setup, filesystem
  helpers, formatting). Anything image-specific belongs in
  :mod:`src.image_loader`, anything plot-specific in
  :mod:`src.visualization`.
* Functions must be small, pure where possible, and independently testable.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src import config

logger = logging.getLogger(__name__)


def setup_logging(level: int = config.LOG_LEVEL) -> None:
    """Configure application-wide logging with a console and a file handler.

    Must be called exactly once, as early as possible in the program entry
    point (``main.py``). All modules then obtain their own logger via
    ``logging.getLogger(__name__)`` and automatically inherit this setup.

    Args:
        level: Minimum log level for both handlers. Defaults to the value
            defined in :mod:`src.config`.
    """
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(fmt=config.LOG_FORMAT, datefmt=config.LOG_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # Replace (instead of append) handlers so repeated calls -- e.g. in
    # tests or notebooks -- never produce duplicated log lines.
    root_logger.handlers = [console_handler, file_handler]

    logger.debug("Logging initialised (level=%s)", logging.getLevelName(level))


def ensure_directories(*directories: Path) -> None:
    """Create the given directories if they do not exist yet.

    Idempotent: existing directories are left untouched. Keeps ``main.py``
    free of filesystem boilerplate.

    Args:
        *directories: Any number of directory paths to create.
    """
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug("Ensured directory exists: %s", directory)


def format_file_size(num_bytes: int) -> str:
    """Convert a byte count into a human-readable string.

    Args:
        num_bytes: File size in bytes. Must be non-negative.

    Returns:
        A string such as ``"1.4 MB"`` or ``"312.0 KB"``.

    Raises:
        ValueError: If ``num_bytes`` is negative.
    """
    if num_bytes < 0:
        raise ValueError(f"File size cannot be negative, got {num_bytes}.")

    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024.0
    # Unreachable, but keeps type checkers happy about the return type.
    return f"{size:.1f} TB"
