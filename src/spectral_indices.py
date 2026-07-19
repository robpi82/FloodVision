"""Mathematical spectral index calculations.

This module contains pure mathematical functions for calculating spectral
indices. It is intentionally independent from GeoTIFF loading, OpenCV,
and water detection so the functions can be reused throughout the project.
"""

from __future__ import annotations

import numpy as np


def calculate_ndwi(
    green: np.ndarray,
    nir: np.ndarray,
    valid_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Calculate the Normalized Difference Water Index (NDWI).

    Pixels with a zero denominator are returned as NaN.
    If a valid-data mask is supplied, invalid pixels are also returned as NaN.
    """
    if green.shape != nir.shape:
        raise ValueError("Green and NIR bands must have the same shape.")

    if valid_mask is not None and valid_mask.shape != green.shape:
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

    return np.clip(result, -1.0, 1.0)


def calculate_mndwi(
    green: np.ndarray,
    swir: np.ndarray,
) -> np.ndarray:
    """Calculate the Modified Normalized Difference Water Index (MNDWI).

    Formula:
        MNDWI = (Green - SWIR) / (Green + SWIR)
    """
    if green.shape != swir.shape:
        raise ValueError("Green and SWIR bands must have the same shape.")

    green = green.astype(np.float32)
    swir = swir.astype(np.float32)

    with np.errstate(divide="ignore", invalid="ignore"):
        mndwi = (green - swir) / (green + swir)

    mndwi = np.nan_to_num(
        mndwi,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    return np.clip(mndwi, -1.0, 1.0)