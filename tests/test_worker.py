import pytest

from src.exceptions import FloodVisionError
from src.gui.app_settings import (
    DETECTION_MODE_HSV,
    DETECTION_MODE_SPECTRAL,
    AppSettings,
)
from src.gui.worker import _create_detector
from src.spectral_detector import SpectralWaterDetector
from src.spectral_indices import SPECTRAL_INDEX_MNDWI
from src.water_detection import HSVWaterDetector


def test_create_detector_returns_spectral_detector_for_spectral_mode() -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_SPECTRAL)

    detector = _create_detector(settings)

    assert isinstance(detector, SpectralWaterDetector)


def test_create_detector_returns_hsv_detector_for_hsv_mode() -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_HSV)

    detector = _create_detector(settings)

    assert isinstance(detector, HSVWaterDetector)


def test_create_detector_uses_configured_hsv_values() -> None:
    settings = AppSettings(
        detection_mode=DETECTION_MODE_HSV,
        hsv_lower=(80, 40, 30),
        hsv_upper=(140, 255, 255),
    )

    detector = _create_detector(settings)

    # HSVWaterDetector has no public accessor for its configured range;
    # the range object itself is the smallest public-ish surface available.
    assert detector._hsv_range.lower == (80, 40, 30)
    assert detector._hsv_range.upper == (140, 255, 255)


def test_create_detector_raises_for_unsupported_mode() -> None:
    settings = AppSettings(detection_mode="invalid")

    with pytest.raises(FloodVisionError, match="invalid"):
        _create_detector(settings)


def test_create_detector_passes_spectral_index_through() -> None:
    settings = AppSettings(
        detection_mode=DETECTION_MODE_SPECTRAL,
        spectral_index=SPECTRAL_INDEX_MNDWI,
    )

    detector = _create_detector(settings)

    assert detector._spectral_index == SPECTRAL_INDEX_MNDWI
