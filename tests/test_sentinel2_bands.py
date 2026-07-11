"""Tests for Sentinel-2 band metadata."""

from __future__ import annotations

import pytest

from src.sentinel2_bands import (
    Sentinel2Band,
    get_sentinel2_band,
)


def test_b02_metadata() -> None:
    """B02 exposes the expected Sentinel-2 blue-band metadata."""
    band = get_sentinel2_band("B02")

    assert band.code == "B02"
    assert band.name == "Blue"
    assert band.resolution_m == 10


def test_b03_metadata() -> None:
    """B03 exposes the expected Sentinel-2 green-band metadata."""
    band = get_sentinel2_band("B03")

    assert band.code == "B03"
    assert band.name == "Green"
    assert band.resolution_m == 10


def test_b04_metadata() -> None:
    """B04 exposes the expected Sentinel-2 red-band metadata."""
    band = get_sentinel2_band("B04")

    assert band.code == "B04"
    assert band.name == "Red"
    assert band.resolution_m == 10


def test_b05_metadata() -> None:
    """B05 exposes the expected Sentinel-2 red-edge metadata."""
    band = get_sentinel2_band("B05")

    assert band.code == "B05"
    assert band.name == "Vegetation Red Edge"
    assert band.resolution_m == 20


def test_b06_metadata() -> None:
    """B06 exposes the expected Sentinel-2 red-edge metadata."""
    band = get_sentinel2_band("B06")

    assert band.code == "B06"
    assert band.name == "Vegetation Red Edge"
    assert band.resolution_m == 20


def test_b07_metadata() -> None:
    """B07 exposes the expected Sentinel-2 red-edge metadata."""
    band = get_sentinel2_band("B07")

    assert band.code == "B07"
    assert band.name == "Vegetation Red Edge"
    assert band.resolution_m == 20


def test_b08_metadata() -> None:
    """B08 exposes the expected Sentinel-2 NIR-band metadata."""
    band = get_sentinel2_band("B08")

    assert band.code == "B08"
    assert band.name == "Near Infrared"
    assert band.resolution_m == 10


def test_b8a_metadata() -> None:
    """B8A exposes the expected Sentinel-2 narrow NIR-band metadata."""
    band = get_sentinel2_band("B8A")

    assert band.code == "B8A"
    assert band.name == "Narrow Near Infrared"
    assert band.resolution_m == 20


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