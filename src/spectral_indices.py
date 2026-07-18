"""Spectral index calculations for multispectral raster data."""

from __future__ import annotations

import numpy as np


def calculate_ndwi(
    green: np.ndarray,
    nir: np.ndarray,
) -> np.ndarray:
    """Calculate the Normalized Difference Water Index (NDWI).

    NDWI is calculated as:

        (green - nir) / (green + nir)

    Pixels with a zero denominator are returned as NaN.
    """
    if green.ndim != 2 or nir.ndim != 2:
        raise ValueError("NDWI input bands must be two-dimensional.")

    if green.shape != nir.shape:
        raise ValueError("NDWI input bands must have the same shape.")

    green_float = green.astype(np.float32, copy=False)
    nir_float = nir.astype(np.float32, copy=False)

    numerator = green_float - nir_float
    denominator = green_float + nir_float

    result = np.full(green.shape, np.nan, dtype=np.float32)

    valid = denominator != 0
    result[valid] = numerator[valid] / denominator[valid]

    return result