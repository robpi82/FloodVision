"""Persisted GUI settings: dataclass model plus JSON load/save.

Separation of concerns: this module owns *what* the settings are and
*how* they persist; :mod:`src.gui.settings_dialog` owns how they are
edited. The backend configuration (``config.yaml``) stays untouched --
GUI settings are *runtime overrides* that flow into the backend through
its existing dependency-injection points (``HSVRange``,
``BatchProcessor`` directory parameters), which is why no backend module
needs to know this file exists.
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
    """Immutable snapshot of all user-adjustable GUI settings.

    Defaults are seeded from the validated YAML configuration, so a fresh
    installation behaves exactly like the CLI. ``replace(settings, ...)``
    (from :mod:`dataclasses`) is used to derive modified copies instead of
    mutating -- the same value-object style as the backend records.

    Attributes:
        before_dir: Pre-event image directory.
        after_dir: Post-event image directory.
        output_dir: Product output directory.
        hsv_lower: Lower HSV bound for water detection.
        hsv_upper: Upper HSV bound for water detection.
        dark_mode: ``True`` for the dark theme.
    """

    before_dir: str = str(config.BEFORE_DATA_DIR)
    after_dir: str = str(config.AFTER_DATA_DIR)
    output_dir: str = str(config.OUTPUT_DATA_DIR)
    hsv_lower: tuple[int, int, int] = config.WATER_HSV_LOWER
    hsv_upper: tuple[int, int, int] = config.WATER_HSV_UPPER
    dark_mode: bool = True


def load_settings(path: Path = SETTINGS_PATH) -> AppSettings:
    """Load settings from JSON, falling back to defaults on any problem.

    A missing or corrupt settings file must never prevent the application
    from starting -- worst case the user re-adjusts a slider. This is the
    opposite policy to the backend's fail-fast ``config.yaml`` handling,
    and intentionally so: ``config.yaml`` is *required project
    configuration*, ``gui_settings.json`` is *optional convenience state*.

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
            before_dir=str(raw.get("before_dir", defaults.before_dir)),
            after_dir=str(raw.get("after_dir", defaults.after_dir)),
            output_dir=str(raw.get("output_dir", defaults.output_dir)),
            hsv_lower=_as_triple(raw.get("hsv_lower"), defaults.hsv_lower),
            hsv_upper=_as_triple(raw.get("hsv_upper"), defaults.hsv_upper),
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
