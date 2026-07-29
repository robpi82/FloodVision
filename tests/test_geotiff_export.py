"""Automated tests for :mod:`src.geotiff_export`.

Strategy: build a :class:`GeoTiffMetadata` directly (no need to read a
real file first -- the exporter only consumes the dataclass) and a
small synthetic mask array, export it, then re-open the written file
with Rasterio to verify every claim independently of the writer's own
internals.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

from src.exceptions import GeoTiffExportError
from src.geotiff_export import export_flood_mask_geotiff, export_spectral_index_geotiff
from src.geotiff_loader import GeoTiffMetadata

WIDTH = 40
HEIGHT = 30
PIXEL = 10.0
ORIGIN = (699_960.0, 5_300_040.0)
UTM32 = CRS.from_epsg(32632)
TRANSFORM = from_origin(ORIGIN[0], ORIGIN[1], PIXEL, PIXEL)


def make_metadata(
    *,
    width: int = WIDTH,
    height: int = HEIGHT,
    crs: CRS | None = UTM32,
    transform=TRANSFORM,
    nodata: float | None = 0.0,
) -> GeoTiffMetadata:
    """Build a metadata instance without needing a real file on disk.

    Args:
        width: Raster width in pixels.
        height: Raster height in pixels.
        crs: Coordinate reference system, or ``None``.
        transform: Affine transform.
        nodata: Source NoData value (irrelevant to the export, per the
            module's documented NoData semantics -- included here to
            prove that irrelevance).

    Returns:
        A fully populated :class:`GeoTiffMetadata`.
    """
    return GeoTiffMetadata(
        filename="after.tif",
        path=Path("/synthetic/after.tif"),
        width=width,
        height=height,
        band_count=3,
        dtypes=("uint8", "uint8", "uint8"),
        driver="GTiff",
        crs=crs,
        epsg=crs.to_epsg() if crs is not None else None,
        bounds=rasterio.coords.BoundingBox(
            left=ORIGIN[0],
            bottom=ORIGIN[1] - height * PIXEL,
            right=ORIGIN[0] + width * PIXEL,
            top=ORIGIN[1],
        ),
        pixel_size=(PIXEL, PIXEL),
        transform=transform,
        nodata=nodata,
    )


def make_flood_mask(width: int = WIDTH, height: int = HEIGHT) -> np.ndarray:
    """Build a deterministic binary flood mask with a known flooded block.

    Args:
        width: Mask width in pixels.
        height: Mask height in pixels.

    Returns:
        A ``(height, width)`` uint8 array of ``0``/``255`` values.
    """
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[5:15, 8:20] = 255  # a known, exactly-reproducible flooded block
    return mask


def make_spectral_index(width: int = WIDTH, height: int = HEIGHT) -> np.ndarray:
    """Build a deterministic NDWI/MNDWI-like raster with one invalid pixel.

    Args:
        width: Raster width in pixels.
        height: Raster height in pixels.

    Returns:
        A ``(height, width)`` float32 array with values in roughly
        ``[-1, 1]`` and a single ``NaN`` at a known, fixed location.
    """
    index = np.full((height, width), -0.2, dtype=np.float32)
    index[5:15, 8:20] = 0.6  # a known "water-like" block, mirrors the flood block
    index[0, 0] = np.nan  # a known invalid pixel
    return index


# ---------------------------------------------------------------------------
# Successful export: file creation, band/dtype, values (tasks: export,
# file creation, single band, uint8, correct 0/255 values)
# ---------------------------------------------------------------------------
class TestSuccessfulExport:
    """A valid mask exports to a real, single-band uint8 GeoTIFF."""

    def test_export_creates_the_output_file(self, tmp_path: Path) -> None:
        """The GeoTIFF file exists on disk after export."""
        output_path = tmp_path / "new_flood_mask.tif"
        result_path = export_flood_mask_geotiff(
            make_flood_mask(), make_metadata(), output_path
        )
        assert result_path == output_path
        assert output_path.is_file()

    def test_export_creates_parent_directories(self, tmp_path: Path) -> None:
        """Missing parent directories are created, mirroring save_image()."""
        output_path = tmp_path / "flood" / "nested" / "new_flood_mask.tif"
        export_flood_mask_geotiff(make_flood_mask(), make_metadata(), output_path)
        assert output_path.is_file()

    def test_output_is_single_band(self, tmp_path: Path) -> None:
        """The written raster has exactly one band."""
        output_path = tmp_path / "new_flood_mask.tif"
        export_flood_mask_geotiff(make_flood_mask(), make_metadata(), output_path)
        with rasterio.open(output_path) as dataset:
            assert dataset.count == 1

    def test_output_dtype_is_uint8(self, tmp_path: Path) -> None:
        """The written raster's data type is uint8."""
        output_path = tmp_path / "new_flood_mask.tif"
        export_flood_mask_geotiff(make_flood_mask(), make_metadata(), output_path)
        with rasterio.open(output_path) as dataset:
            assert dataset.dtypes[0] == "uint8"

    def test_output_values_match_the_source_mask_exactly(self, tmp_path: Path) -> None:
        """Written pixel values are exactly the 0/255 input, unchanged."""
        mask = make_flood_mask()
        output_path = tmp_path / "new_flood_mask.tif"
        export_flood_mask_geotiff(mask, make_metadata(), output_path)
        with rasterio.open(output_path) as dataset:
            written = dataset.read(1)
        assert set(np.unique(written)) <= {0, 255}
        assert np.array_equal(written, mask)
        assert written[10, 15] == 255  # inside the known flooded block
        assert written[0, 0] == 0  # outside it


