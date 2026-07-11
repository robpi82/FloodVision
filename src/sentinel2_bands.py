"""Sentinel-2 spectral band metadata.

This module provides structured metadata for Sentinel-2 spectral bands.
It is intentionally independent from GeoTIFF loading and raster
processing so band definitions can be reused by future multispectral,
NDWI, and Sentinel-2 workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Sentinel2Band:
    """Immutable metadata describing one Sentinel-2 spectral band.

    Attributes:
        code: Official Sentinel-2 band code.
        name: Human-readable spectral band name.
        resolution_m: Native spatial resolution in metres.
    """

    code: str
    name: str
    resolution_m: int


SENTINEL2_BANDS: Final[dict[str, Sentinel2Band]] = {
    "B02": Sentinel2Band(
        code="B02",
        name="Blue",
        resolution_m=10,
    ),
    "B03": Sentinel2Band(
        code="B03",
        name="Green",
        resolution_m=10,
    ),
    "B04": Sentinel2Band(
        code="B04",
        name="Red",
        resolution_m=10,
    ),
    "B05": Sentinel2Band(
        code="B05",
        name="Vegetation Red Edge",
        resolution_m=20,
    ),
    "B06": Sentinel2Band(
        code="B06",
        name="Vegetation Red Edge",
        resolution_m=20,
    ),
    "B07": Sentinel2Band(
        code="B07",
        name="Vegetation Red Edge",
        resolution_m=20,
    ),
    "B08": Sentinel2Band(
        code="B08",
        name="Near Infrared",
        resolution_m=10,
    ),
    "B8A": Sentinel2Band(
        code="B8A",
        name="Narrow Near Infrared",
        resolution_m=20,
    ),
    "B09": Sentinel2Band(
        code="B09",
        name="Water Vapour",
        resolution_m=60,
    ),
    "B10": Sentinel2Band(
        code="B10",
        name="Cirrus",
        resolution_m=60,
    ),
    "B11": Sentinel2Band(
        code="B11",
        name="Short-Wave Infrared",
        resolution_m=20,
    ),
    "B12": Sentinel2Band(
        code="B12",
        name="Short-Wave Infrared",
        resolution_m=20,
    ),
}


def get_sentinel2_band(code: str) -> Sentinel2Band:
    """Return metadata for a Sentinel-2 band code.

    Lookup is case-insensitive and ignores surrounding whitespace.

    Args:
        code: Sentinel-2 band code such as ``"B02"`` or ``"B08"``.

    Returns:
        Metadata for the requested Sentinel-2 band.

    Raises:
        ValueError: If the band code is unknown.
    """
    normalized_code = code.strip().upper()

    try:
        return SENTINEL2_BANDS[normalized_code]
    except KeyError as error:
        raise ValueError(
            f"Unknown Sentinel-2 band: {code}"
        ) from error


def get_sentinel2_band_indices(
    codes: tuple[str, ...],
) -> tuple[int, ...]:
    """Convert Sentinel-2 band codes to zero-based raster indices.

    Band codes are resolved using the order of the supported Sentinel-2
    band metadata catalog. Input order is preserved.

    Args:
        codes: Sentinel-2 band codes to convert.

    Returns:
        Zero-based raster indices corresponding to the requested band codes.

    Raises:
        ValueError: If any requested Sentinel-2 band code is unknown.
    """
    band_codes = tuple(SENTINEL2_BANDS)

    return tuple(
        band_codes.index(get_sentinel2_band(code).code)
        for code in codes
    )