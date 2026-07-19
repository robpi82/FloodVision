"""Change detection: comparison of before/after water masks.

This module answers exactly one question: *which water is new?* It
consumes two binary water masks and remains independent of how those
masks were produced.

Core definition:
    A pixel counts as newly flooded if it is water in the AFTER mask
    and non-water in the BEFORE mask.

When a validity mask is supplied, only pixels valid in both observations
are included in the output mask and statistical calculations.
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
    """Immutable result of comparing two water masks.

    Attributes:
        new_water_mask: Binary mask with newly flooded pixels.
        water_before_percent: Water coverage before the event.
        water_after_percent: Water coverage after the event.
        new_water_percent: Percentage of valid pixels newly flooded.
        new_water_pixels: Absolute count of newly flooded valid pixels.
        increase_percent: Net coverage change in percentage points.
    """

    new_water_mask: MaskArray
    water_before_percent: float
    water_after_percent: float
    new_water_percent: float
    new_water_pixels: int
    increase_percent: float


def compare_masks(
    before_mask: MaskArray,
    after_mask: MaskArray,
    valid_mask: np.ndarray | None = None,
) -> MaskComparison:
    """Detect newly flooded pixels between two binary water masks.

    The new-flood mask is calculated as::

        AFTER AND (NOT BEFORE)

    When ``valid_mask`` is provided, only pixels marked as valid are used
    for the output mask and all percentage calculations.

    Args:
        before_mask: Binary pre-event water mask using values 0 and 255.
        after_mask: Binary post-event water mask using values 0 and 255.
        valid_mask: Optional boolean mask defining pixels valid in both
            observations. ``None`` means every pixel is valid.

    Returns:
        Structured flood-change result.

    Raises:
        ValueError: If mask dimensions or data types are invalid, or if the
            validity mask does not match the water-mask dimensions.
    """
    _validate_pair(
        before_mask,
        after_mask,
    )

    if valid_mask is None:
        valid_pixels = np.ones(
            before_mask.shape,
            dtype=bool,
        )
    else:
        if valid_mask.shape != before_mask.shape:
            raise ValueError(
                "Valid mask shape must match water-mask shape: "
                f"valid={valid_mask.shape}, mask={before_mask.shape}."
            )

        valid_pixels = valid_mask.astype(
            bool,
            copy=False,
        )

    new_water_mask: MaskArray = cv2.bitwise_and(
        after_mask,
        cv2.bitwise_not(before_mask),
    )

    new_water_mask = new_water_mask.copy()
    new_water_mask[~valid_pixels] = 0

    valid_count = int(
        np.count_nonzero(valid_pixels)
    )

    if valid_count == 0:
        water_before = 0.0
        water_after = 0.0
        new_water = 0.0
        new_pixels = 0
    else:
        before_water_pixels = int(
            np.count_nonzero(
                (before_mask == mask_generator.WATER_VALUE)
                & valid_pixels
            )
        )

        after_water_pixels = int(
            np.count_nonzero(
                (after_mask == mask_generator.WATER_VALUE)
                & valid_pixels
            )
        )

        new_pixels = int(
            np.count_nonzero(
                (new_water_mask == mask_generator.WATER_VALUE)
                & valid_pixels
            )
        )

        water_before = (
            100.0
            * before_water_pixels
            / valid_count
        )

        water_after = (
            100.0
            * after_water_pixels
            / valid_count
        )

        new_water = (
            100.0
            * new_pixels
            / valid_count
        )

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


def _validate_pair(
    before_mask: MaskArray,
    after_mask: MaskArray,
) -> None:
    """Validate a pair of binary water masks.

    Args:
        before_mask: Pre-event mask candidate.
        after_mask: Post-event mask candidate.

    Raises:
        ValueError: If either mask is not a two-dimensional uint8 array or
            if the two masks have different dimensions.
    """
    for name, mask in (
        ("before", before_mask),
        ("after", after_mask),
    ):
        if mask.ndim != 2 or mask.dtype != np.uint8:
            raise ValueError(
                f"{name} mask must be 2-D uint8, "
                f"got ndim={mask.ndim}, dtype={mask.dtype}."
            )

    if before_mask.shape != after_mask.shape:
        raise ValueError(
            f"Mask shapes differ: before={before_mask.shape}, "
            f"after={after_mask.shape}. "
            "Image pairs must share dimensions."
        )