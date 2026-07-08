from pathlib import Path

import numpy as np
import pytest
import rasterio
from PIL import Image
from rasterio.transform import from_origin

from src.batch_processor import BatchProcessor, ProcessingStatus
from src.image_loader import ImageLoader


class Detector:
    def detect(self, image):
        raise RuntimeError("downstream reached")


def write_tif(path: Path, *, crs="EPSG:32632", width=4, transform=None):
    transform = transform or from_origin(500000, 5200000, 10, 10)
    with rasterio.open(path, "w", driver="GTiff", width=width, height=4,
                       count=3, dtype="uint8", crs=crs, transform=transform) as dst:
        dst.write(np.zeros((3, 4, width), dtype=np.uint8))


def processor(tmp_path):
    before = tmp_path / "before"; after = tmp_path / "after"; output = tmp_path / "out"
    before.mkdir(); after.mkdir()
    return BatchProcessor(ImageLoader(before), Detector(), before, after, output), before, after


def test_incompatible_crs_is_rejected_before_detection(tmp_path):
    p, before, after = processor(tmp_path)
    write_tif(before / "pair.tif", crs="EPSG:32632")
    write_tif(after / "pair.tif", crs="EPSG:4326")
    result = p.run()
    assert result.records[0].status is ProcessingStatus.FAILED
    assert "Incompatible GeoTIFF pair" in result.records[0].error_message


def test_incompatible_dimensions_are_rejected(tmp_path):
    p, before, after = processor(tmp_path)
    write_tif(before / "pair.tif", width=4); write_tif(after / "pair.tif", width=5)
    result = p.run()
    assert result.records[0].status is ProcessingStatus.FAILED
    assert "width differs" in result.records[0].error_message


def test_mixed_pair_is_rejected(tmp_path):
    p, before, after = processor(tmp_path)
    write_tif(before / "pair.tif")
    Image.new("RGB", (4, 4)).save(after / "pair.tif")
    result = p.run()
    assert result.records[0].status is ProcessingStatus.FAILED
    assert "Mixed image pair" in result.records[0].error_message


def test_compatible_geotiff_reaches_new_pipeline(tmp_path):
    p, before, after = processor(tmp_path)
    write_tif(before / "pair.tif"); write_tif(after / "pair.tif")
    result = p.run()
    assert result.records[0].status is ProcessingStatus.FAILED
    assert result.records[0].error_message == "downstream reached"


def test_normal_images_bypass_geotiff_rejection(tmp_path):
    p, before, after = processor(tmp_path)
    Image.new("RGB", (4, 4)).save(before / "pair.png")
    Image.new("RGB", (4, 4)).save(after / "pair.png")
    result = p.run()
    assert result.records[0].error_message == "downstream reached"


class RecordingDetector:
    def __init__(self):
        self.images = []

    def detect(self, image):
        self.images.append(image)
        raise RuntimeError("downstream reached")


def test_compatible_geotiff_is_adapted_to_rgb_before_detection(tmp_path):
    before = tmp_path / "before"; after = tmp_path / "after"; output = tmp_path / "out"
    before.mkdir(); after.mkdir()
    detector = RecordingDetector()
    p = BatchProcessor(ImageLoader(before), detector, before, after, output)
    write_tif(before / "pair.tif"); write_tif(after / "pair.tif")

    result = p.run()

    assert result.records[0].error_message == "downstream reached"
    assert len(detector.images) == 1
    assert detector.images[0].mode == "RGB"


def test_unsupported_geotiff_band_count_fails_before_detection(tmp_path):
    p, before, after = processor(tmp_path)
    transform = from_origin(500000, 5200000, 10, 10)
    for directory in (before, after):
        with rasterio.open(directory / "pair.tif", "w", driver="GTiff", width=4,
                           height=4, count=1, dtype="uint8", crs="EPSG:32632",
                           transform=transform) as dst:
            dst.write(np.zeros((1, 4, 4), dtype=np.uint8))

    result = p.run()

    assert result.records[0].status is ProcessingStatus.FAILED
    assert "exactly 3 bands" in result.records[0].error_message
