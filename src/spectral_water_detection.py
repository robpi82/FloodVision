"""Water detection from multispectral spectral indices."""

from __future__ import annotations

import numpy as np

from src import mask_generator


def ndwi_to_mask(
    ndwi: np.ndarray,
    threshold: float = 0.1,
    clean: bool = False,
    valid_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Convert a spectral index raster into a binary water mask.

    Invalid raster pixels are always classified as non-water.

    Args:
        ndwi: Two-dimensional spectral index raster.
        threshold: Minimum index value classified as water.
        clean: Whether morphological mask cleanup should be applied.
        valid_mask: Optional two-dimensional validity mask. ``True`` marks
            pixels that may be classified; ``False`` marks invalid or NoData
            pixels.

    Returns:
        Binary uint8 mask where 255 represents water and 0 represents
        non-water.

    Raises:
        ValueError: If the index raster is not two-dimensional or if the
            validity mask does not have the same shape.
    """
    if ndwi.ndim != 2:
        raise ValueError(
            "NDWI raster must be a two-dimensional array."
        )

    if valid_mask is None:
        valid_pixels = np.ones(ndwi.shape, dtype=bool)
    else:
        if valid_mask.shape != ndwi.shape:
            raise ValueError(
                "Valid mask and spectral index raster must have the same shape."
            )

        valid_pixels = valid_mask.astype(bool, copy=False)

    mask = np.zeros(
        ndwi.shape,
        dtype=np.uint8,
    )

    water_pixels = valid_pixels & (ndwi > threshold)
    mask[water_pixels] = mask_generator.WATER_VALUE

    if clean:
        mask = mask_generator.clean_mask(mask)

        # Morphological operations can expand white areas into adjacent
        # invalid pixels, so enforce the validity mask again afterwards.
        mask[~valid_pixels] = 0

    return mask


def spectral_water_coverage_percent(
    mask: np.ndarray,
    valid_mask: np.ndarray | None = None,
) -> float:
    """Return water coverage as a percentage of valid raster pixels.

    Args:
        mask: Binary water mask.
        valid_mask: Optional validity mask. Invalid pixels are excluded from
            the percentage denominator.

    Returns:
        Percentage of valid pixels classified as water. Returns ``0.0`` when
        no pixels are valid.

    Raises:
        ValueError: If the validity mask does not have the same shape as the
            water mask.
    """
    if valid_mask is None:
        return mask_generator.mask_coverage_percent(mask)

    if valid_mask.shape != mask.shape:
        raise ValueError(
            "Valid mask and water mask must have the same shape."
        )

    valid_pixels = valid_mask.astype(bool, copy=False)
    valid_pixel_count = int(np.count_nonzero(valid_pixels))

    if valid_pixel_count == 0:
        return 0.0

    water_pixel_count = int(
        np.count_nonzero(
            (mask == mask_generator.WATER_VALUE) & valid_pixels
        )
    )

    return 100.0 * water_pixel_count / valid_pixel_count