"""Combine individual Sentinel-2 band files into one aligned raster.

Real Sentinel-2 Level-2A products (as delivered in the ``.SAFE`` folder
structure) ship each spectral band as its own single-band file, grouped
by native resolution (``R10m``, ``R20m``, ``R60m``). Everything else in
this project -- :class:`~src.spectral_detector.SpectralWaterDetector`,
:mod:`src.batch_processor`, the settings-dialog spectral-index workflow
-- expects a single, already-stacked :class:`~src.geotiff_raster_loader.
GeoTiffRasterData` with all needed bands on one common pixel grid, the
same shape :class:`~src.geotiff_raster_loader.GeoTiffRasterLoader`
already produces from our single-file synthetic test fixtures.

This module is the bridge between the two: it loads a set of single-band
files, checks their native resolutions against
:data:`~src.sentinel2_bands.SENTINEL2_BANDS`, resamples any band coarser
than the finest one onto that finest band's exact pixel grid, and stacks
the result into one :class:`GeoTiffRasterData` -- so the rest of the
pipeline needs no changes at all to work with real Sentinel-2 tiles.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.warp import reproject

from src.exceptions import Sentinel2BandStackError
from src.geotiff_raster_loader import GeoTiffRasterData
from src.sentinel2_bands import get_sentinel2_band

logger = logging.getLogger(__name__)


def stack_sentinel2_bands(
    band_files: Mapping[str, Path],
    resampling: Resampling = Resampling.bilinear,
) -> GeoTiffRasterData:
    """Load, align and stack individual Sentinel-2 band files.

    All bands finer than the coarsest requested resolution are left
    untouched; every band coarser than the finest requested resolution
    (in practice: 20 m bands such as B11 alongside 10 m bands such as
    B03/B08) is resampled onto the finest band's exact transform and
    shape before stacking, so every pixel in the returned raster lines
    up across bands -- a prerequisite
    :class:`~src.spectral_detector.SpectralWaterDetector` silently
    assumes but :class:`~src.geotiff_raster_loader.GeoTiffRasterLoader`
    never had to enforce, since our single-file test fixtures are
    already on one grid by construction.

    Pixel values are resampled with ``resampling`` (bilinear by
    default, appropriate for continuous reflectance values); each
    band's validity mask is resampled separately with nearest-neighbour
    interpolation regardless of ``resampling``, since a validity mask
    must stay binary -- interpolating it would blur the boundary
    between valid and invalid pixels into meaningless fractional
    values.

    Args:
        band_files: Mapping of Sentinel-2 band code (e.g. ``"B03"``) to
            the single-band file containing it. Order is preserved in
            the returned raster's band stacking order. Any format
            Rasterio/GDAL can read is accepted (GeoTIFF, JPEG2000 as
            shipped in ``.SAFE`` products, etc.).
        resampling: Resampling method for pixel values when a band's
            native resolution does not match the finest requested
            band's resolution.

    Returns:
        A single :class:`GeoTiffRasterData` with one band per requested
        Sentinel-2 band, all aligned to the finest requested band's
        pixel grid, band descriptions set to the requested band codes
        in input order, and a merged validity mask that is ``True``
        only where every contributing band is valid.

    Raises:
        Sentinel2BandStackError: If ``band_files`` is empty, a file
            cannot be read, or the requested bands are not all in the
            same coordinate reference system (e.g. tiles from two
            different UTM zones) -- a domain error the caller can fix
            by supplying compatible input files.
        ValueError: If a band code in ``band_files`` is not a known
            Sentinel-2 band -- a programmer-contract violation, not a
            runtime failure (mirrors
            :func:`src.sentinel2_bands.get_sentinel2_band`).
    """
    if not band_files:
        raise Sentinel2BandStackError("no band files were provided.")

    for code in band_files:
        get_sentinel2_band(code)  # raises ValueError for an unknown code

    loaded = {code: _load_single_band(code, path) for code, path in band_files.items()}

    _ensure_single_crs(loaded)

    reference_code = min(
        loaded, key=lambda code: get_sentinel2_band(code).resolution_m
    )
    reference = loaded[reference_code]

    bands: list[np.ndarray] = []
    valid_mask = np.ones(reference.data.shape, dtype=bool)

    for code, band in loaded.items():
        native_resolution = get_sentinel2_band(code).resolution_m
        reference_resolution = get_sentinel2_band(reference_code).resolution_m

        if native_resolution == reference_resolution:
            bands.append(band.data)
            valid_mask &= band.valid_mask
            continue

        logger.info(
            "Resampling Sentinel-2 band %s from %d m to %d m to match band %s",
            code,
            native_resolution,
            reference_resolution,
            reference_code,
        )
        resampled_data, resampled_mask = _resample_to_reference(
            band, reference, resampling
        )
        bands.append(resampled_data)
        valid_mask &= resampled_mask

    stacked = np.stack(bands, axis=0)

    return GeoTiffRasterData(
        path=next(iter(band_files.values())),
        data=stacked,
        valid_mask=valid_mask,
        nodata=None,
        band_descriptions=tuple(band_files.keys()),
    )


class _SingleBand:
    """Internal payload of one loaded single-band file, pre-stacking."""

    __slots__ = ("crs", "data", "transform", "valid_mask")

    def __init__(
        self,
        data: np.ndarray,
        valid_mask: np.ndarray,
        crs: CRS,
        transform: rasterio.Affine,
    ) -> None:
        self.data = data
        self.valid_mask = valid_mask
        self.crs = crs
        self.transform = transform


def _load_single_band(code: str, path: Path) -> _SingleBand:
    """Read one single-band raster file's first band, mask and geospatial frame.

    Args:
        code: Sentinel-2 band code this file is expected to contain
            (used only for error messages).
        path: Path to the single-band raster file.

    Returns:
        The loaded pixel data, validity mask, CRS and affine transform.

    Raises:
        Sentinel2BandStackError: If the file does not exist or cannot
            be read by Rasterio/GDAL.
    """
    if not path.is_file():
        raise Sentinel2BandStackError(f"band {code} file not found: '{path}'.")

    try:
        with rasterio.open(path) as dataset:
            data = dataset.read(1)
            valid_mask = dataset.dataset_mask() > 0
            crs = dataset.crs
            transform = dataset.transform
    except Exception as error:
        raise Sentinel2BandStackError(
            f"failed to read band {code} from '{path}': {error}"
        ) from error

    return _SingleBand(data=data, valid_mask=valid_mask, crs=crs, transform=transform)


def _ensure_single_crs(loaded: Mapping[str, _SingleBand]) -> None:
    """Fail fast if the requested bands do not share one CRS.

    Bands in different coordinate reference systems (e.g. tiles from
    two different UTM zones, or a caller mixing tiles from different
    Sentinel-2 granules) cannot be aligned onto one pixel grid at all;
    reprojecting across CRSes is a materially different, much more
    expensive operation than the same-CRS resampling this module
    performs, and out of scope here.

    Args:
        loaded: Already-loaded bands, keyed by band code.

    Raises:
        Sentinel2BandStackError: If more than one distinct CRS is
            present among the loaded bands.
    """
    distinct_crs = {band.crs for band in loaded.values()}
    if len(distinct_crs) > 1:
        crs_by_band = {code: band.crs.to_string() for code, band in loaded.items()}
        raise Sentinel2BandStackError(
            "requested bands are not all in the same coordinate reference "
            f"system: {crs_by_band}. Supply bands from a single tile/granule."
        )


def _resample_to_reference(
    band: _SingleBand,
    reference: _SingleBand,
    resampling: Resampling,
) -> tuple[np.ndarray, np.ndarray]:
    """Resample one band's data and mask onto the reference band's exact grid.

    Args:
        band: The coarser-resolution band to resample.
        reference: The finer-resolution band whose transform and shape
            define the target grid.
        resampling: Resampling method for the pixel data. The validity
            mask always uses nearest-neighbour regardless of this
            argument (see :func:`stack_sentinel2_bands`).

    Returns:
        A ``(data, valid_mask)`` pair, both matching ``reference``'s
        shape.
    """
    target_shape = reference.data.shape
    resampled_data = np.empty(target_shape, dtype=band.data.dtype)
    reproject(
        source=band.data,
        destination=resampled_data,
        src_transform=band.transform,
        src_crs=band.crs,
        dst_transform=reference.transform,
        dst_crs=reference.crs,
        resampling=resampling,
    )

    resampled_mask = np.zeros(target_shape, dtype=np.uint8)
    reproject(
        source=band.valid_mask.astype(np.uint8),
        destination=resampled_mask,
        src_transform=band.transform,
        src_crs=band.crs,
        dst_transform=reference.transform,
        dst_crs=reference.crs,
        resampling=Resampling.nearest,
    )

    return resampled_data, resampled_mask.astype(bool)
