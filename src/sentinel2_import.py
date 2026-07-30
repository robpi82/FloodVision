"""Combine individual Sentinel-2 band files into one importable GeoTIFF.

:func:`~src.sentinel2_band_stacker.stack_sentinel2_bands` produces an
in-memory, aligned multi-band raster from individual single-band
Sentinel-2 files -- but everything downstream of it (folder-pairing,
:class:`~src.batch_processor.BatchProcessor`, the GUI's Before/After
navigator and preview tabs) is built around *files on disk*: one
already-stacked multi-band GeoTIFF per Before/After image, exactly the
shape our synthetic test fixtures and the existing
:class:`~src.geotiff_raster_loader.GeoTiffRasterLoader` already handle.

This module is the bridge that closes that last gap: it writes the
in-memory stacked raster back out as a single combined GeoTIFF file, so
a user with a folder of individual Sentinel-2 band files (as shipped in
a Level-2A ``.SAFE`` product) can produce a file they can simply drop
into ``data/before``/``data/after`` like any other GeoTIFF pair -- no
further changes required anywhere else in the application.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

import rasterio
from rasterio.enums import Resampling
from rasterio.errors import RasterioError

from src.exceptions import GeoTiffExportError
from src.sentinel2_band_stacker import stack_sentinel2_bands
from src.sentinel2_bands import get_sentinel2_band

logger = logging.getLogger(__name__)

_DRIVER = "GTiff"


def combine_sentinel2_bands_to_geotiff(
    band_files: Mapping[str, Path],
    output_path: Path,
    resampling: Resampling = Resampling.bilinear,
) -> Path:
    """Stack individual Sentinel-2 band files and write them as one GeoTIFF.

    Combines :func:`~src.sentinel2_band_stacker.stack_sentinel2_bands`
    (alignment and resampling) with a single-file GeoTIFF write, so the
    result is a normal, self-contained multi-band GeoTIFF: one file,
    with each band's Sentinel-2 code embedded as its band description --
    exactly what
    :meth:`~src.geotiff_raster_loader.GeoTiffRasterLoader.load` and
    :class:`~src.spectral_detector.SpectralWaterDetector` already expect
    from any other GeoTIFF pair in ``data/before``/``data/after``.

    Args:
        band_files: Mapping of Sentinel-2 band code (e.g. ``"B03"``) to
            the single-band file containing it. See
            :func:`~src.sentinel2_band_stacker.stack_sentinel2_bands`
            for the full contract this follows (resolution checking,
            resampling, CRS validation).
        output_path: Target ``.tif`` path for the combined file; parent
            directories are created as needed.
        resampling: Resampling method for pixel values when a band's
            native resolution does not match the finest requested
            band's resolution.

    Returns:
        The path the combined GeoTIFF was written to (``output_path``).

    Raises:
        Sentinel2BandStackError: If the individual band files cannot be
            combined -- see
            :func:`~src.sentinel2_band_stacker.stack_sentinel2_bands`
            for the specific cases (missing/unreadable files, mismatched
            coordinate reference systems).
        ValueError: If a band code in ``band_files`` is not a known
            Sentinel-2 band -- a programmer-contract violation, not a
            runtime failure.
        GeoTiffExportError: If Rasterio or the filesystem cannot write
            the output file (disk full, permission denied).
    """
    raster = stack_sentinel2_bands(band_files, resampling=resampling)
    crs, transform = _reference_geospatial_frame(band_files)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(
            output_path,
            "w",
            driver=_DRIVER,
            width=raster.width,
            height=raster.height,
            count=raster.band_count,
            dtype=raster.data.dtype,
            crs=crs,
            transform=transform,
        ) as dataset:
            dataset.write(raster.data)
            for index, code in enumerate(raster.band_descriptions, start=1):
                if code is not None:
                    dataset.set_band_description(index, code)
    except (RasterioError, OSError) as error:
        raise GeoTiffExportError(output_path, str(error)) from error

    logger.info(
        "Combined Sentinel-2 GeoTIFF saved: %s (%d x %d px, %d band(s): %s)",
        output_path,
        raster.width,
        raster.height,
        raster.band_count,
        ", ".join(raster.band_descriptions),
    )
    return output_path


def _reference_geospatial_frame(
    band_files: Mapping[str, Path],
) -> tuple[rasterio.crs.CRS, rasterio.Affine]:
    """Read the CRS and affine transform of the finest requested band.

    Mirrors :func:`~src.sentinel2_band_stacker.stack_sentinel2_bands`'s
    own choice of reference band (the finest requested resolution), so
    the combined GeoTIFF is georeferenced on exactly the same grid the
    stacked pixel data was aligned to -- re-reading the file here rather
    than threading the value through the stacker's return type keeps
    that already-tested function's contract unchanged.

    Args:
        band_files: Same mapping passed to
            :func:`combine_sentinel2_bands_to_geotiff`.

    Returns:
        The reference band file's CRS and affine transform.
    """
    reference_code = min(
        band_files, key=lambda code: get_sentinel2_band(code).resolution_m
    )
    with rasterio.open(band_files[reference_code]) as dataset:
        return dataset.crs, dataset.transform
