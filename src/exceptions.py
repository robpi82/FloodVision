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
