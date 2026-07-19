"""Extraction of spectral bands from loaded raster data."""

from __future__ import annotations

import numpy as np

from src.geotiff_raster_loader import GeoTiffRasterData
from src.sentinel2_bands import get_sentinel2_band_indices


def get_spectral_band(
    raster: GeoTiffRasterData,
    band_code: str,
) -> np.ndarray:
    """Return one spectral band from a loaded raster.

    Args:
        raster: Loaded GeoTIFF raster data.
        band_code: Sentinel-2 band code, e.g. "B03" or "B08".

    Returns:
        Two-dimensional pixel array of the requested band.

    Raises:
        ValueError: If the requested band is not available.
    """
    index = get_sentinel2_band_indices(
        (band_code,),
        available_codes=raster.band_descriptions,
    )[0]

    return raster.data[index]