"""Tests for water-mask change detection."""

import numpy as np
import pytest

from src.change_detection import compare_masks


def test_compare_masks_detects_new_water() -> None:
    """New water is present after the event but absent before."""
    before = np.array(
        [
            [0, 0],
            [0, 255],
        ],
        dtype=np.uint8,
    )
    after = np.array(
        [
            [255, 0],
            [0, 255],
        ],
        dtype=np.uint8,
    )

    result = compare_masks(
        before,
        after,
    )

    assert result.new_water_pixels == 1
    assert result.water_before_percent == pytest.approx(25.0)
    assert result.water_after_percent == pytest.approx(50.0)
    assert result.new_water_percent == pytest.approx(25.0)
    assert result.increase_percent == pytest.approx(25.0)

    np.testing.assert_array_equal(
        result.new_water_mask,
        np.array(
            [
                [255, 0],
                [0, 0],
            ],
            dtype=np.uint8,
        ),
    )


def test_compare_masks_excludes_invalid_pixels() -> None:
    """Invalid pixels do not affect masks or percentage calculations."""
    before = np.zeros(
        (2, 2),
        dtype=np.uint8,
    )
    after = np.array(
        [
            [255, 255],
            [0, 0],
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

    result = compare_masks(
        before,
        after,
        valid_mask=valid_mask,
    )

    assert result.new_water_pixels == 1
    assert result.water_before_percent == pytest.approx(0.0)
    assert result.water_after_percent == pytest.approx(100.0 / 3.0)
    assert result.new_water_percent == pytest.approx(100.0 / 3.0)
    assert result.increase_percent == pytest.approx(100.0 / 3.0)

    np.testing.assert_array_equal(
        result.new_water_mask,
        np.array(
            [
                [255, 0],
                [0, 0],
            ],
            dtype=np.uint8,
        ),
    )


def test_compare_masks_returns_zero_without_valid_pixels() -> None:
    """A fully invalid comparison produces empty statistics."""
    before = np.zeros(
        (2, 2),
        dtype=np.uint8,
    )
    after = np.full(
        (2, 2),
        255,
        dtype=np.uint8,
    )
    valid_mask = np.zeros(
        (2, 2),
        dtype=bool,
    )

    result = compare_masks(
        before,
        after,
        valid_mask=valid_mask,
    )

    assert result.new_water_pixels == 0
    assert result.water_before_percent == 0.0
    assert result.water_after_percent == 0.0
    assert result.new_water_percent == 0.0
    assert result.increase_percent == 0.0
    assert np.count_nonzero(result.new_water_mask) == 0


def test_compare_masks_rejects_wrong_valid_mask_shape() -> None:
    """The validity mask must match the water-mask dimensions."""
    before = np.zeros(
        (2, 2),
        dtype=np.uint8,
    )
    after = np.zeros(
        (2, 2),
        dtype=np.uint8,
    )
    valid_mask = np.ones(
        (3, 2),
        dtype=bool,
    )

    with pytest.raises(
        ValueError,
        match="Valid mask shape must match",
    ):
        compare_masks(
            before,
            after,
            valid_mask=valid_mask,
        )