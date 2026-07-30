"""Tests for :mod:`src.sentinel2_band_stacker`.

Uses small synthetic single-band GeoTIFFs (not real ``.SAFE`` JPEG2000
files -- Rasterio/GDAL reads both through the same code path, so a
GeoTIFF fixture exercises exactly the same logic without needing a real
Sentinel-2 product in the test suite) to stand in for the individual
band files real Sentinel-2 Level-2A products ship.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin

from src.exceptions import Sentinel2BandStackError
from src.sentinel2_band_stacker import stack_sentinel2_bands

UTM32 = "EPSG:32632"
ORIGIN = (699960.0, 5300040.0)


def write_band(
    path: Path,
    width: int,
    height: int,
    pixel_size: float,
    values: np.ndarray | int,
    crs: str = UTM32,
) -> None:
    """Write a single-band GeoTIFF standing in for a Sentinel-2 band file.

    Args:
        path: Output file path.
        width: Raster width in pixels.
        height: Raster height in pixels.
        pixel_size: Pixel size in metres (10.0 or 20.0 for a realistic
            Sentinel-2 stand-in).
        values: Either a scalar fill value, or a pre-built ``(height,
            width)`` array (e.g. a gradient, to exercise resampling
            behaviour beyond a flat value).
        crs: Coordinate reference system, as an EPSG string.
    """
    data = (
        np.full((height, width), values, dtype=np.uint16)
        if np.isscalar(values)
        else np.asarray(values, dtype=np.uint16)
    )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=1,
        dtype="uint16",
        crs=crs,
        transform=from_origin(ORIGIN[0], ORIGIN[1], pixel_size, pixel_size),
    ) as dataset:
        dataset.write(data, 1)


def write_band_with_nodata(
    path: Path,
    width: int,
    height: int,
    pixel_size: float,
    value: int,
    nodata_region: tuple[slice, slice],
    crs: str = UTM32,
) -> None:
    """Write a single-band GeoTIFF with a NoData hole for mask propagation tests."""
    data = np.full((height, width), value, dtype=np.uint16)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=1,
        dtype="uint16",
        crs=crs,
        transform=from_origin(ORIGIN[0], ORIGIN[1], pixel_size, pixel_size),
        nodata=0,
    ) as dataset:
        data[nodata_region] = 0
        dataset.write(data, 1)


# ---------------------------------------------------------------------------
# Basic stacking: same resolution, no resampling needed
# ---------------------------------------------------------------------------
class TestSameResolutionStacking:
    def test_bands_are_stacked_in_input_order(self, tmp_path: Path) -> None:
        write_band(tmp_path / "b08.tif", 20, 20, 10.0, 200)
        write_band(tmp_path / "b04.tif", 20, 20, 10.0, 120)
        write_band(tmp_path / "b03.tif", 20, 20, 10.0, 100)

        raster = stack_sentinel2_bands(
            {
                "B08": tmp_path / "b08.tif",
                "B04": tmp_path / "b04.tif",
                "B03": tmp_path / "b03.tif",
            }
        )

        assert raster.band_descriptions == ("B08", "B04", "B03")
        assert raster.band_count == 3
        assert raster.data[0, 0, 0] == 200  # B08
        assert raster.data[1, 0, 0] == 120  # B04
        assert raster.data[2, 0, 0] == 100  # B03

    def test_shape_matches_source_when_all_bands_share_resolution(
        self, tmp_path: Path
    ) -> None:
        write_band(tmp_path / "b03.tif", 30, 25, 10.0, 100)
        write_band(tmp_path / "b08.tif", 30, 25, 10.0, 200)

        raster = stack_sentinel2_bands(
            {"B03": tmp_path / "b03.tif", "B08": tmp_path / "b08.tif"}
        )

        assert (raster.height, raster.width) == (25, 30)

    def test_valid_mask_is_all_true_without_nodata(self, tmp_path: Path) -> None:
        write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100)
        write_band(tmp_path / "b08.tif", 10, 10, 10.0, 200)

        raster = stack_sentinel2_bands(
            {"B03": tmp_path / "b03.tif", "B08": tmp_path / "b08.tif"}
        )

        assert raster.valid_mask.all()


# ---------------------------------------------------------------------------
# Mixed-resolution stacking: the actual resampling behaviour
# ---------------------------------------------------------------------------
class TestMixedResolutionStacking:
    def test_coarser_band_is_upsampled_to_finer_bands_grid(
        self, tmp_path: Path
    ) -> None:
        """A 20 m band is resampled onto the 10 m bands' exact pixel grid."""
        write_band(tmp_path / "b03_10m.tif", 20, 20, 10.0, 100)
        write_band(tmp_path / "b08_10m.tif", 20, 20, 10.0, 200)
        write_band(tmp_path / "b11_20m.tif", 10, 10, 20.0, 150)

        raster = stack_sentinel2_bands(
            {
                "B03": tmp_path / "b03_10m.tif",
                "B08": tmp_path / "b08_10m.tif",
                "B11": tmp_path / "b11_20m.tif",
            }
        )

        # Every band must end up on the 10 m (20x20) grid, B11 included.
        assert raster.data.shape == (3, 20, 20)
        assert raster.data[2].mean() == pytest.approx(150.0, abs=1.0)

    def test_reference_grid_is_the_finest_requested_band_not_a_fixed_10m(
        self, tmp_path: Path
    ) -> None:
        """If no 10 m band is requested, the finest *requested* band wins.

        Guards against hard-coding "always resample to 10 m" instead of
        "resample to whatever the finest requested band is" -- a caller
        requesting only B11 (20 m) and B09 (60 m) must get a 20 m
        result, not silently fabricate a 10 m grid nothing was measured
        at.
        """
        write_band(tmp_path / "b11_20m.tif", 20, 20, 20.0, 150)
        write_band(tmp_path / "b09_60m.tif", 7, 7, 60.0, 50)  # ~1/3 the pixel count

        raster = stack_sentinel2_bands(
            {"B11": tmp_path / "b11_20m.tif", "B09": tmp_path / "b09_60m.tif"}
        )

        assert raster.data.shape == (2, 20, 20)  # B11's grid, not a 10 m fabrication

    def test_bilinear_resampling_smooths_a_gradient(self, tmp_path: Path) -> None:
        """Resampled values interpolate rather than blockily repeat.

        A hard proof that real (bilinear) resampling ran, not just a
        reshape/repeat: a smooth source gradient must stay smooth after
        upsampling, without abrupt equal-value blocks.
        """
        gradient_20m = np.linspace(0, 1000, 10, dtype=np.uint16).reshape(1, 10)
        gradient_20m = np.repeat(gradient_20m, 10, axis=0)
        write_band(tmp_path / "b03_10m.tif", 20, 20, 10.0, 500)
        write_band(tmp_path / "b11_20m.tif", 10, 10, 20.0, gradient_20m)

        raster = stack_sentinel2_bands(
            {"B03": tmp_path / "b03_10m.tif", "B11": tmp_path / "b11_20m.tif"},
            resampling=Resampling.bilinear,
        )

        resampled_row = raster.data[1, 10, :].astype(float)
        # A blocky (nearest-neighbour) resample would repeat each of the
        # 10 source values exactly twice; bilinear must not.
        assert not np.array_equal(resampled_row[0::2], resampled_row[1::2])
        # The row must still be monotonically non-decreasing, like the
        # source gradient -- resampling shouldn't invent local reversals.
        assert np.all(np.diff(resampled_row) >= -1e-6)

    def test_explicit_resampling_method_is_honoured(self, tmp_path: Path) -> None:
        """Passing Resampling.nearest produces a genuinely blockier result
        than the bilinear default, proving the parameter actually flows
        through to the resampling call."""
        gradient_20m = np.linspace(0, 1000, 10, dtype=np.uint16).reshape(1, 10)
        gradient_20m = np.repeat(gradient_20m, 10, axis=0)
        write_band(tmp_path / "b03_10m.tif", 20, 20, 10.0, 500)
        write_band(tmp_path / "b11_20m.tif", 10, 10, 20.0, gradient_20m)

        raster = stack_sentinel2_bands(
            {"B03": tmp_path / "b03_10m.tif", "B11": tmp_path / "b11_20m.tif"},
            resampling=Resampling.nearest,
        )

        resampled_row = raster.data[1, 10, :]
        # Nearest-neighbour repeats each source pixel exactly.
        np.testing.assert_array_equal(resampled_row[0::2], resampled_row[1::2])


