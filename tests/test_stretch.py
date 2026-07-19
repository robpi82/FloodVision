"""Tests for shared value stretching across raster pairs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.geotiff_image_adapter import GeoTiffImageAdapter
from src.geotiff_raster_loader import GeoTiffRasterData
from src.stretch import Stretch, compute_shared_stretch


def make_raster(
    data: np.ndarray,
    *,
    name: str = "raster.tif",
    valid_mask: np.ndarray | None = None,
    nodata: float | None = None,
    band_descriptions: tuple[str | None, ...] | None = None,
) -> GeoTiffRasterData:
    """Build a raster payload in memory, without touching the file system.

    The stretch logic operates purely on pixel values and the valid-data mask,
    so a synthetic payload is sufficient. It also keeps every test explicit
    about the exact pixel values it depends on.

    Args:
        data: Band-first pixel array of shape ``(bands, height, width)``.
        name: File name used for the (never read) raster path.
        valid_mask: Two-dimensional validity mask; all pixels valid when
            omitted.
        nodata: NoData value of the source raster.
        band_descriptions: One description per band; all ``None`` when omitted.

    Returns:
        A raster payload equivalent to one loaded from a GeoTIFF.
    """
    if valid_mask is None:
        valid_mask = np.ones(data.shape[1:], dtype=bool)

    if band_descriptions is None:
        band_descriptions = (None,) * int(data.shape[0])

    return GeoTiffRasterData(
        path=Path(name),
        data=data,
        valid_mask=valid_mask,
        nodata=nodata,
        band_descriptions=band_descriptions,
    )


def make_pair() -> tuple[GeoTiffRasterData, GeoTiffRasterData]:
    """Build a before/after pair sharing one physically unchanged land pixel.

    Both rasters hold dry land at DN 2000 at position (1, 0). Only the "after"
    raster additionally holds dark water at DN 200, which lowers that raster's
    minimum without touching the land pixel.

    Returns:
        The before and after rasters of the pair.
    """
    before = np.full((3, 2, 2), 2000, dtype=np.uint16)
    before[:, 0, 0] = 500
    before[:, 1, 1] = 3000

    after = before.copy()
    after[:, 0, 1] = 200  # newly flooded pixel

    return (
        make_raster(before, name="before.tif"),
        make_raster(after, name="after.tif"),
    )


class TestStretch:
    """The fixed value range mapped onto the 0-255 display range."""

    def test_maps_the_lower_bound_to_zero(self) -> None:
        stretch = Stretch(lo=200.0, hi=3000.0)

        result = stretch.apply(np.array([200], dtype=np.uint16))

        assert result[0] == 0

    def test_maps_the_upper_bound_to_full_scale(self) -> None:
        stretch = Stretch(lo=200.0, hi=3000.0)

        result = stretch.apply(np.array([3000], dtype=np.uint16))

        assert result[0] == 255

    def test_clips_values_outside_the_range(self) -> None:
        stretch = Stretch(lo=200.0, hi=3000.0)

        result = stretch.apply(np.array([0, 9000], dtype=np.uint16))

        assert result[0] == 0
        assert result[1] == 255

    def test_returns_uint8(self) -> None:
        stretch = Stretch(lo=0.0, hi=1000.0)

        result = stretch.apply(np.array([500], dtype=np.uint16))

        assert result.dtype == np.uint8

    def test_rejects_a_collapsed_range(self) -> None:
        with pytest.raises(ValueError):
            Stretch(lo=100.0, hi=100.0)

    def test_rejects_an_inverted_range(self) -> None:
        with pytest.raises(ValueError):
            Stretch(lo=3000.0, hi=200.0)

    def test_rejects_non_finite_bounds(self) -> None:
        with pytest.raises(ValueError):
            Stretch(lo=0.0, hi=float("inf"))


class TestComputeSharedStretch:
    """Derivation of one value range covering a whole raster pair."""

    def test_spans_the_full_range_of_the_pair(self) -> None:
        """The range must cover both rasters, not just one of them."""
        before, after = make_pair()

        stretch = compute_shared_stretch(before, after)

        assert stretch is not None
        assert stretch.lo == 200.0  # only present in the after raster
        assert stretch.hi == 3000.0  # present in both rasters

    def test_ignores_invalid_pixels(self) -> None:
        """NoData filler values must not widen the range."""
        data = np.full((3, 1, 3), 1000, dtype=np.uint16)
        data[:, 0, 0] = 500  # valid
        data[:, 0, 1] = 60000  # NoData filler -- must be ignored
        data[:, 0, 2] = 2000  # valid

        raster = make_raster(
            data,
            valid_mask=np.array([[True, False, True]]),
        )

        stretch = compute_shared_stretch(raster)

        assert stretch is not None
        assert stretch.lo == 500.0
        assert stretch.hi == 2000.0  # not 60000

    def test_restricts_the_range_to_the_selected_bands(self) -> None:
        """Bands outside the selection must not influence the range."""
        data = np.full((4, 1, 1), 1000, dtype=np.uint16)
        data[0, 0, 0] = 100
        data[3, 0, 0] = 9000  # band outside the RGB selection

        raster = make_raster(data)

        stretch = compute_shared_stretch(raster, bands=(0, 1, 2))

        assert stretch is not None
        assert stretch.lo == 100.0
        assert stretch.hi == 1000.0

    def test_returns_none_for_a_constant_raster(self) -> None:
        """A collapsed range cannot be stretched and must be reported."""
        raster = make_raster(np.full((3, 2, 2), 1000, dtype=np.uint16))

        assert compute_shared_stretch(raster) is None

    def test_returns_none_when_no_pixel_is_valid(self) -> None:
        """A fully masked raster carries no usable value range."""
        raster = make_raster(
            np.full((3, 2, 2), 1000, dtype=np.uint16),
            valid_mask=np.zeros((2, 2), dtype=bool),
        )

        assert compute_shared_stretch(raster) is None


class TestStretchConsistencyAcrossAPair:
    """Regression tests for the per-image stretch defect.

    Before the shared stretch, the display range was derived from each raster
    on its own. Dark water appearing only in the "after" raster lowered that
    raster's minimum, and the resulting offset shifted *every* pixel of the
    image -- including physically unchanged land. Change detection then
    reacted to the normalisation instead of to the scene.
    """

    def test_unchanged_pixels_render_identically_with_a_shared_stretch(
        self,
    ) -> None:
        """A physically unchanged pixel must produce the same RGB value."""
        before, after = make_pair()
        adapter = GeoTiffImageAdapter()
        stretch = compute_shared_stretch(before, after)

        before_rgb = np.asarray(adapter.to_image(before, stretch=stretch))
        after_rgb = np.asarray(adapter.to_image(after, stretch=stretch))

        # Pixel (1, 0) is dry land at DN 2000 in both rasters.
        np.testing.assert_array_equal(before_rgb[1, 0], after_rgb[1, 0])

    def test_unchanged_pixels_diverge_without_a_shared_stretch(self) -> None:
        """Characterization test: the defect the shared stretch removes.

        Asserted explicitly so that the legacy per-image path cannot silently
        become the default again.
        """
        before, after = make_pair()
        adapter = GeoTiffImageAdapter()

        before_rgb = np.asarray(adapter.to_image(before))
        after_rgb = np.asarray(adapter.to_image(after))

        assert not np.array_equal(before_rgb[1, 0], after_rgb[1, 0])

    def test_uint8_rasters_are_unaffected_by_a_stretch(self) -> None:
        """uint8 rasters are already on an absolute scale and stay untouched."""
        raster = make_raster(np.full((3, 2, 2), 120, dtype=np.uint8))
        adapter = GeoTiffImageAdapter()

        plain = np.asarray(adapter.to_image(raster))
        stretched = np.asarray(
            adapter.to_image(raster, stretch=Stretch(lo=0.0, hi=1000.0))
        )

        np.testing.assert_array_equal(plain, stretched)