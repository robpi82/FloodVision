"""Spectral water detection using Sentinel-2 indices.

This module provides a spectral alternative to HSV colour detection.
Instead of analysing RGB appearance, it uses physical spectral
relationships such as NDWI to identify water surfaces.
"""

from __future__ import annotations

import numpy as np

from src import spectral_water_detection
from src.geotiff_raster_loader import GeoTiffRasterData
from src.spectral_band_extractor import get_spectral_band
from src.spectral_indices import calculate_ndwi
from src.water_detection import WaterDetectionResult


class SpectralWaterDetector:
    """Detect water using Sentinel-2 spectral information."""

    def __init__(
        self,
        ndwi_threshold: float = 0.1,
    ) -> None:
        """Initialise the spectral detector.

        Args:
            ndwi_threshold: Minimum NDWI value classified as water.
        """
        self._ndwi_threshold = ndwi_threshold

    def detect(
        self,
        raster: GeoTiffRasterData,
    ) -> WaterDetectionResult:
        """Detect water directly from a Sentinel-2 raster.

        Invalid and NoData pixels are excluded from classification and
        water-coverage statistics.

        Args:
            raster: Loaded Sentinel-2 GeoTIFF raster data.

        Returns:
            Standard FloodVision water detection result.
        """
        green = get_spectral_band(raster, "B03")
        nir = get_spectral_band(raster, "B08")

        return self.detect_from_bands(
            green,
            nir,
            valid_mask=raster.valid_mask,
        )

    def detect_from_bands(
        self,
        green: np.ndarray,
        nir: np.ndarray,
        valid_mask: np.ndarray | None = None,
    ) -> WaterDetectionResult:
        """Detect water from Sentinel-2 Green and NIR bands.

        Args:
            green: Sentinel-2 B03 band.
            nir: Sentinel-2 B08 band.
            valid_mask: Optional validity mask. Invalid pixels are excluded
                from classification and coverage statistics.

        Returns:
            Standard FloodVision water detection result.
        """
        ndwi = calculate_ndwi(
            green,
            nir,
            valid_mask=valid_mask,
        )

        mask = spectral_water_detection.ndwi_to_mask(
            ndwi,
            threshold=self._ndwi_threshold,
            valid_mask=valid_mask,
        )

        coverage = spectral_water_detection.spectral_water_coverage_percent(
            mask,
            valid_mask=valid_mask,
        )

        rgb_placeholder = np.zeros(
            (*mask.shape, 3),
            dtype=np.uint8,
        )

        return WaterDetectionResult(
            image_rgb=rgb_placeholder,
            raw_mask=mask,
            mask=mask,
            water_coverage_percent=coverage,
            valid_mask=valid_mask,
        )