"""Central configuration for the FloodVision application.

Since Version 0.5 this module has two layers:

1. **Code-level constants** -- structural values a *user* never needs to
   touch (project layout, log format, file naming, processing kernel
   sizes). They stay hardcoded here.
2. **User-facing settings** -- everything an operator tunes per dataset
   (paths, HSV thresholds, overlay opacity, log level). These are loaded
   from ``config.yaml`` in the project root **at import time** and
   exposed under the exact same names as before, so no consuming module
   had to change.

Every YAML value is validated on load (missing keys, wrong types, values
out of range) and any problem raises
:class:`~src.exceptions.ConfigurationError` with the precise dotted key,
e.g. ``water_detection.hsv_lower`` -- the application refuses to start
with a broken configuration instead of failing later mid-batch
(fail fast).

Design note -- why import-time loading?
    The rest of the codebase consumes configuration as module attributes
    (``config.WATER_HSV_LOWER``), partly as function-parameter defaults.
    Loading at import keeps that contract intact with zero changes to the
    processing code. The alternative -- an injected settings object
    (e.g. pydantic-settings) -- is the cleaner long-term pattern and the
    planned migration path, but would ripple through every signature.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Final

import yaml

from src.exceptions import ConfigurationError

# ---------------------------------------------------------------------------
# Project root & configuration file
# ---------------------------------------------------------------------------
# This file lives in <project>/src/, therefore the project root is exactly
# two ``parent`` steps up from the resolved file location.
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
CONFIG_FILE: Final[Path] = PROJECT_ROOT / "config.yaml"

# ---------------------------------------------------------------------------
# Code-level constants (not user-facing)
# ---------------------------------------------------------------------------
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
RAW_DATA_DIR: Final[Path] = DATA_DIR / "raw"  # legacy (v0.1-v0.3 single mode)
PROCESSED_DATA_DIR: Final[Path] = DATA_DIR / "processed"

ASSETS_DIR: Final[Path] = PROJECT_ROOT / "assets"
MODELS_DIR: Final[Path] = PROJECT_ROOT / "models"

LOG_DIR: Final[Path] = PROJECT_ROOT / "logs"
LOG_FILE: Final[Path] = LOG_DIR / "floodvision.log"
LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# A frozenset is used because membership tests are O(1) and the collection
# is immutable by design: supported formats are a policy, not mutable state.
SUPPORTED_IMAGE_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
)

# Pre-threshold smoothing / mask cleanup: processing-internal tuning that
# interacts with kernel-oddness rules -- kept out of the YAML on purpose.
GAUSSIAN_BLUR_KERNEL: Final[tuple[int, int]] = (5, 5)
MORPH_KERNEL_SIZE: Final[int] = 5
MORPH_OPEN_ITERATIONS: Final[int] = 2
MORPH_CLOSE_ITERATIONS: Final[int] = 2

# Colours are expressed in RGB because the whole pipeline works on RGB
# arrays (Pillow order); we never store BGR to avoid channel-order bugs.
OVERLAY_COLOR_RGB: Final[tuple[int, int, int]] = (0, 110, 255)
NEW_FLOOD_COLOR_RGB: Final[tuple[int, int, int]] = (230, 40, 40)

# ---------------------------------------------------------------------------
# YAML loading & validation helpers (private)
# ---------------------------------------------------------------------------
_VALID_LOG_LEVELS: Final[frozenset[str]] = frozenset(
    {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
)
_HSV_MAXIMA: Final[tuple[int, int, int]] = (179, 255, 255)
_HSV_CHANNELS: Final[tuple[str, str, str]] = ("H", "S", "V")


def _load_yaml_document(path: Path) -> dict[str, Any]:
    """Read and parse the YAML configuration file.

    Args:
        path: Location of ``config.yaml``.

    Returns:
        The parsed top-level mapping.

    Raises:
        ConfigurationError: If the file is missing, not parseable as YAML,
            or its top level is not a mapping.
    """
    if not path.is_file():
        raise ConfigurationError(
            f"Configuration file not found: '{path}'. FloodVision expects "
            f"'config.yaml' in the project root; restore it from version "
            f"control or the project archive."
        )
    try:
        # safe_load (never load): parses plain data only and cannot execute
        # arbitrary Python objects embedded in a manipulated YAML file.
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ConfigurationError(f"'{path}' is not valid YAML: {error}") from error

    if not isinstance(document, dict):
        raise ConfigurationError(
            f"Top level of '{path}' must be a mapping of sections, "
            f"got {type(document).__name__}."
        )
    return document


def _require_section(document: dict[str, Any], key: str) -> dict[str, Any]:
    """Fetch a top-level section that must be a mapping.

    Args:
        document: Parsed YAML document.
        key: Section name.

    Returns:
        The section mapping.

    Raises:
        ConfigurationError: If the section is missing or not a mapping.
    """
    value = _require(document, key, context="config.yaml")
    if not isinstance(value, dict):
        raise ConfigurationError(
            f"Section '{key}' in config.yaml must be a mapping, "
            f"got {type(value).__name__}."
        )
    return value


def _require(mapping: dict[str, Any], key: str, context: str) -> Any:
    """Fetch a required key, failing with its full dotted path.

    Args:
        mapping: Mapping to read from.
        key: Required key.
        context: Dotted location for the error message (e.g. ``"paths"``).

    Returns:
        The raw value.

    Raises:
        ConfigurationError: If the key is absent.
    """
    if key not in mapping:
        raise ConfigurationError(
            f"Missing required configuration key '{context}.{key}' in config.yaml."
        )
    return mapping[key]


def _as_directory(value: Any, key: str) -> Path:
    """Validate a directory setting and resolve it against the project root.

    Args:
        value: Raw YAML value.
        key: Dotted key for error messages.

    Returns:
        An absolute path (relative inputs are anchored at ``PROJECT_ROOT``
        so the YAML stays portable between machines).

    Raises:
        ConfigurationError: If the value is not a non-empty string.
    """
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(
            f"'{key}' must be a non-empty path string, got {value!r}."
        )
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _as_log_level(value: Any, key: str) -> int:
    """Validate a log level name and convert it to its numeric constant.

    Args:
        value: Raw YAML value (e.g. ``"INFO"``).
        key: Dotted key for error messages.

    Returns:
        The numeric ``logging`` level.

    Raises:
        ConfigurationError: If the name is not a known level.
    """
    if not isinstance(value, str) or value.upper() not in _VALID_LOG_LEVELS:
        raise ConfigurationError(
            f"'{key}' must be one of {sorted(_VALID_LOG_LEVELS)}, got {value!r}."
        )
    return getattr(logging, value.upper())


def _as_hsv_triple(value: Any, key: str) -> tuple[int, int, int]:
    """Validate an HSV bound: three integers within OpenCV's value ranges.

    Args:
        value: Raw YAML value (expected: list of three ints).
        key: Dotted key for error messages.

    Returns:
        The bound as an ``(H, S, V)`` tuple.

    Raises:
        ConfigurationError: On wrong length, non-integer entries or values
            outside ``H:[0,179] S:[0,255] V:[0,255]``.
    """
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ConfigurationError(
            f"'{key}' must be a list of three integers [H, S, V], got {value!r}."
        )
    for channel, item, maximum in zip(_HSV_CHANNELS, value, _HSV_MAXIMA):
        # bool is a subclass of int in Python -- YAML `true` would otherwise
        # slip through an isinstance(int) check as the number 1.
        if isinstance(item, bool) or not isinstance(item, int):
            raise ConfigurationError(
                f"'{key}': channel {channel} must be an integer, got {item!r}."
            )
        if not 0 <= item <= maximum:
            raise ConfigurationError(
                f"'{key}': channel {channel} must lie in [0, {maximum}], got {item}."
            )
    return (int(value[0]), int(value[1]), int(value[2]))


def _validate_hsv_window(
    lower: tuple[int, int, int], upper: tuple[int, int, int]
) -> None:
    """Ensure the lower HSV bound does not exceed the upper bound.

    Args:
        lower: Validated lower bound.
        upper: Validated upper bound.

    Raises:
        ConfigurationError: If any lower channel exceeds its upper channel.
    """
    for channel, low, high in zip(_HSV_CHANNELS, lower, upper):
        if low > high:
            raise ConfigurationError(
                f"water_detection: {channel} lower bound {low} exceeds "
                f"upper bound {high} (hsv_lower must be <= hsv_upper)."
            )


def _as_alpha(value: Any, key: str) -> float:
    """Validate an opacity value in ``[0, 1]``.

    Args:
        value: Raw YAML value.
        key: Dotted key for error messages.

    Returns:
        The opacity as float.

    Raises:
        ConfigurationError: If the value is not a number in ``[0, 1]``.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"'{key}' must be a number, got {value!r}.")
    if not 0.0 <= float(value) <= 1.0:
        raise ConfigurationError(f"'{key}' must lie in [0, 1], got {value}.")
    return float(value)


