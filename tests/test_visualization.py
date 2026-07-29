"""Tests for :mod:`src.visualization`.

Focus: :func:`colorize_spectral_index`, the false-colour rendering added
for NDWI/MNDWI visualization. The other functions in this module either
predate this feature or are exercised indirectly through batch-processor
integration tests.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.visualization import SPECTRAL_INDEX_NO_DATA_COLOR, colorize_spectral_index


def test_colorize_spectral_index_returns_rgb_uint8() -> None:
    """Output is an (H, W, 3) uint8 array regardless of input dtype."""
    index = np.zeros((4, 5), dtype=np.float32)

    rgb = colorize_spectral_index(index)

    assert rgb.shape == (4, 5, 3)
    assert rgb.dtype == np.uint8


def test_high_index_renders_differently_from_low_index() -> None:
    """A water-like (+1) and land-like (-1) pixel must render as distinct colours.

    This is the whole point of a diverging colormap: sign, not just
    magnitude, must be visually distinguishable.
    """
    index = np.array([[1.0, -1.0]], dtype=np.float32)

    rgb = colorize_spectral_index(index)

    assert not np.array_equal(rgb[0, 0], rgb[0, 1])


def test_nan_pixels_render_as_no_data_color() -> None:
    """NaN entries (e.g. zero-denominator NDWI pixels) get the no-data colour."""
    index = np.array([[0.5, np.nan]], dtype=np.float32)

    rgb = colorize_spectral_index(index)

    np.testing.assert_array_equal(rgb[0, 1], SPECTRAL_INDEX_NO_DATA_COLOR)


def test_invalid_mask_pixels_render_as_no_data_color_regardless_of_value() -> None:
    """A pixel marked invalid renders as no-data even with a plausible index value."""
    index = np.array([[0.8, 0.8]], dtype=np.float32)
    valid_mask = np.array([[True, False]])

    rgb = colorize_spectral_index(index, valid_mask=valid_mask)

    np.testing.assert_array_equal(rgb[0, 1], SPECTRAL_INDEX_NO_DATA_COLOR)
    assert not np.array_equal(rgb[0, 0], np.array(SPECTRAL_INDEX_NO_DATA_COLOR))


def test_rejects_non_two_dimensional_input() -> None:
    """A non-2D raster is a programming error, not silently reshaped."""
    index = np.zeros((2, 3, 3), dtype=np.float32)

    with pytest.raises(ValueError, match="two-dimensional"):
        colorize_spectral_index(index)


def test_rejects_mismatched_valid_mask_shape() -> None:
    """The valid mask must match the index raster's shape."""
    index = np.zeros((2, 2), dtype=np.float32)
    valid_mask = np.ones((3, 3), dtype=bool)

    with pytest.raises(ValueError, match="same shape"):
        colorize_spectral_index(index, valid_mask=valid_mask)


def test_out_of_range_values_are_clipped_not_rejected() -> None:
    """Values slightly outside [-1, 1] (e.g. floating-point noise) are clipped."""
    index = np.array([[1.5, -1.5]], dtype=np.float32)

    rgb = colorize_spectral_index(index)

    # Should not raise, and the extreme values should match the clipped bounds.
    clipped = colorize_spectral_index(np.array([[1.0, -1.0]], dtype=np.float32))
    np.testing.assert_array_equal(rgb, clipped)
