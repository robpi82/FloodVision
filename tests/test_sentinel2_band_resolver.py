"""Tests for Sentinel-2 raster band resolution."""

from __future__ import annotations

import pytest

from src.sentinel2_band_resolver import Sentinel2BandResolver


def test_resolver_returns_rgb_indices_from_raster_band_order() -> None:
    """RGB indices are resolved from the actual Sentinel-2 band order."""
    resolver = Sentinel2BandResolver()

    indices = resolver.resolve_rgb_indices(
        ("B08", "B04", "B03", "B02"),
    )

    assert indices == (1, 2, 3)


def test_resolver_supports_partially_missing_band_descriptions() -> None:
    """RGB indices are resolved despite unrelated missing descriptions."""
    resolver = Sentinel2BandResolver()

    indices = resolver.resolve_rgb_indices(
        ("B08", "B04", "B03", "B02", None),
    )

    assert indices == (1, 2, 3)


def test_resolver_rejects_missing_required_rgb_band() -> None:
    """Missing required RGB bands raise a clear error."""
    resolver = Sentinel2BandResolver()

    with pytest.raises(
        ValueError,
        match="Required Sentinel-2 band B04 is not available in raster bands",
    ):
        resolver.resolve_rgb_indices(
            ("B08", "B11", "B12"),
        )