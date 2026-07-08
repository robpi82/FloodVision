import numpy as np
from PIL import Image
from src.geotiff_raster_loader import GeoTiffRasterData

class GeoTiffImageAdapter:
    def to_image(self, raster: GeoTiffRasterData) -> Image.Image:
        if raster.band_count != 3:
            raise ValueError(f"GeoTIFF RGB conversion requires exactly 3 bands, got {raster.band_count}.")
        rgb = np.moveaxis(raster.data, 0, -1)
        if rgb.dtype == np.uint8:
            result = rgb.copy()
        else:
            values = rgb[raster.valid_mask]
            if values.size == 0:
                result = np.zeros(rgb.shape, dtype=np.uint8)
            else:
                lo, hi = float(np.min(values)), float(np.max(values))
                if not np.isfinite(lo) or not np.isfinite(hi):
                    raise ValueError("Raster contains non-finite valid pixel values.")
                if hi == lo:
                    result = np.zeros(rgb.shape, dtype=np.uint8)
                    result[raster.valid_mask] = np.uint8(np.clip(lo, 0, 255))
                else:
                    result = np.clip((rgb.astype(float)-lo)/(hi-lo)*255, 0, 255).astype(np.uint8)
        result[~raster.valid_mask] = 0
        return Image.fromarray(result, mode="RGB")
