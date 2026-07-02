"""Binary mask post-processing and mask-based image products.

This module owns everything that happens *after* a raw binary mask exists:
noise removal (morphology), quality metrics and the semi-transparent
overlay product. It deliberately knows nothing about *how* the mask was
produced (HSV thresholding today, an ML model tomorrow) -- that separation
is what keeps Version 0.4's AI segmentation a drop-in replacement.

Like :mod:`src.visualization`, this module is a collection of stateless
functions: every function is a pure transformation ``array in -> array out``
with no state between calls, so a class would add ceremony without benefit.

Conventions:
    * Masks are 2-D ``uint8`` arrays with exactly two values:
      255 = water (white), 0 = non-water (black).
    * Images are 3-D ``uint8`` arrays in **RGB** channel order (Pillow
      order). BGR never enters or leaves this module.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from numpy.typing import NDArray

from src import config

logger = logging.getLogger(__name__)

# Semantic aliases: the type checker treats them identically to their right-
# hand side, but human readers instantly see *which kind* of array a
# function expects. Cheap documentation that never goes out of date.
MaskArray = NDArray[np.uint8]
RGBImageArray = NDArray[np.uint8]

#: Pixel value representing water in a binary mask.
WATER_VALUE: int = 255


def apply_opening(
    mask: MaskArray,
    kernel_size: int = config.MORPH_KERNEL_SIZE,
    iterations: int = config.MORPH_OPEN_ITERATIONS,
) -> MaskArray:
    """Remove small isolated white specks from a binary mask.

    Morphological *opening* is an erosion followed by a dilation: objects
    smaller than the structuring element are eroded away entirely and
    therefore cannot be restored by the dilation, while larger objects
    regain their original size.

    Args:
        mask: Binary mask (0 / 255) to clean.
        kernel_size: Diameter of the elliptical structuring element in
            pixels. Larger values remove larger specks but also erase thin,
            genuine water features (narrow channels).
        iterations: How often the operation is repeated.

    Returns:
        The opened mask as a new array; the input is not modified.
    """
    _validate_mask(mask)
    kernel = _structuring_element(kernel_size)
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)


def apply_closing(
    mask: MaskArray,
    kernel_size: int = config.MORPH_KERNEL_SIZE,
    iterations: int = config.MORPH_CLOSE_ITERATIONS,
) -> MaskArray:
    """Fill small black holes inside white regions of a binary mask.

    Morphological *closing* is a dilation followed by an erosion: small
    gaps and pinholes inside water bodies (caused by waves, sun glint or
    sensor noise) are bridged by the dilation and stay filled after the
    erosion shrinks the region back to its original outline.

    Args:
        mask: Binary mask (0 / 255) to clean.
        kernel_size: Diameter of the elliptical structuring element.
        iterations: How often the operation is repeated.

    Returns:
        The closed mask as a new array; the input is not modified.
    """
    _validate_mask(mask)
    kernel = _structuring_element(kernel_size)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=iterations)


def clean_mask(
    mask: MaskArray,
    kernel_size: int = config.MORPH_KERNEL_SIZE,
    open_iterations: int = config.MORPH_OPEN_ITERATIONS,
    close_iterations: int = config.MORPH_CLOSE_ITERATIONS,
) -> MaskArray:
    """Run the standard cleanup chain on a raw mask: opening, then closing.

    Order matters and is intentional: opening first removes false-positive
    specks *before* closing could dilate them into larger blobs.

    Args:
        mask: Raw binary mask straight from thresholding.
        kernel_size: Structuring element diameter for both operations.
        open_iterations: Iterations for the opening step.
        close_iterations: Iterations for the closing step.

    Returns:
        The cleaned binary mask.
    """
    opened = apply_opening(mask, kernel_size, open_iterations)
    closed = apply_closing(opened, kernel_size, close_iterations)

    removed = int(np.count_nonzero(mask) - np.count_nonzero(closed))
    logger.debug(
        "Mask cleanup changed %d px (kernel=%d, open=%d, close=%d)",
        removed,
        kernel_size,
        open_iterations,
        close_iterations,
    )
    return closed


def colorize_mask(
    mask: MaskArray,
    color: tuple[int, int, int] = config.NEW_FLOOD_COLOR_RGB,
) -> RGBImageArray:
    """Render a binary mask as an RGB image: black background, colour = hits.

    Used for the "new flood" product where red pixels mark newly flooded
    areas on a black canvas (cartographic alert convention).

    Args:
        mask: Binary mask (0 / 255).
        color: RGB colour applied to all mask pixels.

    Returns:
        An ``(H, W, 3)`` uint8 RGB image.
    """
    _validate_mask(mask)
    canvas: RGBImageArray = np.zeros((*mask.shape, 3), dtype=np.uint8)
    canvas[mask == WATER_VALUE] = color
    return canvas


def create_overlay(
    image: RGBImageArray,
    mask: MaskArray,
    color: tuple[int, int, int] = config.OVERLAY_COLOR_RGB,
    alpha: float = config.OVERLAY_ALPHA,
) -> RGBImageArray:
    """Blend a semi-transparent colour layer onto the masked image regions.

    Technique: a copy of the image is painted solid ``color`` wherever the
    mask is white, then blended with the original via
    ``cv2.addWeighted(original, 1 - alpha, painted, alpha, 0)``. Outside the
    mask the painted copy equals the original, so the blend is a no-op
    there -- one vectorised operation, no per-pixel Python loop.

    Args:
        image: Original RGB image, shape ``(H, W, 3)``, dtype ``uint8``.
        mask: Binary water mask, shape ``(H, W)``, same H/W as the image.
        color: RGB overlay colour.
        alpha: Overlay opacity in ``[0, 1]``; 0 = invisible, 1 = opaque.

    Returns:
        A new RGB image with the highlighted water regions.

    Raises:
        ValueError: If shapes are incompatible or ``alpha`` is out of range.
    """
    _validate_rgb_image(image)
    _validate_mask(mask)
    if image.shape[:2] != mask.shape:
        raise ValueError(
            f"Image {image.shape[:2]} and mask {mask.shape} dimensions differ."
        )
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0, 1], got {alpha}.")

    painted = image.copy()
    painted[mask == WATER_VALUE] = color
    return cv2.addWeighted(image, 1.0 - alpha, painted, alpha, 0.0)


def mask_coverage_percent(mask: MaskArray) -> float:
    """Compute the percentage of mask pixels classified as water.

    Args:
        mask: Binary mask (0 / 255).

    Returns:
        Water coverage in percent of the total pixel count, ``0.0``-``100.0``.
    """
    _validate_mask(mask)
    return 100.0 * float(np.count_nonzero(mask)) / float(mask.size)


def _structuring_element(kernel_size: int) -> MaskArray:
    """Create the elliptical structuring element used by all morphology here.

    An ellipse is preferred over a square kernel because natural water
    boundaries are curved; square kernels leave visibly blocky artefacts.

    Args:
        kernel_size: Diameter in pixels; must be a positive odd number.

    Returns:
        The OpenCV structuring element.

    Raises:
        ValueError: If ``kernel_size`` is not a positive odd integer.
    """
    if kernel_size < 1 or kernel_size % 2 == 0:
        raise ValueError(f"kernel_size must be a positive odd int, got {kernel_size}.")
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))


def _validate_mask(mask: np.ndarray) -> None:
    """Fail fast if an array does not satisfy the binary-mask convention.

    Args:
        mask: Candidate array.

    Raises:
        ValueError: If the array is not 2-D ``uint8``.
    """
    if mask.ndim != 2 or mask.dtype != np.uint8:
        raise ValueError(
            f"Expected a 2-D uint8 mask, got ndim={mask.ndim}, dtype={mask.dtype}."
        )


def _validate_rgb_image(image: np.ndarray) -> None:
    """Fail fast if an array is not an RGB uint8 image.

    Args:
        image: Candidate array.

    Raises:
        ValueError: If the array is not ``(H, W, 3)`` ``uint8``.
    """
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError(
            "Expected an (H, W, 3) uint8 RGB image, got "
            f"shape={image.shape}, dtype={image.dtype}."
        )
