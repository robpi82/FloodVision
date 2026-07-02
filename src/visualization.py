"""Display utilities for FloodVision, built on matplotlib.

This module is deliberately a collection of *functions*, not a class: it
holds no state between calls, so object-oriented design would add ceremony
without benefit. Should stateful features arrive later (themes, multi-panel
dashboards), a ``FigureBuilder`` class can be introduced here without
changing any caller-facing behaviour.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from src import utils
from src.image_loader import ImageInfo

logger = logging.getLogger(__name__)

_FIGURE_SIZE_INCHES: tuple[float, float] = (10.0, 7.0)


def display_image(
    image: Image.Image,
    info: ImageInfo | None = None,
    *,
    save_path: Path | None = None,
    show: bool = True,
) -> None:
    """Display an image in a matplotlib window and/or save it to disk.

    Args:
        image: The Pillow image to display.
        info: Optional metadata used to build an informative title.
        save_path: If given, the figure is additionally written to this file
            (useful for headless environments and automated reports).
        show: If ``True`` (default) the figure is shown interactively.
            Set to ``False`` in tests or batch runs.
    """
    figure, axes = plt.subplots(figsize=_FIGURE_SIZE_INCHES)

    # Single-band images (mode "L", "I;16", ...) need an explicit gray
    # colormap; otherwise matplotlib applies its default "viridis" palette,
    # which misrepresents grayscale satellite data.
    colormap = "gray" if info is not None and info.channels == 1 else None
    axes.imshow(image, cmap=colormap)
    axes.set_axis_off()

    axes.set_title(_build_title(info), fontsize=11)
    figure.tight_layout()

    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info("Figure saved to %s", save_path)

    if show:
        plt.show()

    plt.close(figure)


def display_panels(
    panels: Sequence[tuple[str, np.ndarray]],
    *,
    suptitle: str | None = None,
    save_path: Path | None = None,
    show: bool = True,
) -> None:
    """Display several images side by side in one figure.

    Two-dimensional arrays (binary masks, grayscale) are rendered with the
    ``gray`` colormap and fixed limits ``vmin=0, vmax=255`` so that a mask
    containing only zeros still appears black instead of being auto-scaled.

    Args:
        panels: Ordered ``(title, image_array)`` pairs; arrays may be RGB
            ``(H, W, 3)`` or single-channel ``(H, W)``.
        suptitle: Optional headline above all panels.
        save_path: If given, the complete figure is saved to this file.
        show: If ``True`` (default) the figure is shown interactively.

    Raises:
        ValueError: If ``panels`` is empty.
    """
    if not panels:
        raise ValueError("display_panels() requires at least one panel.")

    figure, axes = plt.subplots(
        nrows=1,
        ncols=len(panels),
        figsize=(
            _FIGURE_SIZE_INCHES[0] * 0.6 * len(panels),
            _FIGURE_SIZE_INCHES[1] * 0.6,
        ),
    )
    # With ncols == 1 matplotlib returns a single Axes instead of an array;
    # np.atleast_1d normalises both cases so the loop below always works.
    for axis, (title, array) in zip(np.atleast_1d(axes), panels):
        if array.ndim == 2:
            axis.imshow(array, cmap="gray", vmin=0, vmax=255)
        else:
            axis.imshow(array)
        axis.set_title(title, fontsize=10)
        axis.set_axis_off()

    if suptitle:
        figure.suptitle(suptitle, fontsize=12)
    figure.tight_layout()

    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info("Comparison figure saved to %s", save_path)

    if show:
        plt.show()

    plt.close(figure)


def save_image(array: np.ndarray, path: Path) -> None:
    """Write an image array (RGB or single-channel) losslessly to disk.

    Belongs to the presentation layer because it produces user-facing
    artefacts; unlike :func:`display_panels` it saves the *pure pixel
    data* without any matplotlib decoration, axes or resampling.

    Args:
        array: ``(H, W, 3)`` RGB or ``(H, W)`` grayscale/mask uint8 array.
        path: Target file path; parent directories are created as needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array).save(path)
    logger.info("Image saved to %s", path)


def _build_title(info: ImageInfo | None) -> str:
    """Build a human-readable figure title from image metadata.

    Args:
        info: Metadata of the displayed image, or ``None``.

    Returns:
        A one-line title string; a generic fallback if no metadata is given.
    """
    if info is None:
        return "FloodVision - Image Preview"
    return (
        f"{info.filename}  |  {info.width} x {info.height} px  |  "
        f"{info.channels} channel(s)  |  mode: {info.mode}  |  "
        f"{utils.format_file_size(info.file_size_bytes)}"
    )
