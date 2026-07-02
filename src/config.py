"""Central configuration for the FloodVision application.

This module is the single source of truth for all filesystem paths and
application-wide constants. No other module is allowed to hardcode a path
or a magic value; everything is imported from here.

Design notes
------------
* All paths are built with :class:`pathlib.Path` (never strings) so that
  the code is OS-independent and path arithmetic stays readable.
* ``PROJECT_ROOT`` is derived from the location of this file instead of the
  current working directory. This makes the application runnable from any
  directory (IDE, terminal, scheduler) without breaking paths.
* Constants are annotated with :data:`typing.Final` to signal that they must
  never be reassigned at runtime.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------
# This file lives in <project>/src/, therefore the project root is exactly
# two ``parent`` steps up from the resolved file location.
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Data directories
# ---------------------------------------------------------------------------
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
RAW_DATA_DIR: Final[Path] = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Final[Path] = DATA_DIR / "processed"
OUTPUT_DATA_DIR: Final[Path] = DATA_DIR / "output"

# ---------------------------------------------------------------------------
# Asset and model directories (reserved for future versions)
# ---------------------------------------------------------------------------
ASSETS_DIR: Final[Path] = PROJECT_ROOT / "assets"
MODELS_DIR: Final[Path] = PROJECT_ROOT / "models"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR: Final[Path] = PROJECT_ROOT / "logs"
LOG_FILE: Final[Path] = LOG_DIR / "floodvision.log"
LOG_LEVEL: Final[int] = logging.INFO
LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# ---------------------------------------------------------------------------
# Image handling
# ---------------------------------------------------------------------------
# A frozenset is used because membership tests are O(1) and the collection
# is immutable by design: supported formats are a policy, not mutable state.
# All extensions are stored lowercase; comparisons must therefore lowercase
# the file suffix first (see ImageLoader.find_images).
SUPPORTED_IMAGE_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
)

# ---------------------------------------------------------------------------
# Water detection (Version 0.2, classical HSV thresholding)
# ---------------------------------------------------------------------------
# OpenCV HSV value ranges: H in [0, 179], S in [0, 255], V in [0, 255].
# The hue window below covers cyan to deep blue tones, the S/V minima reject
# gray haze (low saturation) and near-black shadows (low value). These are
# *starting values* -- real scenes usually require per-dataset tuning.
WATER_HSV_LOWER: Final[tuple[int, int, int]] = (85, 40, 40)
WATER_HSV_UPPER: Final[tuple[int, int, int]] = (135, 255, 255)

# Pre-threshold smoothing. Kernel side lengths must be odd (OpenCV rule).
GAUSSIAN_BLUR_KERNEL: Final[tuple[int, int]] = (5, 5)

# Post-threshold mask cleanup (morphology). The kernel size is the diameter
# of the elliptical structuring element in pixels.
MORPH_KERNEL_SIZE: Final[int] = 5
MORPH_OPEN_ITERATIONS: Final[int] = 2
MORPH_CLOSE_ITERATIONS: Final[int] = 2

# ---------------------------------------------------------------------------
# Overlay rendering
# ---------------------------------------------------------------------------
# Colour is expressed in RGB because the whole pipeline works on RGB arrays
# (Pillow order); we never store BGR to avoid channel-order bugs.
OVERLAY_COLOR_RGB: Final[tuple[int, int, int]] = (0, 110, 255)
OVERLAY_ALPHA: Final[float] = 0.45

# ---------------------------------------------------------------------------
# Reporting (Version 0.3)
# ---------------------------------------------------------------------------
REPORT_CSV_PATH: Final[Path] = OUTPUT_DATA_DIR / "report.csv"

# ---------------------------------------------------------------------------
# Change detection (Version 0.4)
# ---------------------------------------------------------------------------
# Input pairs: images with identical filenames in these two directories are
# compared against each other (before = pre-event, after = post-event).
BEFORE_DATA_DIR: Final[Path] = DATA_DIR / "before"
AFTER_DATA_DIR: Final[Path] = DATA_DIR / "after"

# Rendering of *newly* flooded areas. Red is the cartographic convention
# for change/alert layers, distinct from the blue used for plain water.
NEW_FLOOD_COLOR_RGB: Final[tuple[int, int, int]] = (230, 40, 40)
CHANGE_OVERLAY_ALPHA: Final[float] = 0.5
