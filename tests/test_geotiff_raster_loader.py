"""Automated tests for :mod:`src.geotiff_raster_loader`."""

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.exceptions import ImageLoadError
from src.geotiff_raster_loader import GeoTiffRasterLoader


def write_raster(
    path: Path,
    *,
    band_count: int = 3,
    nodata: int | None = 0,
) -> np.ndarray:
    data = np.arange(
        band_count * 4 * 5, dtype=np.uint8
    ).reshape(band_count, 4, 5)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=5,
        height=4,
        count=band_count,
        dtype="uint8",
        crs="EPSG:32632",
        transform=from_origin(500000, 5200000, 10, 10),
        nodata=nodata,
    ) as dataset:
        dataset.write(data)

    return data


@pytest.fixture
def loader() -> GeoTiffRasterLoader:
    return GeoTiffRasterLoader()


def test_load_preserves_pixel_values(
    loader: GeoTiffRasterLoader, tmp_path: Path
) -> None:
    path = tmp_path / "raster.tif"
    expected = write_raster(path)

    result = loader.load(path)

    np.testing.assert_array_equal(result.data, expected)


def test_load_preserves_band_descriptions(
    loader: GeoTiffRasterLoader,
    tmp_path: Path,
) -> None:
    path = tmp_path / "sentinel2_bands.tif"
    write_raster(path, band_count=3)

    with rasterio.open(path, "r+") as dataset:
        dataset.set_band_description(1, "B04")
        dataset.set_band_description(2, "B03")
        dataset.set_band_description(3, "B02")

    result = loader.load(path)

    assert result.band_descriptions == ("B04", "B03", "B02")


@pytest.mark.parametrize("band_count", [1, 2, 3])
def test_load_supports_band_counts(
    loader: GeoTiffRasterLoader, tmp_path: Path, band_count: int
) -> None:
    path = tmp_path / f"{band_count}_bands.tif"
    write_raster(path, band_count=band_count)

    result = loader.load(path)

    assert result.band_count == band_count
    assert result.height == 4
    assert result.width == 5
    assert result.data.shape == (band_count, 4, 5)


def test_nodata_creates_invalid_pixels(
    loader: GeoTiffRasterLoader, tmp_path: Path
) -> None:
    path = tmp_path / "nodata.tif"
    write_raster(path, band_count=1, nodata=0)

    result = loader.load(path)

    assert result.nodata == 0
    assert result.valid_mask.shape == (4, 5)
    assert result.valid_mask.dtype == np.bool_
    assert result.valid_mask[0, 0] == np.False_
    assert result.valid_mask[0, 1] == np.True_


def test_raster_without_nodata_is_fully_valid(
    loader: GeoTiffRasterLoader, tmp_path: Path
) -> None:
    path = tmp_path / "no_nodata.tif"
    write_raster(path, nodata=None)

    result = loader.load(path)

    assert result.nodata is None
    assert result.valid_mask.all()


def test_missing_file_raises_image_load_error(
    loader: GeoTiffRasterLoader, tmp_path: Path
) -> None:
    missing = tmp_path / "missing.tif"

    with pytest.raises(ImageLoadError) as excinfo:
        loader.load(missing)

    assert excinfo.value.path == missing


def test_corrupt_file_preserves_exception_chain(
    loader: GeoTiffRasterLoader, tmp_path: Path
) -> None:
    path = tmp_path / "corrupt.tif"
    path.write_bytes(b"not a raster")

    with pytest.raises(ImageLoadError) as excinfo:
        loader.load(path)

    assert excinfo.value.path == path
    assert excinfo.value.__cause__ is not None
