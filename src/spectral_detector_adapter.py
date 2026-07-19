"""Adapter connecting spectral detection to FloodVision detector interface."""

from __future__ import annotations

from PIL import Image

from src.water_detection import WaterDetectionResult


class SpectralDetectorAdapter:
    """Adapter for using spectral detection inside FloodVision pipeline."""

    def __init__(self, detector) -> None:
        self._detector = detector

    def detect(self, image: Image.Image) -> WaterDetectionResult:
        """Run spectral detection.

        This method keeps compatibility with WaterSegmentationStrategy.
        """
        raise NotImplementedError(
            "Spectral GeoTIFF adapter integration comes next."
        )