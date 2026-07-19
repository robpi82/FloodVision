"""Shared linear value stretching for raster display conversion."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.geotiff_raster_loader import GeoTiffRasterData


@dataclass(frozen=True)
class Stretch:
    """A fixed linear value range mapped onto the 0-255 display range."""

    lo: float
    hi: float

    def __post_init__(self) -> None:
        if not np.isfinite(self.lo) or not np.isfinite(self.hi):
            raise ValueError("Stretch bounds must be finite.")

        if self.hi <= self.lo:
            raise ValueError("Stretch requires hi > lo.")

    def apply(self, data: np.ndarray) -> np.ndarray:
        """Map raster values onto uint8 using this fixed value range."""
        scaled = (data.astype(float) - self.lo) / (self.hi - self.lo) * 255.0
        return np.clip(scaled, 0, 255).astype(np.uint8)


def compute_shared_stretch(
    *rasters: GeoTiffRasterData,
    bands: tuple[int, ...] | None = None,
) -> Stretch | None:
    """Compute a single stretch shared by all given rasters.

    A per-image stretch maps identical physical pixel values onto different
    display values, because the value range differs between the rasters of a
    before/after pair. Newly flooded, dark pixels lower the minimum of the
    "after" raster, which shifts every unchanged pixel in that raster as well.
    Change detection then reacts to the normalisation instead of the scene.

    Deriving one value range from all rasters of the pair removes that bias.

    Returns None when no shared stretch can be derived, either because no
    valid pixels exist or because the value range is constant. Callers should
    then fall back to the legacy per-image behaviour.
    """
    lows: list[float] = []
    highs: list[float] = []

    for raster in rasters:
        data = raster.data if bands is None else raster.data[list(bands)]
        values = data[:, raster.valid_mask]

        if values.size == 0:
            continue

        finite = values[np.isfinite(values)]

        if finite.size == 0:
            continue

        lows.append(float(np.min(finite)))
        highs.append(float(np.max(finite)))

    if not lows:
        return None

    lo = min(lows)
    hi = max(highs)

    if hi <= lo:
        return None

    return Stretch(lo=lo, hi=hi)