# ---------------------------------------------------------------------------
# Spatial metadata preservation (tasks: CRS, transform, dimensions)
# ---------------------------------------------------------------------------
class TestSpatialMetadataPreservation:
    """CRS, affine transform and dimensions match the source exactly."""

    def test_crs_is_preserved(self, tmp_path: Path) -> None:
        """The output CRS equals the source metadata's CRS."""
        output_path = tmp_path / "new_flood_mask.tif"
        export_flood_mask_geotiff(
            make_flood_mask(), make_metadata(crs=UTM32), output_path
        )
        with rasterio.open(output_path) as dataset:
            assert dataset.crs == UTM32
            assert dataset.crs.to_epsg() == 32632

    def test_transform_is_preserved(self, tmp_path: Path) -> None:
        """The output affine transform equals the source metadata's."""
        output_path = tmp_path / "new_flood_mask.tif"
        export_flood_mask_geotiff(
            make_flood_mask(), make_metadata(transform=TRANSFORM), output_path
        )
        with rasterio.open(output_path) as dataset:
            assert dataset.transform.almost_equals(TRANSFORM, precision=1e-9)

    def test_dimensions_are_preserved(self, tmp_path: Path) -> None:
        """Width and height match the source metadata exactly."""
        width, height = 77, 55
        output_path = tmp_path / "new_flood_mask.tif"
        export_flood_mask_geotiff(
            make_flood_mask(width, height),
            make_metadata(width=width, height=height),
            output_path,
        )
        with rasterio.open(output_path) as dataset:
            assert (dataset.width, dataset.height) == (width, height)

    def test_bounds_are_consistent_with_transform_and_dimensions(
        self, tmp_path: Path
    ) -> None:
        """Re-derived bounds match the source metadata's bounds."""
        metadata = make_metadata()
        output_path = tmp_path / "new_flood_mask.tif"
        export_flood_mask_geotiff(make_flood_mask(), metadata, output_path)
        with rasterio.open(output_path) as dataset:
            assert dataset.bounds.left == pytest.approx(metadata.bounds.left)
            assert dataset.bounds.top == pytest.approx(metadata.bounds.top)
            assert dataset.bounds.right == pytest.approx(metadata.bounds.right)
            assert dataset.bounds.bottom == pytest.approx(metadata.bounds.bottom)


