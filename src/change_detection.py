"""Change detection: comparison of before/after water masks.

This module answers exactly one question: *which water is new?* It
consumes two binary water masks -- it neither knows nor cares how they
were produced (HSV thresholding today, an ML segmenter tomorrow). That
mask-level interface is what makes change detection independent of the
segmentation method.

Core definition:
    A pixel counts as *newly flooded* if it is water in the AFTER mask
    **and** non-water in the BEFORE mask. Water that already existed is
    never counted; water that *receded* is intentionally not part of the
    new-flood mask (it lowers the net increase instead).

All heavy lifting is done with vectorised OpenCV bitwise operations --
no Python pixel loops, no machine learning.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

from src import mask_generator
from src.mask_generator import MaskArray

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MaskComparison:
    """Immutable, structured result of comparing two water masks.

    Attributes:
        new_water_mask: Binary mask (255 = newly flooded, 0 = unchanged).
        water_before_percent: Water coverage of the BEFORE mask in percent.
        water_after_percent: Water coverage of the AFTER mask in percent.
        new_water_percent: Share of the image that is *newly* flooded
            (gross gain), in percent.
        new_water_pixels: Absolute number of newly flooded pixels.
        increase_percent: Net coverage change in percentage points
            (``after - before``). Can be smaller than
            ``new_water_percent`` when water receded elsewhere, and even
            negative if recession outweighs new flooding.
    """

    new_water_mask: MaskArray
    water_before_percent: float
    water_after_percent: float
    new_water_percent: float
    new_water_pixels: int
    increase_percent: float


def compare_masks(before_mask: MaskArray, after_mask: MaskArray) -> MaskComparison:
    """Detect newly flooded pixels between two binary water masks.

    The new-flood mask is computed as ``AFTER AND (NOT BEFORE)`` using
    vectorised OpenCV bitwise operations: ``cv2.bitwise_not`` inverts the
    before mask (non-water becomes 255), ``cv2.bitwise_and`` then keeps
    exactly those pixels that are water now but were not water before.

    Args:
        before_mask: Binary water mask of the pre-event image (0 / 255).
        after_mask: Binary water mask of the post-event image (0 / 255).

    Returns:
        A :class:`MaskComparison` with the new-flood mask and all metrics.

    Raises:
        ValueError: If the masks violate the mask contract or their
            dimensions differ (unaligned image pairs must fail loudly
            instead of producing silently wrong change maps).
    """
    _validate_pair(before_mask, after_mask)

    new_water_mask: MaskArray = cv2.bitwise_and(
        after_mask, cv2.bitwise_not(before_mask)
    )

    water_before = mask_generator.mask_coverage_percent(before_mask)
    water_after = mask_generator.mask_coverage_percent(after_mask)
    new_water = mask_generator.mask_coverage_percent(new_water_mask)
    new_pixels = int(np.count_nonzero(new_water_mask))

    comparison = MaskComparison(
        new_water_mask=new_water_mask,
        water_before_percent=water_before,
        water_after_percent=water_after,
        new_water_percent=new_water,
        new_water_pixels=new_pixels,
        increase_percent=water_after - water_before,
    )
    logger.info(
        "Change detection: before=%.2f %%, after=%.2f %%, new=%.2f %% "
        "(%d px), net change=%+.2f pp",
        water_before,
        water_after,
        new_water,
        new_pixels,
        comparison.increase_percent,
    )
    return comparison


def _validate_pair(before_mask: MaskArray, after_mask: MaskArray) -> None:
    """Fail fast on contract violations of a mask pair.

    Args:
        before_mask: Pre-event mask candidate.
        after_mask: Post-event mask candidate.

    Raises:
        ValueError: If either array is not a 2-D uint8 mask or the two
            shapes differ.
    """
    for name, mask in (("before", before_mask), ("after", after_mask)):
        if mask.ndim != 2 or mask.dtype != np.uint8:
            raise ValueError(
                f"{name} mask must be 2-D uint8, "
                f"got ndim={mask.ndim}, dtype={mask.dtype}."
            )
    if before_mask.shape != after_mask.shape:
        raise ValueError(
            f"Mask shapes differ: before={before_mask.shape}, "
            f"after={after_mask.shape}. Image pairs must share dimensions."
        )
