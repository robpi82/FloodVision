"""Raster data loading for GeoTIFF files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio

from src.exceptions import ImageLoadError


@dataclass(frozen=True)
class GeoTiffRasterData:
    """Immutable raster payload loaded from a GeoTIFF."""

    path: Path
    data: np.ndarray
    valid_mask: np.ndarray
    nodata: float | None

    @property
    def band_count(self) -> int:
        return int(self.data.shape[0])

    @property
    def height(self) -> int:
        return int(self.data.shape[1])

    @property
    def width(self) -> int:
        return int(self.data.shape[2])


class GeoTiffRasterLoader:
    """Load GeoTIFF pixel data while preserving band-first layout."""

    def load(self, path: Path | str) -> GeoTiffRasterData:
        """Load raster pixels and a two-dimensional valid-data mask."""
        raster_path = Path(path)

        if not raster_path.is_file():
            raise ImageLoadError(raster_path, "file not found")

        try:
            with rasterio.open(raster_path) as dataset:
                data = dataset.read()
                valid_mask = dataset.dataset_mask() > 0
                nodata = dataset.nodata
        except Exception as error:
            raise ImageLoadError(raster_path, str(error)) from error

        return GeoTiffRasterData(
            path=raster_path,
            data=data,
            valid_mask=valid_mask,
            nodata=nodata,
        )
