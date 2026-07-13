"""Integration tests for Sentinel-2 spectral detection workflow."""

from pathlib import Path

import numpy as np

from src.geotiff_raster_loader import GeoTiffRasterData
from src.spectral_detector import SpectralWaterDetector


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