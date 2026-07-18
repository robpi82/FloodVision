"""Spectral index calculations for multispectral raster data."""

from __future__ import annotations

import numpy as np


def calculate_ndwi(
    green: np.ndarray,
    nir: np.ndarray,
    valid_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Calculate the Normalized Difference Water Index (NDWI).

    NDWI is calculated as:

        (green - nir) / (green + nir)

    Pixels with a zero denominator are returned as NaN.
    If a valid-data mask is supplied, invalid pixels are also returned as NaN.
    """
    if green.ndim != 2 or nir.ndim != 2:
        raise ValueError("NDWI input bands must be two-dimensional.")

    if green.shape != nir.shape:
        raise ValueError("NDWI input bands must have the same shape.")

    if valid_mask is not None:
        if valid_mask.ndim != 2:
            raise ValueError("NDWI valid mask must be two-dimensional.")

        if valid_mask.shape != green.shape:
            raise ValueError(
                "NDWI valid mask must have the same shape as the input bands."
            )

    green_float = green.astype(np.float32, copy=False)
    nir_float = nir.astype(np.float32, copy=False)

    numerator = green_float - nir_float
    denominator = green_float + nir_float

    result = np.full(green.shape, np.nan, dtype=np.float32)

    valid = denominator != 0

    if valid_mask is not None:
        valid &= valid_mask.astype(bool, copy=False)

    result[valid] = numerator[valid] / denominator[valid]

    return result