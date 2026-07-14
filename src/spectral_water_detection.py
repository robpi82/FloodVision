"""Water detection from multispectral spectral indices."""

from __future__ import annotations

import numpy as np

from src import mask_generator


def ndwi_to_mask(
    ndwi: np.ndarray,
    threshold: float = 0.1,
    clean: bool = False,
) -> np.ndarray:
    """Convert a spectral index raster into a binary water mask.

    Args:
        ndwi: Two-dimensional spectral index raster.
        threshold: Minimum index value classified as water.
        clean: Whether morphological mask cleanup should be applied.

    Returns:
        Binary uint8 mask where 255 represents water and 0 represents
        non-water.

    Raises:
        ValueError: If the spectral index raster is not two-dimensional.
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


def spectral_water_coverage_percent(
    mask: np.ndarray,
) -> float:
    """Return the water coverage percentage of a spectral mask."""
    return mask_generator.mask_coverage_percent(mask)