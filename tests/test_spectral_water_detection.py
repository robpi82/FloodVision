"""Tests for spectral water detection."""

import numpy as np
import pytest

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

    with pytest.raises(ValueError, match="two-dimensional"):
        ndwi_to_mask(ndwi)


def test_invalid_pixels_are_excluded_from_water_mask() -> None:
    """Invalid raster pixels must never be classified as water."""
    ndwi = np.array(
        [
            [0.8, 0.8],
            [-0.2, 0.4],
        ],
        dtype=np.float32,
    )
    valid_mask = np.array(
        [
            [True, False],
            [True, True],
        ],
        dtype=bool,
    )

    mask = ndwi_to_mask(
        ndwi,
        threshold=0.1,
        valid_mask=valid_mask,
    )

    assert mask[0, 0] == 255
    assert mask[0, 1] == 0
    assert mask[1, 0] == 0
    assert mask[1, 1] == 255


def test_coverage_uses_only_valid_pixels() -> None:
    """Invalid pixels must not contribute to the coverage denominator."""
    mask = np.array(
        [
            [255, 0],
            [0, 255],
        ],
        dtype=np.uint8,
    )
    valid_mask = np.array(
        [
            [True, False],
            [True, True],
        ],
        dtype=bool,
    )

    coverage = spectral_water_coverage_percent(
        mask,
        valid_mask=valid_mask,
    )

    assert coverage == pytest.approx(200.0 / 3.0)


def test_valid_mask_must_match_index_shape() -> None:
    """A differently shaped validity mask is rejected."""
    ndwi = np.zeros((2, 2), dtype=np.float32)
    valid_mask = np.ones((3, 3), dtype=bool)

    with pytest.raises(ValueError, match="same shape"):
        ndwi_to_mask(
            ndwi,
            valid_mask=valid_mask,
        )


def test_coverage_returns_zero_when_no_pixels_are_valid() -> None:
    """Coverage is zero when the raster contains no valid pixels."""
    mask = np.full((2, 2), 255, dtype=np.uint8)
    valid_mask = np.zeros((2, 2), dtype=bool)

    coverage = spectral_water_coverage_percent(
        mask,
        valid_mask=valid_mask,
    )

    assert coverage == 0.0