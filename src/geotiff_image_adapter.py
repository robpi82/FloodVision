"""Convert GeoTIFF raster data to Pillow RGB images."""

from __future__ import annotations

import numpy as np
from PIL import Image

from src.geotiff_raster_loader import GeoTiffRasterData


class GeoTiffImageAdapter:
    """Convert GeoTIFF raster data to RGB images."""

    def to_image(
        self,
        raster: GeoTiffRasterData,
        bands: tuple[int, int, int] | None = None,
    ) -> Image.Image:
        """Convert raster data to an RGB image.

        Optionally select three raster bands in the requested RGB order.
        Band indices are zero-based.
        """
        data = raster.data

        if bands is None:
            if raster.band_count != 3:
                raise ValueError(
                    "GeoTIFF RGB conversion requires exactly 3 bands, "
                    f"got {raster.band_count}."
                )
        else:
            if len(bands) != 3:
                raise ValueError(
                    "GeoTIFF RGB conversion requires exactly 3 bands."
                )

            if any(band < 0 or band >= raster.band_count for band in bands):
                raise ValueError(
                    "Selected GeoTIFF band index is out of range."
                )

            data = raster.data[list(bands)]

        rgb = np.moveaxis(data, 0, -1)

        if rgb.dtype == np.uint8:
            result = rgb.copy()
        else:
            values = rgb[raster.valid_mask]

            if values.size == 0:
                result = np.zeros(rgb.shape, dtype=np.uint8)
            else:
                lo = float(np.min(values))
                hi = float(np.max(values))

                if not np.isfinite(lo) or not np.isfinite(hi):
                    raise ValueError(
                        "Raster contains non-finite valid pixel values."
                    )

                if hi == lo:
                    result = np.zeros(rgb.shape, dtype=np.uint8)
                    result[raster.valid_mask] = np.uint8(
                        np.clip(lo, 0, 255)
                    )
                else:
                    result = np.clip(
                        (rgb.astype(float) - lo) / (hi - lo) * 255,
                        0,
                        255,
                    ).astype(np.uint8)

        result[~raster.valid_mask] = 0

        return Image.fromarray(result, mode="RGB")