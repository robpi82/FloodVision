from src.gui.app_settings import AppSettings
from src.gui.worker import _create_detector
from src.spectral_detector import SpectralWaterDetector


def test_create_detector_returns_spectral_detector_for_spectral_mode() -> None:
    settings = AppSettings(detection_mode="spectral")

    detector = _create_detector(settings)

    assert isinstance(detector, SpectralWaterDetector)