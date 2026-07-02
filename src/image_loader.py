"""Discovery and loading of image files from the raw data directory.

This module owns exactly one responsibility: turning files on disk into
in-memory image objects plus structured metadata. It knows nothing about
visualization, flood detection or reporting.

Public API:
    * :class:`ImageInfo`  -- immutable metadata record for a loaded image.
    * :class:`ImageLoader` -- finds and loads supported images.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from src import config
from src.exceptions import ImageLoadError, NoImagePairsFoundError, NoImagesFoundError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImagePair:
    """A before/after image pair identified by a shared filename.

    Attributes:
        name: The common filename (e.g. ``"location01.png"``).
        before_path: Path to the pre-event image.
        after_path: Path to the post-event image.
    """

    name: str
    before_path: Path
    after_path: Path

    @property
    def stem(self) -> str:
        """Filename without extension, used for output directory naming."""
        return Path(self.name).stem


def find_image_pairs(
    before_dir: Path = config.BEFORE_DATA_DIR,
    after_dir: Path = config.AFTER_DATA_DIR,
    supported_extensions: frozenset[str] = config.SUPPORTED_IMAGE_EXTENSIONS,
) -> list[ImagePair]:
    """Match images in two directories by identical filename.

    Files without a partner in the other directory are skipped and logged
    as a warning -- an unmatched file is a data-quality issue the user
    should notice, but never a reason to abort the run.

    Args:
        before_dir: Directory with pre-event images.
        after_dir: Directory with post-event images.
        supported_extensions: File extensions treated as images.

    Returns:
        Matching pairs, sorted by filename for deterministic runs.

    Raises:
        NoImagesFoundError: If either directory contains no images at all.
        NoImagePairsFoundError: If both directories contain images but no
            filename exists in both.
    """
    # Reuse the existing single-directory discovery (DRY): case-insensitive
    # extension filtering and empty-directory errors come for free.
    before_files = {path.name: path for path in ImageLoader(before_dir).find_images()}
    after_files = {path.name: path for path in ImageLoader(after_dir).find_images()}

    common_names = sorted(before_files.keys() & after_files.keys())

    for unmatched in sorted(before_files.keys() - after_files.keys()):
        logger.warning("Skipping '%s': no AFTER partner in %s", unmatched, after_dir)
    for unmatched in sorted(after_files.keys() - before_files.keys()):
        logger.warning("Skipping '%s': no BEFORE partner in %s", unmatched, before_dir)

    if not common_names:
        raise NoImagePairsFoundError(before_dir, after_dir)

    logger.info("Found %d matching image pair(s)", len(common_names))
    return [
        ImagePair(
            name=name, before_path=before_files[name], after_path=after_files[name]
        )
        for name in common_names
    ]


@dataclass(frozen=True)
class ImageInfo:
    """Immutable metadata describing a loaded image.

    Attributes:
        filename: File name including extension (no directory part).
        path: Absolute path to the image file.
        width: Image width in pixels.
        height: Image height in pixels.
        channels: Number of colour channels (e.g. 1 for grayscale, 3 for RGB).
        mode: Pillow image mode string (e.g. ``"RGB"``, ``"L"``, ``"I;16"``).
        file_size_bytes: Size of the file on disk in bytes.
    """

    filename: str
    path: Path
    width: int
    height: int
    channels: int
    mode: str
    file_size_bytes: int

    @classmethod
    def from_image(cls, image: Image.Image, path: Path) -> "ImageInfo":
        """Build an :class:`ImageInfo` from an open Pillow image and its path.

        Args:
            image: An already opened Pillow image.
            path: The file the image was loaded from.

        Returns:
            A fully populated, immutable metadata record.
        """
        return cls(
            filename=path.name,
            path=path.resolve(),
            width=image.width,
            height=image.height,
            channels=len(image.getbands()),
            mode=image.mode,
            file_size_bytes=path.stat().st_size,
        )


class ImageLoader:
    """Finds and loads image files from a directory.

    The loader encapsulates two pieces of policy in a single place:
    *where* images live and *which* file formats count as images. Both are
    injected via the constructor (dependency injection), so tests can point
    the loader at a temporary directory and future code can reuse it for
    other directories without modification.
    """

    def __init__(
        self,
        directory: Path = config.RAW_DATA_DIR,
        supported_extensions: frozenset[str] = config.SUPPORTED_IMAGE_EXTENSIONS,
    ) -> None:
        """Initialise the loader.

        Args:
            directory: Directory to search for images. Defaults to the
                project's ``data/raw`` directory from :mod:`src.config`.
            supported_extensions: Lowercase file extensions (including the
                leading dot) that are treated as images.
        """
        self._directory = directory
        self._supported_extensions = supported_extensions

    @property
    def directory(self) -> Path:
        """The directory this loader searches (read-only)."""
        return self._directory

    def find_images(self) -> list[Path]:
        """Return all supported image files in the configured directory.

        The comparison is case-insensitive (``photo.TIF`` is found) and the
        result is sorted alphabetically so that runs are deterministic.

        Returns:
            A sorted list of image file paths.

        Raises:
            NoImagesFoundError: If the directory does not exist or contains
                no supported image files.
        """
        if not self._directory.is_dir():
            logger.warning("Image directory does not exist: %s", self._directory)
            raise NoImagesFoundError(self._directory, self._supported_extensions)

        images = sorted(
            entry
            for entry in self._directory.iterdir()
            if entry.is_file() and entry.suffix.lower() in self._supported_extensions
        )

        if not images:
            raise NoImagesFoundError(self._directory, self._supported_extensions)

        logger.info("Found %d image file(s) in %s", len(images), self._directory)
        return images

    def load(self, path: Path) -> Image.Image:
        """Load a single image file into memory.

        Args:
            path: Path to the image file.

        Returns:
            The decoded Pillow image with all pixel data read into memory.

        Raises:
            ImageLoadError: If the file is missing or cannot be decoded.
        """
        logger.info("Loading image: %s", path.name)
        try:
            image = Image.open(path)
            # Pillow opens files lazily; load() forces the actual decode now
            # so that corrupt files fail here -- inside our error handling --
            # and not later in some unrelated processing step.
            image.load()
        except FileNotFoundError as error:
            raise ImageLoadError(path, "file not found") from error
        except UnidentifiedImageError as error:
            raise ImageLoadError(path, "file is not a readable image") from error
        except OSError as error:
            raise ImageLoadError(path, f"I/O error while decoding ({error})") from error

        logger.debug(
            "Loaded %s (%dx%d, mode=%s)",
            path.name,
            image.width,
            image.height,
            image.mode,
        )
        return image