# ---------------------------------------------------------------------------
# Validity-mask propagation through resampling
# ---------------------------------------------------------------------------
class TestValidMaskPropagation:
    def test_nodata_in_a_same_resolution_band_reduces_the_merged_mask(
        self, tmp_path: Path
    ) -> None:
        write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100)
        write_band_with_nodata(
            tmp_path / "b08.tif", 10, 10, 10.0, 200, (slice(0, 3), slice(0, 3))
        )

        raster = stack_sentinel2_bands(
            {"B03": tmp_path / "b03.tif", "B08": tmp_path / "b08.tif"}
        )

        assert not raster.valid_mask[0:3, 0:3].any()
        assert raster.valid_mask[5:, 5:].all()

    def test_nodata_in_a_resampled_coarser_band_still_excludes_pixels(
        self, tmp_path: Path
    ) -> None:
        """NoData in a 20 m band must still reach the final 10 m mask.

        The mask itself is resampled (nearest-neighbour, see module
        docstring) alongside the data -- this confirms that path is
        actually wired up, not just the pixel-value resampling.
        """
        write_band(tmp_path / "b03_10m.tif", 20, 20, 10.0, 100)
        write_band_with_nodata(
            tmp_path / "b11_20m.tif", 10, 10, 20.0, 150, (slice(0, 2), slice(0, 2))
        )

        raster = stack_sentinel2_bands(
            {"B03": tmp_path / "b03_10m.tif", "B11": tmp_path / "b11_20m.tif"}
        )

        assert not raster.valid_mask[0:4, 0:4].any()
        assert raster.valid_mask[10:, 10:].all()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------
