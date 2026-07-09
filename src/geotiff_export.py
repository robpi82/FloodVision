"""Georeferenced export of flood-detection results as GeoTIFF.

Writes FloodVision's binary "new flood" mask -- the same array already
rendered as ``new_flood_mask.png`` -- as a single-band, georeferenced
GeoTIFF that opens directly in GIS software (QGIS, ArcGIS Pro). This is
the write counterpart to :mod:`src.geotiff_loader` (read) and
:mod:`src.geotiff_compatibility` (compare); this module only writes.

Value convention:
    The exported raster reuses
    :class:`~src.change_detection.MaskComparison`'s existing convention
    verbatim -- ``0`` = no newly detected flood, ``255`` = newly
    detected flood -- so no pixel transformation happens here at all,
    only georeferencing is added around the same array that already
    produces ``new_flood_mask.png``.

NoData semantics:
    The output is written **without** a NoData value, even when the
    source raster defines one. The source's NoData marks *missing
    sensor data*; this mask is a derived two-class product where both
    ``0`` and ``255`` are equally valid, meaningful classifications.
    Reusing the source's NoData value (commonly ``0``) on this output
    would wrongly mark every "not flooded" pixel as missing data, which
    GIS software would then render as transparent/absent instead of as
    a real, negative detection result.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import RasterioError

from src.exceptions import GeoTiffExportError
from src.geotiff_loader import GeoTiffMetadata
from src.mask_generator import MaskArray

logger = logging.getLogger(__name__)

#: GDAL driver used for the exported raster.
_DRIVER = "GTiff"


def export_flood_mask_geotiff(
    mask: MaskArray,
    geo_metadata: GeoTiffMetadata,
    output_path: Path,
) -> Path:
    """Write a binary flood mask as a georeferenced single-band GeoTIFF.

    Args:
        mask: Binary flood mask, ``(height, width)`` uint8 with values
            ``0`` (no new flood) and ``255`` (new flood) -- the exact
            array underlying ``new_flood_mask.png``.
        geo_metadata: Metadata of the source GeoTIFF, providing the CRS,
            affine transform and raster dimensions used to georeference
            the output.
        output_path: Target ``.tif`` path; parent directories are
            created as needed.

    Returns:
        The path the GeoTIFF was written to (``output_path``).

    Raises:
        ValueError: If ``mask`` is not a 2-D uint8 array, or its shape
            does not match ``geo_metadata``'s dimensions -- a
            programmer-contract violation, not a runtime failure.
        GeoTiffExportError: If Rasterio or the filesystem cannot write
            the file (disk full, permission denied, invalid raster
            parameters).
    """
    _validate_mask_matches_metadata(mask, geo_metadata)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(
            output_path,
            "w",
            driver=_DRIVER,
            width=geo_metadata.width,
            height=geo_metadata.height,
            count=1,
            dtype="uint8",
            crs=geo_metadata.crs,
            transform=geo_metadata.transform,
        ) as dataset:
            dataset.write(mask, 1)
    except (RasterioError, OSError) as error:
        raise GeoTiffExportError(output_path, str(error)) from error

    logger.info(
        "Georeferenced flood mask saved: %s (%d x %d px, CRS %s)",
        output_path,
        geo_metadata.width,
        geo_metadata.height,
        geo_metadata.crs_display,
    )
    return output_path


def _validate_mask_matches_metadata(
    mask: MaskArray, geo_metadata: GeoTiffMetadata
) -> None:
    """Fail fast on shape/dtype contract violations.

    Mirrors the validation style of
    :func:`src.change_detection.compare_masks` and
    :func:`src.mask_generator._validate_mask`: a wrong shape or dtype
    here is a bug in the calling code, not a runtime/environment
    failure, so it raises plain ``ValueError`` rather than a
    :class:`~src.exceptions.FloodVisionError` subclass.

    Args:
        mask: Candidate flood mask.
        geo_metadata: Metadata the mask is meant to be exported against.

    Raises:
        ValueError: If the mask's dtype or shape is wrong.
    """
    if mask.ndim != 2 or mask.dtype != np.uint8:
        raise ValueError(
            f"mask must be 2-D uint8, got ndim={mask.ndim}, dtype={mask.dtype}."
        )
    expected_shape = (geo_metadata.height, geo_metadata.width)
    if mask.shape != expected_shape:
        raise ValueError(
            f"mask shape {mask.shape} does not match geo_metadata "
            f"dimensions {expected_shape} (height, width)."
        )