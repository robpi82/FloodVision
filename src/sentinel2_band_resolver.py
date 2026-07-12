"""Sentinel-2 raster band resolution."""

from __future__ import annotations

from src.sentinel2_bands import get_sentinel2_band_indices


class Sentinel2BandResolver:
    """Resolve Sentinel-2 spectral bands from actual raster band order."""

    def resolve_rgb_indices(
        self,
        available_codes: tuple[str | None, ...],
    ) -> tuple[int, ...]:
        """Resolve RGB band indices from actual raster band descriptions."""
        return get_sentinel2_band_indices(
            ("B04", "B03", "B02"),
            available_codes=available_codes,
        )