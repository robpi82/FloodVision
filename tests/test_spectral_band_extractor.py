"""Tests for spectral band extraction."""

from pathlib import Path

import numpy as np

from src.geotiff_raster_loader import GeoTiffRasterData
from src.spectral_band_extractor import get_spectral_band


def create_test_raster() -> GeoTiffRasterData:
    """Create a small Sentinel-2-like raster for testing."""
    return GeoTiffRasterData(
        path=Path("test.tif"),
        data=np.array(
            [
                [[1, 2], [3, 4]],       # B02
                [[5, 6], [7, 8]],       # B03
                [[9, 10], [11, 12]],    # B04
                [[13, 14], [15, 16]],   # B08
            ],
            dtype=np.uint16,
        ),
        valid_mask=np.ones((2, 2), dtype=bool),
        nodata=None,
        band_descriptions=(
            "B02",
            "B03",
            "B04",
            "B08",
        ),
    )


def test_extracts_requested_sentinel2_band() -> None:
    """The requested band is returned as a two-dimensional array."""
    raster = create_test_raster()

    result = get_spectral_band(raster, "B03")

    expected = np.array(
        [
            [5, 6],
            [7, 8],
        ],
        dtype=np.uint16,
    )

    np.testing.assert_array_equal(result, expected)


def test_band_lookup_is_case_insensitive() -> None:
    """Band codes should work regardless of letter casing."""
    raster = create_test_raster()

    result = get_spectral_band(raster, "b08")

    expected = np.array(
        [
            [13, 14],
            [15, 16],
        ],
        dtype=np.uint16,
    )

    np.testing.assert_array_equal(result, expected)


def test_missing_band_raises_value_error() -> None:
    """Requesting an unavailable band fails clearly."""
    raster = create_test_raster()

    try:
        get_spectral_band(raster, "B11")
    except ValueError as error:
        assert "B11" in str(error)
    else:
        raise AssertionError("Expected ValueError for missing band")