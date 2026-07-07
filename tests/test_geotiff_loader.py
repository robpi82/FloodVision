"""Automated tests for :mod:`src.geotiff_loader`.

Test-data strategy: every raster is a tiny synthetic file written into
pytest's ``tmp_path`` during the test itself -- no binary fixtures in
the repository, no network access, deterministic values throughout, and
automatic cleanup by pytest. Real Rasterio files are used instead of
mocks because the loader's job *is* the interaction with Rasterio.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from PIL import Image
from rasterio.crs import CRS
from rasterio.transform import from_origin

from src.exceptions import FloodVisionError, ImageLoadError
from src.geotiff_loader import GEOTIFF_EXTENSIONS, GeoTiffLoader

# ---------------------------------------------------------------------------
# Reference values for the synthetic GeoTIFF (UTM zone 32N, 10 m pixels)
# ---------------------------------------------------------------------------
WIDTH = 64
HEIGHT = 48
BAND_COUNT = 3
EPSG = 32632
ORIGIN_X = 699_960.0
ORIGIN_Y = 5_300_040.0
PIXEL_SIZE = 10.0
NODATA = 0.0
TRANSFORM = from_origin(ORIGIN_X, ORIGIN_Y, PIXEL_SIZE, PIXEL_SIZE)

#: CRS that is valid but has no exact EPSG equivalent (custom-centred
#: azimuthal equidistant), used for the "CRS without EPSG" case.
NO_EPSG_PROJ4 = "+proj=aeqd +lat_0=48.1 +lon_0=11.5 +datum=WGS84 +units=m +no_defs"


def write_geotiff(
    path: Path,
    *,
    band_count: int = BAND_COUNT,
    crs: str | CRS | None = f"EPSG:{EPSG}",
    nodata: float | None = NODATA,
) -> None:
    """Write a small deterministic GeoTIFF for a test.

    Args:
        path: Target file path.
        band_count: Number of uint8 bands to write.
        crs: CRS definition passed to Rasterio.
        nodata: NoData value, or ``None`` to omit it.
    """
    data = np.full((band_count, HEIGHT, WIDTH), 128, dtype=np.uint8)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=WIDTH,
        height=HEIGHT,
        count=band_count,
        dtype="uint8",
        crs=crs,
        transform=TRANSFORM,
        nodata=nodata,
    ) as dataset:
        dataset.write(data)


@pytest.fixture
def loader() -> GeoTiffLoader:
    """A loader with default configuration."""
    return GeoTiffLoader()


@pytest.fixture
def valid_geotiff(tmp_path: Path) -> Path:
    """A fully georeferenced synthetic GeoTIFF on disk."""
    path = tmp_path / "site.tif"
    write_geotiff(path)
    return path


# ---------------------------------------------------------------------------
# Valid GeoTIFF: full metadata extraction (task 5)
# ---------------------------------------------------------------------------
class TestValidGeoTiffMetadata:
    """Extraction of every metadata field from a valid GeoTIFF."""

    def test_identity_and_raster_shape(
        self, loader: GeoTiffLoader, valid_geotiff: Path
    ) -> None:
        """File identity, dimensions and band structure are extracted."""
        metadata = loader.read_metadata(valid_geotiff)
        assert metadata.path == valid_geotiff
        assert metadata.filename == "site.tif"
        assert metadata.width == WIDTH
        assert metadata.height == HEIGHT
        assert metadata.band_count == BAND_COUNT
        assert metadata.dtypes == ("uint8",) * BAND_COUNT
        assert metadata.driver == "GTiff"

    def test_georeferencing_fields(
        self, loader: GeoTiffLoader, valid_geotiff: Path
    ) -> None:
        """CRS, EPSG, bounds, resolution, transform and NoData match."""
        metadata = loader.read_metadata(valid_geotiff)
        assert metadata.crs is not None
        assert metadata.epsg == EPSG
        assert metadata.pixel_size == (PIXEL_SIZE, PIXEL_SIZE)
        assert metadata.nodata == NODATA
        assert metadata.transform.almost_equals(TRANSFORM, precision=1e-9)
        assert metadata.bounds.left == pytest.approx(ORIGIN_X)
        assert metadata.bounds.top == pytest.approx(ORIGIN_Y)
        assert metadata.bounds.right == pytest.approx(ORIGIN_X + WIDTH * PIXEL_SIZE)
        assert metadata.bounds.bottom == pytest.approx(ORIGIN_Y - HEIGHT * PIXEL_SIZE)

    @pytest.mark.parametrize("band_count", [1, 3])
    def test_band_count_variants(
        self, loader: GeoTiffLoader, tmp_path: Path, band_count: int
    ) -> None:
        """Single- and multi-band rasters report matching band metadata."""
        path = tmp_path / f"bands_{band_count}.tif"
        write_geotiff(path, band_count=band_count)
        metadata = loader.read_metadata(path)
        assert metadata.band_count == band_count
        assert metadata.dtypes == ("uint8",) * band_count


# ---------------------------------------------------------------------------
# Convenience properties (task 6)
# ---------------------------------------------------------------------------
class TestGeoreferenceProperties:
    """Behaviour of ``is_georeferenced`` and ``crs_display``."""

    def test_properties_for_georeferenced_raster(
        self, loader: GeoTiffLoader, valid_geotiff: Path
    ) -> None:
        """A proper GeoTIFF reports georeferencing and a compact CRS."""
        metadata = loader.read_metadata(valid_geotiff)
        assert metadata.is_georeferenced is True
        assert metadata.crs_display == f"EPSG:{EPSG}"

    def test_is_geotiff_true_for_georeferenced_raster(
        self, loader: GeoTiffLoader, valid_geotiff: Path
    ) -> None:
        """The predicate accepts a georeferenced raster."""
        assert loader.is_geotiff(valid_geotiff) is True


# ---------------------------------------------------------------------------
# Plain TIFF without CRS (task 7)
# ---------------------------------------------------------------------------
class TestPlainTiffWithoutCrs:
    """A readable TIFF without georeferencing must not be a GeoTIFF."""

    @pytest.fixture
    def plain_tiff(self, tmp_path: Path) -> Path:
        """A valid TIFF written by Pillow, carrying no geo metadata."""
        path = tmp_path / "plain.tif"
        Image.fromarray(np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)).save(path)
        return path

    def test_missing_crs_is_handled_safely(
        self, loader: GeoTiffLoader, plain_tiff: Path
    ) -> None:
        """Metadata extraction succeeds with CRS/EPSG reported as None."""
        metadata = loader.read_metadata(plain_tiff)
        assert metadata.crs is None
        assert metadata.epsg is None
        assert metadata.crs_display == "none"
        assert metadata.is_georeferenced is False
        assert metadata.width == WIDTH
        assert metadata.height == HEIGHT

    def test_is_geotiff_false_for_plain_tiff(
        self, loader: GeoTiffLoader, plain_tiff: Path
    ) -> None:
        """Readable-but-plain TIFFs are distinguished from GeoTIFFs."""
        assert loader.is_geotiff(plain_tiff) is False


# ---------------------------------------------------------------------------
# Error handling (tasks 8-10)
# ---------------------------------------------------------------------------
class TestErrorHandling:
    """Missing, corrupted and misnamed files follow the project rules."""

    def test_missing_file_raises_project_exception(
        self, loader: GeoTiffLoader, tmp_path: Path
    ) -> None:
        """A non-existent path raises ImageLoadError from the hierarchy."""
        missing = tmp_path / "does_not_exist.tif"
        with pytest.raises(ImageLoadError) as excinfo:
            loader.read_metadata(missing)
        assert isinstance(excinfo.value, FloodVisionError)
        assert excinfo.value.path == missing

    def test_corrupted_file_raises_with_chained_cause(
        self, loader: GeoTiffLoader, tmp_path: Path
    ) -> None:
        """Garbage bytes raise ImageLoadError, preserving the cause chain."""
        corrupt = tmp_path / "corrupt.tif"
        corrupt.write_bytes(b"THIS IS NOT A RASTER FILE")
        with pytest.raises(ImageLoadError) as excinfo:
            loader.read_metadata(corrupt)
        assert excinfo.value.path == corrupt
        assert excinfo.value.__cause__ is not None

    def test_is_geotiff_false_for_corrupted_file(
        self, loader: GeoTiffLoader, tmp_path: Path
    ) -> None:
        """The predicate classifies corrupt files without raising."""
        corrupt = tmp_path / "corrupt.tif"
        corrupt.write_bytes(b"\x00\x01\x02\x03 garbage")
        assert loader.is_geotiff(corrupt) is False

    def test_is_geotiff_false_for_unsupported_extension(
        self, loader: GeoTiffLoader, tmp_path: Path
    ) -> None:
        """Files outside the extension set are rejected by the predicate."""
        png = tmp_path / "image.png"
        Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(png)
        assert png.suffix not in GEOTIFF_EXTENSIONS
        assert loader.is_geotiff(png) is False


# ---------------------------------------------------------------------------
# Valid CRS without EPSG representation (task 11)
# ---------------------------------------------------------------------------
class TestCrsWithoutEpsg:
    """Exotic but valid CRS definitions yield ``epsg=None`` safely."""

    def test_custom_crs_yields_none_epsg(
        self, loader: GeoTiffLoader, tmp_path: Path
    ) -> None:
        """A custom-centred projection keeps its CRS but has no EPSG."""
        crs = CRS.from_proj4(NO_EPSG_PROJ4)
        assert crs.to_epsg() is None  # precondition for a meaningful test
        path = tmp_path / "custom_crs.tif"
        write_geotiff(path, crs=crs)

        metadata = loader.read_metadata(path)
        assert metadata.crs is not None
        assert metadata.epsg is None
        assert metadata.is_georeferenced is True
        assert metadata.crs_display != "none"
