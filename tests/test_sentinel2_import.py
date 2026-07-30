"""Tests for :mod:`src.sentinel2_import`.

Focus: the combined GeoTIFF this module writes must be a completely
normal file from the rest of the application's point of view -- in
particular, loadable by the existing, unmodified
:class:`~src.geotiff_raster_loader.GeoTiffRasterLoader` with correct
CRS, shape and band descriptions. That round trip, not just the
low-level Rasterio metadata, is the actual point of this feature.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.exceptions import Sentinel2BandStackError
from src.geotiff_raster_loader import GeoTiffRasterLoader
from src.sentinel2_import import combine_sentinel2_bands_to_geotiff

UTM32 = "EPSG:32632"
ORIGIN = (699960.0, 5300040.0)


def write_band(
    path: Path,
    width: int,
    height: int,
    pixel_size: float,
    value: int,
    crs: str = UTM32,
) -> None:
    """Write a single-band GeoTIFF standing in for a Sentinel-2 band file."""
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
        dataset.write(np.full((height, width), value, dtype=np.uint16), 1)


class TestCombinedFileIsWrittenCorrectly:
    def test_output_file_is_created(self, tmp_path: Path) -> None:
        write_band(tmp_path / "b03.tif", 20, 20, 10.0, 100)
        write_band(tmp_path / "b08.tif", 20, 20, 10.0, 200)
        output = tmp_path / "combined.tif"

        result_path = combine_sentinel2_bands_to_geotiff(
            {"B03": tmp_path / "b03.tif", "B08": tmp_path / "b08.tif"}, output
        )

        assert result_path == output
        assert output.is_file()

    def test_output_creates_parent_directories(self, tmp_path: Path) -> None:
        write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100)
        output = tmp_path / "nested" / "dir" / "combined.tif"

        combine_sentinel2_bands_to_geotiff({"B03": tmp_path / "b03.tif"}, output)

        assert output.is_file()

    def test_band_count_and_order_are_preserved(self, tmp_path: Path) -> None:
        write_band(tmp_path / "b08.tif", 10, 10, 10.0, 200)
        write_band(tmp_path / "b04.tif", 10, 10, 10.0, 120)
        write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100)
        output = tmp_path / "combined.tif"

        combine_sentinel2_bands_to_geotiff(
            {
                "B08": tmp_path / "b08.tif",
                "B04": tmp_path / "b04.tif",
                "B03": tmp_path / "b03.tif",
            },
            output,
        )

        with rasterio.open(output) as dataset:
            assert dataset.count == 3
            assert dataset.descriptions == ("B08", "B04", "B03")

    def test_crs_matches_the_finest_requested_band(self, tmp_path: Path) -> None:
        write_band(tmp_path / "b03_10m.tif", 20, 20, 10.0, 100)
        write_band(tmp_path / "b11_20m.tif", 10, 10, 20.0, 150)
        output = tmp_path / "combined.tif"

        combine_sentinel2_bands_to_geotiff(
            {"B03": tmp_path / "b03_10m.tif", "B11": tmp_path / "b11_20m.tif"}, output
        )

        with rasterio.open(output) as dataset:
            assert dataset.crs == rasterio.crs.CRS.from_epsg(32632)
            assert dataset.width == 20
            assert dataset.height == 20

    def test_mixed_resolution_bands_end_up_on_one_common_grid(
        self, tmp_path: Path
    ) -> None:
        """The whole point: a 20 m band must be resampled, not just cropped
        or left mismatched, so all bands share one pixel grid in the file."""
        write_band(tmp_path / "b03_10m.tif", 40, 40, 10.0, 100)
        write_band(tmp_path / "b11_20m.tif", 20, 20, 20.0, 150)
        output = tmp_path / "combined.tif"

        combine_sentinel2_bands_to_geotiff(
            {"B03": tmp_path / "b03_10m.tif", "B11": tmp_path / "b11_20m.tif"}, output
        )

        with rasterio.open(output) as dataset:
            data = dataset.read()
            assert data.shape == (2, 40, 40)
            assert data[1].mean() == pytest.approx(150.0, abs=1.0)


class TestRoundTripWithExistingLoader:
    """The combined file must be a completely ordinary GeoTIFF pair member.

    This is the actual acceptance criterion for this feature: a user
    drops the combined file into ``data/before``/``data/after`` and
    everything downstream -- loader, detector, batch processor -- works
    completely unmodified.
    """

    def test_geotiff_raster_loader_reads_it_back_unmodified(
        self, tmp_path: Path
    ) -> None:
        write_band(tmp_path / "b03.tif", 20, 20, 10.0, 100)
        write_band(tmp_path / "b08.tif", 20, 20, 10.0, 200)
        write_band(tmp_path / "b11.tif", 10, 10, 20.0, 150)
        output = tmp_path / "combined.tif"

        combine_sentinel2_bands_to_geotiff(
            {
                "B03": tmp_path / "b03.tif",
                "B08": tmp_path / "b08.tif",
                "B11": tmp_path / "b11.tif",
            },
            output,
        )

        raster = GeoTiffRasterLoader().load(output)

        assert raster.band_descriptions == ("B03", "B08", "B11")
        assert raster.data.shape == (3, 20, 20)
        assert raster.valid_mask.all()

    def test_spectral_water_detector_consumes_it_without_modification(
        self, tmp_path: Path
    ) -> None:
        """End-to-end proof: combined file -> unmodified loader -> unmodified
        detector, with a correctly detected water region."""
        from src.spectral_detector import SpectralWaterDetector

        write_band(tmp_path / "b03.tif", 20, 20, 10.0, 100)  # green, low
        write_band(tmp_path / "b08.tif", 20, 20, 10.0, 50)  # nir, lower -> water-like
        output = tmp_path / "combined.tif"

        combine_sentinel2_bands_to_geotiff(
            {"B03": tmp_path / "b03.tif", "B08": tmp_path / "b08.tif"}, output
        )

        raster = GeoTiffRasterLoader().load(output)
        result = SpectralWaterDetector().detect(raster)

        assert result.water_coverage_percent == pytest.approx(100.0)


class TestErrorHandling:
    def test_missing_band_file_propagates_stack_error(self, tmp_path: Path) -> None:
        with pytest.raises(Sentinel2BandStackError, match="not found"):
            combine_sentinel2_bands_to_geotiff(
                {"B03": tmp_path / "does_not_exist.tif"}, tmp_path / "out.tif"
            )

    def test_unknown_band_code_raises_value_error(self, tmp_path: Path) -> None:
        write_band(tmp_path / "unknown.tif", 10, 10, 10.0, 100)

        with pytest.raises(ValueError, match="Unknown Sentinel-2 band"):
            combine_sentinel2_bands_to_geotiff(
                {"NOT_A_BAND": tmp_path / "unknown.tif"}, tmp_path / "out.tif"
            )

    def test_mismatched_crs_propagates_stack_error(self, tmp_path: Path) -> None:
        write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100, crs="EPSG:32632")
        write_band(tmp_path / "b08.tif", 10, 10, 10.0, 200, crs="EPSG:32633")

        with pytest.raises(Sentinel2BandStackError, match="coordinate reference"):
            combine_sentinel2_bands_to_geotiff(
                {"B03": tmp_path / "b03.tif", "B08": tmp_path / "b08.tif"},
                tmp_path / "out.tif",
            )
