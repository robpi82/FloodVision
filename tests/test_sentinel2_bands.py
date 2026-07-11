"""Tests for Sentinel-2 band metadata."""

from __future__ import annotations

import pytest

from src.sentinel2_bands import (
    Sentinel2Band,
    get_sentinel2_band,
    get_sentinel2_band_indices,
)

@pytest.mark.parametrize(
    ("code", "name", "resolution_m"),
    [
        ("B02", "Blue", 10),
        ("B03", "Green", 10),
        ("B04", "Red", 10),
        ("B05", "Vegetation Red Edge", 20),
        ("B06", "Vegetation Red Edge", 20),
        ("B07", "Vegetation Red Edge", 20),
        ("B08", "Near Infrared", 10),
        ("B8A", "Narrow Near Infrared", 20),
        ("B09", "Water Vapour", 60),
        ("B10", "Cirrus", 60),
        ("B11", "Short-Wave Infrared", 20),
        ("B12", "Short-Wave Infrared", 20),
    ],
)
def test_supported_band_metadata(
    code: str,
    name: str,
    resolution_m: int,
) -> None:
    """Supported bands expose the expected Sentinel-2 metadata."""
    band = get_sentinel2_band(code)

    assert band.code == code
    assert band.name == name
    assert band.resolution_m == resolution_m


def test_band_lookup_is_case_insensitive() -> None:
    """Band codes can be looked up regardless of letter case."""
    band = get_sentinel2_band("b04")

    assert band.code == "B04"


def test_band_lookup_strips_whitespace() -> None:
    """Whitespace around a band code is ignored."""
    band = get_sentinel2_band("  B08  ")

    assert band.code == "B08"


def test_unknown_band_is_rejected() -> None:
    """Unknown Sentinel-2 band codes raise a clear error."""
    with pytest.raises(ValueError, match="Unknown Sentinel-2 band"):
        get_sentinel2_band("B99")


def test_band_metadata_is_immutable() -> None:
    """Sentinel-2 band metadata records are immutable."""
    band = Sentinel2Band(
        code="B02",
        name="Blue",
        resolution_m=10,
    )

    with pytest.raises(AttributeError):
        band.name = "Changed"


def test_sentinel2_band_codes_are_converted_to_raster_indices() -> None:
    """Sentinel-2 band codes are converted to zero-based raster indices."""
    indices = get_sentinel2_band_indices(("B04", "B03", "B02"))

    assert indices == (2, 1, 0)