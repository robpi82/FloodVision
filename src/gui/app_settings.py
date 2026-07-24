"""Persisted GUI settings: dataclass model plus JSON load/save.

Separation of concerns: this module owns *what* the settings are and
*how* they persist; :mod:`src.gui.settings_dialog` owns how they are
edited. The backend configuration (``config.yaml``) stays untouched --
GUI settings are *runtime overrides* that flow into the backend through
its existing dependency-injection points (``HSVRange``,
``BatchProcessor`` directory parameters), which is why no backend module
needs to know this file exists.

Cross-platform directory portability:
    ``gui_settings.json`` is git-ignored, but a whole-project folder
    synced via iCloud/OneDrive/Dropbox (or copied by hand) carries it
    along regardless -- so a before/after/output directory saved on one
    machine can silently reappear on another OS or user account.
    :func:`load_settings` therefore never applies a stored directory
    blindly: each of the three fields is only kept if it names a
    directory that actually exists *on the machine currently running
    the app*; otherwise it falls back to the project-relative default
    (``src.config.BEFORE_DATA_DIR`` and friends), which is always valid
    since it is computed from ``__file__`` at import time.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Final

from src import config

logger = logging.getLogger(__name__)

SETTINGS_PATH: Final[Path] = config.PROJECT_ROOT / "gui_settings.json"


@dataclass(frozen=True)
class AppSettings:
    before_dir: str = str(config.BEFORE_DATA_DIR)
    after_dir: str = str(config.AFTER_DATA_DIR)
    output_dir: str = str(config.OUTPUT_DATA_DIR)
    hsv_lower: tuple[int, int, int] = config.WATER_HSV_LOWER
    hsv_upper: tuple[int, int, int] = config.WATER_HSV_UPPER
    detection_mode: str = "hsv"
    dark_mode: bool = True


def load_settings(path: Path = SETTINGS_PATH) -> AppSettings:
    """Load settings from JSON, falling back to defaults on any problem.

    A missing or corrupt settings file must never prevent the application
    from starting -- worst case the user re-adjusts a slider. This is the
    opposite policy to the backend's fail-fast ``config.yaml`` handling,
    and intentionally so: ``config.yaml`` is *required project
    configuration*, ``gui_settings.json`` is *optional convenience state*.

    Directory fields go through :func:`_reconcile_directory` rather than
    being applied as-is, so a path saved on a different machine or OS
    (see the module docstring) cannot silently redirect this session's
    input/output folders.

    Args:
        path: Settings file location.

    Returns:
        The loaded settings, or defaults if unavailable/invalid.
    """
    if not path.is_file():
        logger.info("No GUI settings at %s, using defaults", path)
        return AppSettings()
    try:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        defaults = AppSettings()
        return replace(
            defaults,
            before_dir=_reconcile_directory(
                raw.get("before_dir"), defaults.before_dir, "before_dir"
            ),
            after_dir=_reconcile_directory(
                raw.get("after_dir"), defaults.after_dir, "after_dir"
            ),
            output_dir=_reconcile_directory(
                raw.get("output_dir"), defaults.output_dir, "output_dir"
            ),
            hsv_lower=_as_triple(raw.get("hsv_lower"), defaults.hsv_lower),
            hsv_upper=_as_triple(raw.get("hsv_upper"), defaults.hsv_upper),
            detection_mode=str(
                raw.get("detection_mode", defaults.detection_mode)
            ),
            dark_mode=bool(raw.get("dark_mode", defaults.dark_mode)),
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.exception("GUI settings unreadable, using defaults: %s", path)
        return AppSettings()


def save_settings(settings: AppSettings, path: Path = SETTINGS_PATH) -> None:
    """Persist settings as human-readable JSON.

    Args:
        settings: The settings snapshot to save.
        path: Target file location.
    """
    path.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info("GUI settings saved to %s", path)


def _reconcile_directory(stored: Any, default: str, field_name: str) -> str:
    """Keep a stored directory only if it exists on this machine.

    Persisted paths in ``gui_settings.json`` are plain strings written
    by a *previous* session -- possibly on a different OS or user
    account (see the module docstring for how they travel between
    machines). A stored path that no longer resolves to a real
    directory here is untrustworthy regardless of *why* -- foreign OS,
    deleted, or never created -- so it is replaced by the
    project-relative default instead of being applied blindly.

    This intentionally does not try to distinguish "foreign machine" from
    "a directory I just have not created yet": both look identical from a
    plain existence check, and only the former is the reported problem.
    In the GUI, directories are almost always chosen through a folder
    picker (which can only select directories that already exist), so a
    genuinely fresh custom path is a rare edge case -- see the module's
    "known limitations" note in the v0.8.0 migration report.

    Args:
        stored: The raw JSON value for this field (``None`` if the key
            was absent).
        default: The project-relative default for this field (see
            :class:`AppSettings`).
        field_name: Field name, used only for the log message.

    Returns:
        ``str(stored)`` if it names a directory that exists right now,
        otherwise ``default``.
    """
    if stored is None:
        return default
    candidate = str(stored)
    try:
        exists_here = Path(candidate).is_dir()
    except (OSError, ValueError):
        # A stored string can be syntactically invalid on this OS (e.g.
        # characters illegal in Windows paths, or embedded null bytes);
        # treat that the same as "does not exist" rather than crashing
        # application startup over a settings file.
        exists_here = False
    if exists_here:
        return candidate
    logger.info(
        "Stored %s '%s' does not exist on this machine; using default: %s",
        field_name,
        candidate,
        default,
    )
    return default


def _as_triple(value: Any, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    """Coerce a JSON list into an int triple, falling back when invalid.

    Args:
        value: Raw JSON value.
        fallback: Value to use when coercion is impossible.

    Returns:
        A validated ``(int, int, int)`` tuple.
    """
    if (
        isinstance(value, (list, tuple))
        and len(value) == 3
        and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    ):
        return (value[0], value[1], value[2])
    return fallback