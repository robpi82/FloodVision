"""Tests for multispectral band configuration validation."""

from __future__ import annotations

import pytest

from src.config import MULTISPECTRAL_RGB_BANDS, validate_rgb_bands
from src.exceptions import ConfigurationError




def test_valid_rgb_bands_are_converted_to_tuple():
    result = validate_rgb_bands([3, 2, 1])

    assert result == (3, 2, 1)


def test_rgb_bands_require_exactly_three_entries():
    with pytest.raises(ConfigurationError, match="three integers"):
        validate_rgb_bands([3, 2])


@pytest.mark.parametrize(
    "value",
    [
        [3, 2, 1, 0],
        [],
        "3,2,1",
        None,
    ],
)
def test_rgb_bands_reject_invalid_structure(value):
    with pytest.raises(ConfigurationError, match="three integers"):
        validate_rgb_bands(value)


@pytest.mark.parametrize(
    "value",
    [
        [3, 2, 1.5],
        [3, "2", 1],
        [True, 2, 1],
    ],
)
def test_rgb_bands_reject_non_integer_entries(value):
    with pytest.raises(ConfigurationError, match="integer"):
        validate_rgb_bands(value)


def test_rgb_bands_reject_negative_indices():
    with pytest.raises(ConfigurationError, match="non-negative"):
        validate_rgb_bands([3, -1, 1])


def test_rgb_bands_preserve_requested_order():
    result = validate_rgb_bands([1, 3, 2])

    assert result == (1, 3, 2)

def test_multispectral_rgb_bands_are_loaded_from_configuration():
    assert MULTISPECTRAL_RGB_BANDS == (0, 1, 2)