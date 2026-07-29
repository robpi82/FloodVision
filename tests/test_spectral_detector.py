"""Tests for spectral water detector."""

from pathlib import Path

import numpy as np
import pytest

from src.geotiff_raster_loader import GeoTiffRasterData
from src.spectral_detector import SpectralWaterDetector
from src.spectral_indices import SPECTRAL_INDEX_MNDWI, SPECTRAL_INDEX_NDWI
from src.water_detection import WaterDetectionResult


def test_spectral_detector_creates_water_mask() -> None:
    """NDWI based detector identifies water pixels."""
    green = np.array(
        [
            [100, 50],
            [200, 100],
        ],
        dtype=np.uint16,
    )

    nir = np.array(
        [
            [50, 100],
            [100, 200],
        ],
        dtype=np.uint16,
    )

    detector = SpectralWaterDetector(
        ndwi_threshold=0.1,
    )

    result = detector.detect_from_bands(
        green,
        nir,
    )

    assert isinstance(result, WaterDetectionResult)
    assert result.mask.shape == green.shape

    assert result.mask[0, 0] == 255
    assert result.mask[0, 1] == 0
    assert result.mask[1, 0] == 255
    assert result.mask[1, 1] == 0


def test_spectral_detector_returns_coverage() -> None:
    """Coverage is calculated from the generated mask."""
    green = np.array(
        [
            [100, 50],
            [200, 100],
        ],
        dtype=np.uint16,
    )

    nir = np.array(
        [
            [50, 100],
            [100, 200],
        ],
        dtype=np.uint16,
    )

    detector = SpectralWaterDetector()

    result = detector.detect_from_bands(
        green,
        nir,
    )

    assert result.water_coverage_percent == 50.0

def test_spectral_detector_excludes_invalid_raster_pixels() -> None:
    """Invalid GeoTIFF pixels are excluded from mask and coverage."""
    green = np.array(
        [
            [100, 100],
            [200, 100],
        ],
        dtype=np.uint16,
    )
    nir = np.array(
        [
            [50, 50],
            [100, 200],
        ],
        dtype=np.uint16,
    )

    raster = GeoTiffRasterData(
        path=Path("sentinel2_test.tif"),
        data=np.stack([green, nir]),
        valid_mask=np.array(
            [
                [True, False],
                [True, True],
            ],
            dtype=bool,
        ),
        nodata=None,
        band_descriptions=("B03", "B08"),
    )

    detector = SpectralWaterDetector(ndwi_threshold=0.1)

    result = detector.detect(raster)

    assert result.mask[0, 0] == 255
    assert result.mask[0, 1] == 0
    assert result.mask[1, 0] == 255
    assert result.mask[1, 1] == 0
    assert result.water_coverage_percent == pytest.approx(200.0 / 3.0)

    assert result.valid_mask is not None
    np.testing.assert_array_equal(
        result.valid_mask,
        raster.valid_mask,
    )


# ---------------------------------------------------------------------------
# Spectral index selection (NDWI vs MNDWI)
# ---------------------------------------------------------------------------
def test_spectral_detector_defaults_to_ndwi() -> None:
    """Without an explicit index, the detector behaves as it always did (NDWI)."""
    detector = SpectralWaterDetector()

    assert detector._spectral_index == SPECTRAL_INDEX_NDWI


def test_spectral_detector_rejects_unknown_spectral_index() -> None:
    """An unsupported spectral index is rejected at construction time."""
    with pytest.raises(ValueError, match="invalid"):
        SpectralWaterDetector(spectral_index="invalid")


def test_mndwi_detector_creates_water_mask_from_green_and_swir() -> None:
    """MNDWI-based detection identifies water from Green/SWIR, like NDWI does for Green/NIR."""
    green = np.array(
        [
            [100, 50],
            [200, 100],
        ],
        dtype=np.uint16,
    )
    swir = np.array(
        [
            [50, 100],
            [100, 200],
        ],
        dtype=np.uint16,
    )

    detector = SpectralWaterDetector(
        ndwi_threshold=0.1,
        spectral_index=SPECTRAL_INDEX_MNDWI,
    )

    result = detector.detect_from_bands(green, swir)

    assert isinstance(result, WaterDetectionResult)
    assert result.mask[0, 0] == 255
    assert result.mask[0, 1] == 0
    assert result.mask[1, 0] == 255
    assert result.mask[1, 1] == 0


def test_mndwi_detector_reads_green_and_swir_bands_from_raster() -> None:
    """detect() resolves B03 (Green) and B11 (SWIR) when MNDWI is selected."""
    green = np.array(
        [
            [100, 50],
            [200, 100],
        ],
        dtype=np.uint16,
    )
    swir = np.array(
        [
            [50, 100],
            [100, 200],
        ],
        dtype=np.uint16,
    )

    raster = GeoTiffRasterData(
        path=Path("sentinel2_test.tif"),
        data=np.stack([green, swir]),
        valid_mask=np.ones(green.shape, dtype=bool),
        nodata=None,
        band_descriptions=("B03", "B11"),
    )

    detector = SpectralWaterDetector(
        ndwi_threshold=0.1,
        spectral_index=SPECTRAL_INDEX_MNDWI,
    )

    result = detector.detect(raster)

    assert result.mask[0, 0] == 255
    assert result.mask[0, 1] == 0
    assert result.mask[1, 0] == 255
    assert result.mask[1, 1] == 0


def test_ndwi_detector_still_reads_green_and_nir_bands_from_raster() -> None:
    """detect() continues to resolve B03/B08 when NDWI is explicitly selected."""
    green = np.array(
        [
            [100, 50],
            [200, 100],
        ],
        dtype=np.uint16,
    )
    nir = np.array(
        [
            [50, 100],
            [100, 200],
        ],
        dtype=np.uint16,
    )

    raster = GeoTiffRasterData(
        path=Path("sentinel2_test.tif"),
        data=np.stack([green, nir]),
        valid_mask=np.ones(green.shape, dtype=bool),
        nodata=None,
        band_descriptions=("B03", "B08"),
    )

    detector = SpectralWaterDetector(
        ndwi_threshold=0.1,
        spectral_index=SPECTRAL_INDEX_NDWI,
    )

    result = detector.detect(raster)

    assert result.mask[0, 0] == 255
    assert result.mask[0, 1] == 0
    assert result.mask[1, 0] == 255
    assert result.mask[1, 1] == 0

