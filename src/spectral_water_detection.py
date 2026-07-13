"""Water detection from multispectral spectral indices."""

from __future__ import annotations

import numpy as np

from src import mask_generator


def ndwi_to_mask(
    ndwi: np.ndarray,
    threshold: float = 0.1,
    clean: bool = False,
) -> np.ndarray:
    """Convert an NDWI raster into a binary water mask.

    Args:
        ndwi: NDWI floating point raster.
        threshold: Minimum NDWI value classified as water.
        clean: Apply morphological mask cleanup.

    Returns:
        Binary uint8 mask:
            255 = water
             0 = non-water
    """
    if ndwi.ndim != 2:
        raise ValueError(
            "NDWI raster must be a two-dimensional array."
        )

    mask = np.zeros(
        ndwi.shape,
        dtype=np.uint8,
    )

    mask[ndwi > threshold] = mask_generator.WATER_VALUE

    if clean:
        return mask_generator.clean_mask(mask)

    return mask
    if ndwi.ndim != 2:
        raise ValueError(
            "NDWI raster must be a two-dimensional array."
        )

    mask = np.zeros(
        ndwi.shape,
        dtype=np.uint8,
    )

    mask[ndwi > threshold] = mask_generator.WATER_VALUE

    return mask_generator.clean_mask(mask)


def spectral_water_coverage_percent(
    mask: np.ndarray,
) -> float:
    """Return water coverage percentage of a spectral mask."""
    return mask_generator.mask_coverage_percent(mask)