# ---------------------------------------------------------------------------
# NoData semantics (task 10)
# ---------------------------------------------------------------------------
class TestNoDataSemantics:
    """The source NoData value is never copied onto the derived mask."""

    def test_source_nodata_is_not_applied_to_the_output(self, tmp_path: Path) -> None:
        """A source NoData of 0 must not mark 'not flooded' as missing data."""
        output_path = tmp_path / "new_flood_mask.tif"
        export_flood_mask_geotiff(
            make_flood_mask(), make_metadata(nodata=0.0), output_path
        )
        with rasterio.open(output_path) as dataset:
            assert dataset.nodata is None

    def test_export_without_crs_still_writes_a_valid_file(self, tmp_path: Path) -> None:
        """A pair with no CRS at all still exports without error.

        Valid per the compatibility validator's documented policy
        (both rasters lacking a CRS still passes as compatible).
        """
        output_path = tmp_path / "new_flood_mask.tif"
        export_flood_mask_geotiff(
            make_flood_mask(), make_metadata(crs=None), output_path
        )
        with rasterio.open(output_path) as dataset:
            assert dataset.crs is None
            assert (dataset.width, dataset.height) == (WIDTH, HEIGHT)


# ---------------------------------------------------------------------------
# Error handling (task 15): contract violations vs. genuine write failures
# ---------------------------------------------------------------------------
class TestErrorHandling:
    """Bad input fails fast; write failures raise a project exception."""

    def test_wrong_dtype_raises_value_error(self, tmp_path: Path) -> None:
        """A non-uint8 mask is a programmer-contract violation."""
        bad_mask = make_flood_mask().astype(np.int32)
        with pytest.raises(ValueError, match="uint8"):
            export_flood_mask_geotiff(bad_mask, make_metadata(), tmp_path / "out.tif")

    def test_wrong_ndim_raises_value_error(self, tmp_path: Path) -> None:
        """A non-2-D mask is a programmer-contract violation."""
        bad_mask = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match="2-D"):
            export_flood_mask_geotiff(bad_mask, make_metadata(), tmp_path / "out.tif")

    def test_mismatched_shape_raises_value_error(self, tmp_path: Path) -> None:
        """A mask shape that disagrees with the metadata dimensions fails."""
        mismatched = make_flood_mask(width=WIDTH + 5, height=HEIGHT)
        with pytest.raises(ValueError, match="does not match"):
            export_flood_mask_geotiff(mismatched, make_metadata(), tmp_path / "out.tif")

    def test_unwritable_output_path_raises_geotiff_export_error(
        self, tmp_path: Path
    ) -> None:
        """A path that cannot be created as a directory tree fails cleanly.

        A file is placed where the export needs a *directory*, so
        ``mkdir(parents=True)`` fails with a real ``OSError`` -- this
        reaches the writer's own error handling, not the earlier
        shape/dtype validation.
        """
        blocking_file = tmp_path / "blocked"
        blocking_file.write_text("not a directory")
        output_path = blocking_file / "new_flood_mask.tif"

        with pytest.raises(GeoTiffExportError) as excinfo:
            export_flood_mask_geotiff(make_flood_mask(), make_metadata(), output_path)
        assert excinfo.value.path == output_path


