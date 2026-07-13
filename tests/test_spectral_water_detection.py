"""Tests for spectral water detection."""

import numpy as np

from src.spectral_water_detection import (
    ndwi_to_mask,
    spectral_water_coverage_percent,
)


def test_ndwi_above_threshold_is_water() -> None:
    """Pixels above threshold become water pixels."""
    ndwi = np.array(
        [
            [0.2, -0.1],
            [0.5, 0.0],
        ],
        dtype=np.float32,
    )

    mask = ndwi_to_mask(
        ndwi,
        threshold=0.1,
    )

    assert mask[0, 0] == 255
    assert mask[1, 0] == 255
    assert mask[0, 1] == 0
    assert mask[1, 1] == 0


def test_ndwi_mask_has_expected_coverage() -> None:
    """Coverage calculation uses the generated water mask."""
    ndwi = np.array(
        [
            [0.2, -0.1],
            [0.5, 0.0],
        ],
        dtype=np.float32,
    )

    mask = ndwi_to_mask(
        ndwi,
        threshold=0.1,
    )

    coverage = spectral_water_coverage_percent(mask)

    assert coverage == 50.0


def test_ndwi_requires_two_dimensions() -> None:
    """Three-dimensional input is rejected."""
    ndwi = np.zeros(
        (2, 2, 1),
        dtype=np.float32,
    )

    try:
        ndwi_to_mask(ndwi)
    except ValueError as error:
        assert "two-dimensional" in str(error)
    else:
        raise AssertionError(
            "Expected ValueError for invalid NDWI dimensions"
        )