class TestErrorHandling:
    def test_empty_band_files_raises(self) -> None:
        with pytest.raises(Sentinel2BandStackError, match="no band files"):
            stack_sentinel2_bands({})

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(Sentinel2BandStackError, match="not found"):
            stack_sentinel2_bands({"B03": tmp_path / "does_not_exist.tif"})

    def test_unknown_band_code_raises_value_error(self, tmp_path: Path) -> None:
        write_band(tmp_path / "unknown.tif", 10, 10, 10.0, 100)

        with pytest.raises(ValueError, match="Unknown Sentinel-2 band"):
            stack_sentinel2_bands({"NOT_A_BAND": tmp_path / "unknown.tif"})

    def test_mismatched_crs_raises_with_both_crs_named(self, tmp_path: Path) -> None:
        write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100, crs="EPSG:32632")
        write_band(tmp_path / "b08.tif", 10, 10, 10.0, 200, crs="EPSG:32633")

        with pytest.raises(Sentinel2BandStackError, match="32632") as excinfo:
            stack_sentinel2_bands(
                {"B03": tmp_path / "b03.tif", "B08": tmp_path / "b08.tif"}
            )
        assert "32633" in str(excinfo.value)

    def test_unreadable_file_raises_sentinel2_band_stack_error(
        self, tmp_path: Path
    ) -> None:
        garbage = tmp_path / "not_a_raster.tif"
        garbage.write_text("this is not a GeoTIFF")

        with pytest.raises(Sentinel2BandStackError, match="failed to read"):
            stack_sentinel2_bands({"B03": garbage})
