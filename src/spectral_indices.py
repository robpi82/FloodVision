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
) -> np.ndarray:
    """Calculate the Normalized Difference Water Index (NDWI).

    Args:
        green: Green spectral band.
        nir: Near Infrared (NIR) spectral band.

    Returns:
        NDWI values as a floating-point NumPy array.

    Raises:
        ValueError: If the input arrays do not have the same shape.
    """
    if green.shape != nir.shape:
        raise ValueError("Green and NIR bands must have the same shape.")

    green = green.astype(np.float32)
    nir = nir.astype(np.float32)

    with np.errstate(divide="ignore", invalid="ignore"):
        ndwi = (green - nir) / (green + nir)

    ndwi = np.nan_to_num(
        ndwi,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    return np.clip(ndwi, -1.0, 1.0)


def calculate_mndwi(
    green: np.ndarray,
    swir: np.ndarray,
) -> np.ndarray:
    """Calculate the Modified Normalized Difference Water Index (MNDWI).

    Formula:
        MNDWI = (Green - SWIR) / (Green + SWIR)

    Args:
        green: Green spectral band.
        swir: Short-Wave Infrared (SWIR) spectral band.

    Returns:
        MNDWI values as a floating-point NumPy array.

    Raises:
        ValueError: If the input arrays do not have the same shape.
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