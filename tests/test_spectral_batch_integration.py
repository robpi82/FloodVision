"""Integration tests for the Sentinel-2 spectral detection workflow."""

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.batch_processor import BatchProcessor, ProcessingStatus
from src.geotiff_raster_loader import GeoTiffRasterData
from src.image_loader import ImageLoader
from src.spectral_detector import SpectralWaterDetector

WIDTH = 64
HEIGHT = 48
UTM32 = "EPSG:32632"
PIXEL_SIZE = 10.0
ORIGIN_X = 699_960.0
ORIGIN_Y = 5_300_040.0


def test_spectral_detector_accepts_sentinel2_raster() -> None:
    """B03/B08 bands are extracted and converted into a water mask."""
    green = np.array(
        [
            [100, 100],
            [100, 100],
        ],
        dtype=np.uint16,
    )

    nir = np.array(
        [
            [20, 20],
            [200, 200],
        ],
        dtype=np.uint16,
    )

    raster = GeoTiffRasterData(
        path=Path("test.tif"),
        data=np.stack(
            [
                green,
                nir,
            ]
        ),
        valid_mask=np.ones(
            (2, 2),
            dtype=bool,
        ),
        nodata=None,
        band_descriptions=(
            "B03",
            "B08",
        ),
    )

    detector = SpectralWaterDetector(
        ndwi_threshold=0.1,
    )

    result = detector.detect(raster)

    assert result.mask.shape == (2, 2)
    assert result.water_coverage_percent == 50.0


def write_sentinel2_geotiff(
    path: Path,
    *,
    flooded: bool,
) -> None:
    """Create a synthetic four-band Sentinel-2-like GeoTIFF."""
    data = np.zeros(
        (4, HEIGHT, WIDTH),
        dtype=np.uint16,
    )

    # Raster order: B02, B03, B04, B08.
    data[0] = 80
    data[1] = 100
    data[2] = 120
    data[3] = 200

    if flooded:
        # High green and low NIR produce a positive NDWI value.
        data[1, 10:38, 20:50] = 200
        data[3, 10:38, 20:50] = 50

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=WIDTH,
        height=HEIGHT,
        count=4,
        dtype="uint16",
        crs=UTM32,
        transform=from_origin(
            ORIGIN_X,
            ORIGIN_Y,
            PIXEL_SIZE,
            PIXEL_SIZE,
        ),
    ) as dataset:
        dataset.write(data)
        dataset.set_band_description(1, "B02")
        dataset.set_band_description(2, "B03")
        dataset.set_band_description(3, "B04")
        dataset.set_band_description(4, "B08")


def test_sentinel2_before_after_pair_uses_spectral_detection(
    tmp_path: Path,
) -> None:
    """The real batch pipeline detects newly flooded Sentinel-2 pixels."""
    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    output_dir = tmp_path / "output"

    before_dir.mkdir()
    after_dir.mkdir()

    write_sentinel2_geotiff(
        before_dir / "sentinel2_flood.tif",
        flooded=False,
    )
    write_sentinel2_geotiff(
        after_dir / "sentinel2_flood.tif",
        flooded=True,
    )

    processor = BatchProcessor(
        loader=ImageLoader(),
        detector=SpectralWaterDetector(
            ndwi_threshold=0.1,
        ),
        before_dir=before_dir,
        after_dir=after_dir,
        output_dir=output_dir,
    )

    result = processor.run()

    assert len(result.records) == 1

    record = result.records[0]

    expected_flood_pixels = 28 * 30
    expected_flood_percent = (
        expected_flood_pixels
        / (WIDTH * HEIGHT)
        * 100.0
    )

    assert record.status is ProcessingStatus.SUCCESS
    assert record.error_message is None
    assert record.water_before_percent == pytest.approx(0.0)
    assert record.water_after_percent == pytest.approx(
        expected_flood_percent
    )
    assert record.new_flood_pixels == expected_flood_pixels
    assert record.new_water_percent == pytest.approx(
        expected_flood_percent
    )
    assert record.increase_percent == pytest.approx(
        expected_flood_percent
    )

    product_dir = output_dir / "sentinel2_flood"

    assert (product_dir / "overlay.png").is_file()
    assert (product_dir / "new_flood_mask.png").is_file()
    assert (product_dir / "new_flood_mask.tif").is_file()

    with rasterio.open(
        product_dir / "new_flood_mask.tif"
    ) as dataset:
        exported_mask = dataset.read(1)

        assert dataset.crs.to_string() == UTM32
        assert dataset.width == WIDTH
        assert dataset.height == HEIGHT
        assert np.count_nonzero(exported_mask == 255) == expected_flood_pixels