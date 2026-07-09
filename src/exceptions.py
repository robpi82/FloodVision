"""Custom exception hierarchy for FloodVision.

Every domain-specific error in this project derives from
:class:`FloodVisionError`. This gives calling code (for example ``main.py``)
one single ``except FloodVisionError`` clause to distinguish *expected,
domain-level* failures (bad input data, empty directories) from genuine
programming errors, which are intentionally allowed to crash loudly.

Future modules (flood detection, segmentation, GIS export, ML inference)
should add their own exception types here so the hierarchy stays in one
discoverable place.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


class FloodVisionError(Exception):
    """Base class for all FloodVision-specific errors."""


class NoImagesFoundError(FloodVisionError):
    """Raised when a directory contains no supported image files.

    Attributes:
        directory: The directory that was searched.
        supported_extensions: The extensions that were looked for.
    """

    def __init__(self, directory: Path, supported_extensions: Iterable[str]) -> None:
        self.directory = directory
        self.supported_extensions = sorted(supported_extensions)
        message = (
            f"No supported image files found in '{directory}'. "
            f"Supported extensions: {', '.join(self.supported_extensions)}. "
            f"Please place at least one image into this directory."
        )
        super().__init__(message)


class ImageLoadError(FloodVisionError):
    """Raised when a file exists but cannot be decoded as an image.

    Attributes:
        path: The file that failed to load.
    """

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        message = f"Failed to load image '{path}': {reason}"
        super().__init__(message)


class NoImagePairsFoundError(FloodVisionError):
    """Raised when before/after directories share no common filenames.

    Attributes:
        before_dir: The pre-event image directory.
        after_dir: The post-event image directory.
    """

    def __init__(self, before_dir: Path, after_dir: Path) -> None:
        self.before_dir = before_dir
        self.after_dir = after_dir
        message = (
            f"No matching image pairs between '{before_dir}' and '{after_dir}'. "
            f"A pair requires the identical filename in both directories."
        )
        super().__init__(message)


class ConfigurationError(FloodVisionError):
    """Raised when the YAML configuration is missing, unreadable or invalid.

    Configuration problems are *user-fixable* domain errors (edit the
    file, restart), not programming bugs -- hence they belong under
    :class:`FloodVisionError` and carry messages that name the exact file,
    key and expected value range.
    """


class GeoTiffPairError(FloodVisionError):
    """Raised when a before/after pair cannot be compared geospatially.

    Covers *mixed* pairs (exactly one georeferenced file) and spatially
    *incompatible* GeoTIFF pairs. It is raised inside the per-pair batch
    failure boundary, so it becomes a failed record with a useful reason
    -- never a crashed batch.

    Attributes:
        pair_name: Shared filename of the pair.
        reason: Human-readable rejection reason (e.g. the compatibility
            validator's one-line summary).
    """

    def __init__(self, pair_name: str, reason: str) -> None:
        self.pair_name = pair_name
        self.reason = reason
        super().__init__(f"GeoTIFF pair '{pair_name}' rejected: {reason}")


class GeoTiffExportError(FloodVisionError):
    """Raised when a georeferenced GeoTIFF result cannot be written.

    Covers Rasterio/GDAL write failures and filesystem problems (disk
    full, permission denied). Contract violations of the mask itself
    (wrong shape or dtype) are a *programmer* error, not a runtime
    failure, and are raised as plain :class:`ValueError` instead --
    mirroring how :func:`src.change_detection.compare_masks` separates
    the two failure classes.

    Attributes:
        path: The output file that failed to write.
        reason: Human-readable failure reason.
    """

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to write georeferenced GeoTIFF '{path}': {reason}")