# ---------------------------------------------------------------------------
# User-facing settings, loaded and validated from config.yaml
# ---------------------------------------------------------------------------
_document = _load_yaml_document(CONFIG_FILE)
_paths = _require_section(_document, "paths")
_logging = _require_section(_document, "logging")
_water = _require_section(_document, "water_detection")
_overlay = _require_section(_document, "overlay")

BEFORE_DATA_DIR: Final[Path] = _as_directory(
    _require(_paths, "before_dir", "paths"), "paths.before_dir"
)
AFTER_DATA_DIR: Final[Path] = _as_directory(
    _require(_paths, "after_dir", "paths"), "paths.after_dir"
)
OUTPUT_DATA_DIR: Final[Path] = _as_directory(
    _require(_paths, "output_dir", "paths"), "paths.output_dir"
)

LOG_LEVEL: Final[int] = _as_log_level(
    _require(_logging, "level", "logging"), "logging.level"
)

WATER_HSV_LOWER: Final[tuple[int, int, int]] = _as_hsv_triple(
    _require(_water, "hsv_lower", "water_detection"), "water_detection.hsv_lower"
)
WATER_HSV_UPPER: Final[tuple[int, int, int]] = _as_hsv_triple(
    _require(_water, "hsv_upper", "water_detection"), "water_detection.hsv_upper"
)
_validate_hsv_window(WATER_HSV_LOWER, WATER_HSV_UPPER)

OVERLAY_ALPHA: Final[float] = _as_alpha(
    _require(_overlay, "alpha", "overlay"), "overlay.alpha"
)
CHANGE_OVERLAY_ALPHA: Final[float] = _as_alpha(
    _require(_overlay, "change_alpha", "overlay"), "overlay.change_alpha"
)

# Derived paths (must come after the YAML-driven directories).
REPORT_CSV_PATH: Final[Path] = OUTPUT_DATA_DIR / "report.csv"

# The raw document served its purpose; removing the temporaries keeps the
# module namespace clean for introspection and star-import hygiene.
del _document, _paths, _logging, _water, _overlay