# ---------------------------------------------------------------------------
# Spectral index export: continuous float raster, NaN as NoData
# ---------------------------------------------------------------------------
class TestSpectralIndexExport:
    """A NDWI/MNDWI raster exports to a real, single-band float32 GeoTIFF.

    Deliberately mirrors :class:`TestSuccessfulExport` and
    :class:`TestSpatialMetadataPreservation` in structure -- same claims,
    same georeferencing guarantees -- but for the continuous index
    export rather than the binary flood mask, plus the NoData handling
    that is genuinely different between the two (see the module
    docstring of :func:`export_spectral_index_geotiff`).
    """

    def test_export_creates_the_output_file(self, tmp_path: Path) -> None:
        output_path = tmp_path / "after_index.tif"
        result_path = export_spectral_index_geotiff(
            make_spectral_index(), make_metadata(), output_path
        )
        assert result_path == output_path
        assert output_path.is_file()

    def test_export_creates_parent_directories(self, tmp_path: Path) -> None:
        output_path = tmp_path / "flood" / "nested" / "after_index.tif"
        export_spectral_index_geotiff(
            make_spectral_index(), make_metadata(), output_path
        )
        assert output_path.is_file()

    def test_output_is_single_band(self, tmp_path: Path) -> None:
        output_path = tmp_path / "after_index.tif"
        export_spectral_index_geotiff(
            make_spectral_index(), make_metadata(), output_path
        )
        with rasterio.open(output_path) as dataset:
            assert dataset.count == 1

    def test_output_dtype_is_float32(self, tmp_path: Path) -> None:
        output_path = tmp_path / "after_index.tif"
        export_spectral_index_geotiff(
            make_spectral_index(), make_metadata(), output_path
        )
        with rasterio.open(output_path) as dataset:
            assert dataset.dtypes[0] == "float32"

    def test_output_values_match_the_source_raster(self, tmp_path: Path) -> None:
        """Written pixel values equal the input, NaN pixel included."""
        index = make_spectral_index()
        output_path = tmp_path / "after_index.tif"
        export_spectral_index_geotiff(index, make_metadata(), output_path)
        with rasterio.open(output_path) as dataset:
            written = dataset.read(1)
        np.testing.assert_allclose(
            written, index, rtol=1e-5, equal_nan=True
        )
        assert written[10, 15] == pytest.approx(0.6)  # inside the water-like block
        assert written[1, 1] == pytest.approx(-0.2)  # outside it
        assert np.isnan(written[0, 0])  # the known invalid pixel

    def test_nan_is_written_as_nodata(self, tmp_path: Path) -> None:
        """Unlike the flood mask, NaN pixels here get a real NoData value.

        This is the deliberate semantic difference documented in
        :func:`export_spectral_index_geotiff`: NaN means "no index value
        here", a genuinely missing value, not a valid third class.
        """
        output_path = tmp_path / "after_index.tif"
        export_spectral_index_geotiff(
            make_spectral_index(), make_metadata(), output_path
        )
        with rasterio.open(output_path) as dataset:
            assert dataset.nodata is not None
            assert np.isnan(dataset.nodata)

    def test_crs_and_transform_are_preserved(self, tmp_path: Path) -> None:
        output_path = tmp_path / "after_index.tif"
        export_spectral_index_geotiff(
            make_spectral_index(),
            make_metadata(crs=UTM32, transform=TRANSFORM),
            output_path,
        )
        with rasterio.open(output_path) as dataset:
            assert dataset.crs == UTM32
            assert dataset.transform.almost_equals(TRANSFORM, precision=1e-9)

    def test_dimensions_are_preserved(self, tmp_path: Path) -> None:
        width, height = 77, 55
        output_path = tmp_path / "after_index.tif"
        export_spectral_index_geotiff(
            make_spectral_index(width, height),
            make_metadata(width=width, height=height),
            output_path,
        )
        with rasterio.open(output_path) as dataset:
            assert (dataset.width, dataset.height) == (width, height)

    def test_wrong_dtype_raises_value_error(self, tmp_path: Path) -> None:
        """An integer raster is a programmer-contract violation here."""
        bad_index = make_spectral_index().astype(np.int32)
        with pytest.raises(ValueError, match="floating-point"):
            export_spectral_index_geotiff(
                bad_index, make_metadata(), tmp_path / "out.tif"
            )

    def test_wrong_ndim_raises_value_error(self, tmp_path: Path) -> None:
        bad_index = np.zeros((HEIGHT, WIDTH, 1), dtype=np.float32)
        with pytest.raises(ValueError, match="2-D"):
            export_spectral_index_geotiff(
                bad_index, make_metadata(), tmp_path / "out.tif"
            )

    def test_mismatched_shape_raises_value_error(self, tmp_path: Path) -> None:
        mismatched = make_spectral_index(width=WIDTH + 5, height=HEIGHT)
        with pytest.raises(ValueError, match="does not match"):
            export_spectral_index_geotiff(
                mismatched, make_metadata(), tmp_path / "out.tif"
            )

    def test_unwritable_output_path_raises_geotiff_export_error(
        self, tmp_path: Path
    ) -> None:
        blocking_file = tmp_path / "blocked"
        blocking_file.write_text("not a directory")
        output_path = blocking_file / "after_index.tif"

        with pytest.raises(GeoTiffExportError) as excinfo:
            export_spectral_index_geotiff(
                make_spectral_index(), make_metadata(), output_path
            )
        assert excinfo.value.path == output_path