"""Tests for spectral index calculations."""

import numpy as np
import pytest

from src.spectral_indices import calculate_mndwi, calculate_ndwi


def test_calculate_ndwi_returns_expected_values() -> None:
    """NDWI should be calculated correctly."""
    green = np.array(
        [
            [900.0, 800.0],
            [500.0, 1000.0],
        ],
        dtype=np.float32,
    )
    nir = np.array(
        [
            [100.0, 1200.0],
            [500.0, 0.0],
        ],
        dtype=np.float32,
    )

    result = calculate_ndwi(green, nir)

    expected = np.array(
        [
            [0.8, -0.2],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )

    np.testing.assert_allclose(result, expected)


def test_calculate_ndwi_returns_nan_when_denominator_is_zero() -> None:
    """Zero denominator should produce NaN."""
    green = np.array([[0.0]], dtype=np.float32)
    nir = np.array([[0.0]], dtype=np.float32)

    result = calculate_ndwi(green, nir)

    assert np.isnan(result[0, 0])


def test_calculate_ndwi_rejects_different_shapes() -> None:
    """Bands with different shapes should raise an error."""
    green = np.zeros((2, 2), dtype=np.float32)
    nir = np.zeros((3, 3), dtype=np.float32)

    with pytest.raises(ValueError, match="same shape"):
        calculate_ndwi(green, nir)


def test_calculate_ndwi_applies_valid_mask() -> None:
    """Invalid raster pixels should be returned as NaN."""
    green = np.array(
        [
            [900.0, 800.0],
            [500.0, 1000.0],
        ],
        dtype=np.float32,
    )
    nir = np.array(
        [
            [100.0, 1200.0],
            [500.0, 0.0],
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

    result = calculate_ndwi(
        green,
        nir,
        valid_mask=valid_mask,
    )

    assert np.isclose(result[0, 0], 0.8)
    assert np.isnan(result[0, 1])
    assert np.isclose(result[1, 0], 0.0)
    assert np.isclose(result[1, 1], 1.0)


def test_calculate_ndwi_rejects_different_valid_mask_shape() -> None:
    """Valid-data mask must match the spectral band dimensions."""
    green = np.zeros((2, 2), dtype=np.float32)
    nir = np.zeros((2, 2), dtype=np.float32)
    valid_mask = np.ones((3, 3), dtype=bool)

    with pytest.raises(ValueError, match="valid mask must have the same shape"):
        calculate_ndwi(
            green,
            nir,
            valid_mask=valid_mask,
        )


def test_calculate_mndwi_returns_expected_values() -> None:
    """MNDWI should be calculated correctly."""
    green = np.array([[0.8, 0.6]], dtype=np.float32)
    swir = np.array([[0.2, 0.4]], dtype=np.float32)

    result = calculate_mndwi(green, swir)

    expected = np.array([[0.6, 0.2]], dtype=np.float32)

    np.testing.assert_allclose(result, expected)


def test_calculate_mndwi_handles_zero_division() -> None:
    """Division by zero should not create NaN or infinity."""
    green = np.array([[0.0]], dtype=np.float32)
    swir = np.array([[0.0]], dtype=np.float32)

    result = calculate_mndwi(green, swir)

    assert result[0, 0] == 0.0
    assert np.isfinite(result).all()


def test_calculate_mndwi_rejects_different_shapes() -> None:
    """Bands with different shapes should raise an error."""
    green = np.zeros((2, 2), dtype=np.float32)
    swir = np.zeros((3, 3), dtype=np.float32)

    with pytest.raises(ValueError, match="same shape"):
        calculate_mndwi(green, swir)