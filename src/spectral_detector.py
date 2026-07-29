"""Spectral water detection using Sentinel-2 indices.

This module provides a spectral alternative to HSV colour detection.
Instead of analysing RGB appearance, it uses physical spectral
relationships such as NDWI or MNDWI to identify water surfaces.
"""

from __future__ import annotations

from typing import Final

import numpy as np

from src import spectral_water_detection
from src.geotiff_raster_loader import GeoTiffRasterData
from src.spectral_band_extractor import get_spectral_band
from src.spectral_indices import (
    SPECTRAL_INDEX_MNDWI,
    SPECTRAL_INDEX_NDWI,
    VALID_SPECTRAL_INDICES,
    calculate_mndwi,
    calculate_ndwi,
)
from src.water_detection import WaterDetectionResult

# Sentinel-2 band feeding the second half of each supported index, alongside
# the Green band (B03) both indices share. NDWI contrasts Green against Near
# Infrared; MNDWI substitutes Short-Wave Infrared, which is less sensitive to
# turbidity and better suited to distinguishing water from built-up areas.
_SECONDARY_BAND_BY_INDEX: dict[str, str] = {
    SPECTRAL_INDEX_NDWI: "B08",
    SPECTRAL_INDEX_MNDWI: "B11",
}

DEFAULT_SPECTRAL_THRESHOLD: Final[float] = 0.1


class SpectralWaterDetector:
    """Detect water using Sentinel-2 spectral information."""

    def __init__(
        self,
        ndwi_threshold: float = DEFAULT_SPECTRAL_THRESHOLD,
        spectral_index: str = SPECTRAL_INDEX_NDWI,
    ) -> None:
        """Initialise the spectral detector.

        Args:
            ndwi_threshold: Minimum index value classified as water. Applies
                to whichever index is selected; the name is kept from the
                original NDWI-only detector for backward compatibility with
                existing keyword-argument call sites.
            spectral_index: Which spectral index to use -- one of
                :data:`~src.spectral_indices.SPECTRAL_INDEX_NDWI` or
                :data:`~src.spectral_indices.SPECTRAL_INDEX_MNDWI`.

        Raises:
            ValueError: If ``spectral_index`` is not a supported index.
        """
        if spectral_index not in VALID_SPECTRAL_INDICES:
            raise ValueError(f"Unsupported spectral index: {spectral_index!r}")

        self._ndwi_threshold = ndwi_threshold
        self._spectral_index = spectral_index

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
        secondary = get_spectral_band(
            raster, _SECONDARY_BAND_BY_INDEX[self._spectral_index]
        )

        return self.detect_from_bands(
            green,
            secondary,
            valid_mask=raster.valid_mask,
        )

    def detect_from_bands(
        self,
        green: np.ndarray,
        secondary: np.ndarray,
        valid_mask: np.ndarray | None = None,
    ) -> WaterDetectionResult:
        """Detect water from a Sentinel-2 Green band and one other band.

        Args:
            green: Sentinel-2 B03 band, used by both supported indices.
            secondary: The band paired with Green for the configured index --
                B08 (NIR) for NDWI, B11 (SWIR) for MNDWI.
            valid_mask: Optional validity mask. Invalid pixels are excluded
                from classification and coverage statistics.

        Returns:
            Standard FloodVision water detection result.
        """
        if self._spectral_index == SPECTRAL_INDEX_MNDWI:
            index = calculate_mndwi(green, secondary)
        else:
            index = calculate_ndwi(green, secondary, valid_mask=valid_mask)

        mask = spectral_water_detection.ndwi_to_mask(
            index,
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
            index_values=index,
        )