"""Tests for spectral index calculations."""

import numpy as np
import pytest

from src.spectral_indices import calculate_mndwi, calculate_ndwi


def test_calculate_ndwi_returns_expected_values() -> None:
    """NDWI should be calculated correctly."""
    green = np.array([0.8, 0.6], dtype=np.float32)
    nir = np.array([0.2, 0.4], dtype=np.float32)

    result = calculate_ndwi(green, nir)

    expected = np.array([0.6, 0.2], dtype=np.float32)

    np.testing.assert_allclose(result, expected)


def test_calculate_ndwi_handles_zero_division() -> None:
    """Division by zero should not create NaN or infinity."""
    green = np.array([0.0], dtype=np.float32)
    nir = np.array([0.0], dtype=np.float32)

    result = calculate_ndwi(green, nir)

    assert result[0] == 0.0
    assert np.isfinite(result).all()


def test_calculate_ndwi_rejects_different_shapes() -> None:
    """Bands with different shapes should raise an error."""
    green = np.zeros((2, 2), dtype=np.float32)
    nir = np.zeros((3, 3), dtype=np.float32)

    with pytest.raises(ValueError):
        calculate_ndwi(green, nir)


def test_calculate_ndwi_limits_output_range() -> None:
    """NDWI output should stay inside the valid range."""
    green = np.array([10.0, -10.0], dtype=np.float32)
    nir = np.array([-10.0, 10.0], dtype=np.float32)

    result = calculate_ndwi(green, nir)

    assert np.all(result >= -1.0)
    assert np.all(result <= 1.0)


def test_calculate_mndwi_returns_expected_values() -> None:
    """MNDWI should be calculated correctly."""
    green = np.array([0.8, 0.6], dtype=np.float32)
    swir = np.array([0.2, 0.4], dtype=np.float32)

    result = calculate_mndwi(green, swir)

    expected = np.array([0.6, 0.2], dtype=np.float32)

    np.testing.assert_allclose(result, expected)


def test_calculate_mndwi_handles_zero_division() -> None:
    """Division by zero should not create NaN or infinity."""
    green = np.array([0.0], dtype=np.float32)
    swir = np.array([0.0], dtype=np.float32)

    result = calculate_mndwi(green, swir)

    assert result[0] == 0.0
    assert np.isfinite(result).all()


def test_calculate_mndwi_rejects_different_shapes() -> None:
    """Bands with different shapes should raise an error."""
    green = np.zeros((2, 2), dtype=np.float32)
    swir = np.zeros((3, 3), dtype=np.float32)

    with pytest.raises(ValueError):
        calculate_mndwi(green, swir)