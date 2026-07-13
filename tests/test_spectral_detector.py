"""Tests for spectral water detector."""

import numpy as np

from src.spectral_detector import SpectralWaterDetector
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