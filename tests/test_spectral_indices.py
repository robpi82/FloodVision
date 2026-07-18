import numpy as np

from src.spectral_indices import calculate_ndwi


def test_calculate_ndwi_returns_expected_values() -> None:
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
    green = np.array([[0.0]], dtype=np.float32)
    nir = np.array([[0.0]], dtype=np.float32)

    result = calculate_ndwi(green, nir)

    assert np.isnan(result[0, 0])


def test_calculate_ndwi_rejects_different_shapes() -> None:
    green = np.zeros((2, 2), dtype=np.float32)
    nir = np.zeros((3, 3), dtype=np.float32)

    try:
        calculate_ndwi(green, nir)
    except ValueError as error:
        assert "same shape" in str(error)
    else:
        raise AssertionError("Expected ValueError for mismatched band shapes")