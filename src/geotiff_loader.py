"""GeoTIFF loading and metadata extraction using Rasterio.

Scope (v0.8 foundation step): this module only *opens* raster files
safely and extracts structured geospatial metadata. It deliberately does
**not** feed pixel data into the detection pipeline, validate image
pairs or write georeferenced outputs -- those are separate, later
development steps that will build on the metadata provided here.

Design notes:
    * ``read_metadata`` accepts any raster Rasterio can open (not only
      GTiff), which keeps the component reusable for future Sentinel-2
      or Landsat ingestion without changes.
    * "GeoTIFF" is defined here as a readable raster that actually
      carries georeferencing: a CRS and/or a non-identity affine
      transform. A plain TIFF is a valid raster but *not* a GeoTIFF;
      :meth:`GeoTiffLoader.is_geotiff` makes that distinction without
      raising, so callers can branch safely.
    * All Rasterio datasets are opened via context managers; every value
      stored in :class:`GeoTiffMetadata` is copied out of the dataset,
      so no handle outlives the ``with`` block.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import warnings
from collections.abc import Iterator
from contextlib import contextmanager

import rasterio
from affine import Affine
from rasterio.coords import BoundingBox
from rasterio.crs import CRS
from rasterio.errors import NotGeoreferencedWarning, RasterioError

from src.exceptions import ImageLoadError

logger = logging.getLogger(__name__)

#: File extensions the loader treats as GeoTIFF candidates.
GEOTIFF_EXTENSIONS: Final[frozenset[str]] = frozenset({".tif", ".tiff"})


@dataclass(frozen=True)
class GeoTiffMetadata:
    """Immutable, structured metadata of one raster file.

    Attributes:
        filename: Base name of the raster file.
        path: Full path to the raster file.
        width: Raster width in pixels.
        height: Raster height in pixels.
        band_count: Number of raster bands.
        dtypes: Data type per band (e.g. ``("uint8", "uint8", "uint8")``).
        driver: Rasterio/GDAL driver name (e.g. ``"GTiff"``).
        crs: Coordinate reference system, or ``None`` if the file
            carries no CRS definition.
        epsg: EPSG code of the CRS, or ``None`` when the CRS is missing
            or cannot be expressed as an EPSG code.
        bounds: Geographic extent as ``(left, bottom, right, top)`` in
            CRS units (pixel units for non-georeferenced rasters).
        pixel_size: Pixel resolution as ``(x_size, y_size)`` in CRS
            units, always positive.
        transform: Affine transform mapping pixel to CRS coordinates.
        nodata: NoData value, or ``None`` if not defined.
    """

    filename: str
    path: Path
    width: int
    height: int
    band_count: int
    dtypes: tuple[str, ...]
    driver: str
    crs: CRS | None
    epsg: int | None
    bounds: BoundingBox
    pixel_size: tuple[float, float]
    transform: Affine
    nodata: float | None

    @property
    def is_georeferenced(self) -> bool:
        """Whether the raster carries real geospatial referencing.

        A raster counts as georeferenced if it defines a CRS **or** a
        non-identity affine transform; plain TIFFs have neither.
        """
        return self.crs is not None or self.transform != Affine.identity()

    @property
    def crs_display(self) -> str:
        """Human-readable CRS representation (``"none"`` if absent).

        Prefers the compact authority string (e.g. ``"EPSG:32632"``) and
        falls back to WKT for exotic definitions.
        """
        if self.crs is None:
            return "none"
        try:
            return self.crs.to_string()
        except RasterioError:  # pragma: no cover -- defensive fallback
            return self.crs.wkt

    @classmethod
    def from_dataset(cls, dataset: rasterio.DatasetReader) -> "GeoTiffMetadata":
        """Build a metadata record from an open Rasterio dataset.

        Every value is copied out of the dataset so the record stays
        valid after the dataset is closed.

        Args:
            dataset: An open Rasterio dataset.

        Returns:
            The extracted metadata.
        """
        transform: Affine = dataset.transform
        return cls(
            filename=Path(dataset.name).name,
            path=Path(dataset.name),
            width=int(dataset.width),
            height=int(dataset.height),
            band_count=int(dataset.count),
            dtypes=tuple(dataset.dtypes),
            driver=str(dataset.driver),
            crs=dataset.crs,
            epsg=_safe_epsg(dataset.crs),
            bounds=dataset.bounds,
            pixel_size=(abs(transform.a), abs(transform.e)),
            transform=transform,
            nodata=dataset.nodata,
        )


class GeoTiffLoader:
    """Opens raster files safely and extracts geospatial metadata.

    Mirrors the role of :class:`~src.image_loader.ImageLoader` for the
    geospatial world: it knows how to read files and report problems via
    the project's exception hierarchy, and nothing else (Single
    Responsibility). Detection, pair validation and output writing are
    intentionally out of scope for this component.
    """

    def __init__(
        self,
        supported_extensions: frozenset[str] = GEOTIFF_EXTENSIONS,
    ) -> None:
        """Initialise the loader.

        Args:
            supported_extensions: Extensions considered GeoTIFF
                candidates by :meth:`is_geotiff` (injectable for tests
                and future formats, mirroring ``ImageLoader``).
        """
        self._supported_extensions = supported_extensions

    def is_geotiff(self, path: Path) -> bool:
        """Classify whether a file is a readable, georeferenced raster.

        This is a *predicate*, so it never raises: unreadable files,
        wrong extensions and plain (non-georeferenced) TIFFs all return
        ``False``. Use :meth:`read_metadata` when failure details are
        needed.

        Args:
            path: File to classify.

        Returns:
            ``True`` only for rasters that carry georeferencing.
        """
        if path.suffix.lower() not in self._supported_extensions:
            return False
        if not path.is_file():
            return False
        try:
            with _quiet_georeference_warning(), rasterio.open(path) as dataset:
                metadata = GeoTiffMetadata.from_dataset(dataset)
        except (RasterioError, ValueError, OSError):
            logger.debug("Not a readable raster: %s", path, exc_info=True)
            return False
        return metadata.is_georeferenced

    def read_metadata(self, path: Path) -> GeoTiffMetadata:
        """Open a raster file and extract its full metadata.

        The dataset is opened via a context manager and closed before
        this method returns; only plain values leave the ``with`` block.

        Args:
            path: Path to the raster file.

        Returns:
            The extracted :class:`GeoTiffMetadata`.

        Raises:
            ImageLoadError: If the file is missing, cannot be opened by
                Rasterio, or is not a valid raster.
        """
        logger.info("Reading raster metadata: %s", path.name)
        if not path.is_file():
            raise ImageLoadError(path, "file not found")
        try:
            with _quiet_georeference_warning(), rasterio.open(path) as dataset:
                metadata = GeoTiffMetadata.from_dataset(dataset)
        except (RasterioError, ValueError, OSError) as error:
            raise ImageLoadError(path, "file is not a readable raster") from error

        self._log_metadata(metadata)
        return metadata

    @staticmethod
    def _log_metadata(metadata: GeoTiffMetadata) -> None:
        """Log the essentials of a successfully read raster.

        Args:
            metadata: The metadata to summarise.
        """
        if metadata.is_georeferenced:
            logger.info(
                "GeoTIFF detected: %s | %d x %d px, %d band(s), %s | "
                "CRS %s | EPSG %s | pixel %.4g x %.4g | nodata %s",
                metadata.filename,
                metadata.width,
                metadata.height,
                metadata.band_count,
                "/".join(metadata.dtypes),
                metadata.crs_display,
                metadata.epsg if metadata.epsg is not None else "n/a",
                metadata.pixel_size[0],
                metadata.pixel_size[1],
                metadata.nodata,
            )
        else:
            logger.warning(
                "Raster without georeferencing (plain %s): %s | "
                "%d x %d px, %d band(s) -- CRS missing, identity transform",
                metadata.driver,
                metadata.filename,
                metadata.width,
                metadata.height,
                metadata.band_count,
            )


def _safe_epsg(crs: CRS | None) -> int | None:
    """Extract the EPSG code from a CRS without ever raising.

    Args:
        crs: The CRS to inspect, possibly ``None``.

    Returns:
        The EPSG code, or ``None`` for missing, exotic or invalid CRS
        definitions.
    """
    if crs is None:
        return None
    try:
        return crs.to_epsg()
    except RasterioError:
        logger.debug("CRS has no EPSG representation", exc_info=True)
        return None


@contextmanager
def _quiet_georeference_warning() -> Iterator[None]:
    """Silence Rasterio's ``NotGeoreferencedWarning`` for one ``open``.

    Plain TIFFs are an *expected* input here and handled explicitly (own
    warning log, ``is_georeferenced`` flag), so Rasterio's stderr warning
    would only duplicate noise. The filter is scoped to this context --
    a global warning filter would be rude to the rest of the application.

    Yields:
        Nothing; used purely for its warning-filter side effect.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        yield
