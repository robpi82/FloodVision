from pathlib import Path
import numpy as np
import pytest
from src.geotiff_image_adapter import GeoTiffImageAdapter
from src.geotiff_raster_loader import GeoTiffRasterData


def make(data, mask=None):
    mask = np.ones(data.shape[1:], dtype=bool) if mask is None else mask
    return GeoTiffRasterData(Path("test.tif"), data, mask, None)


def test_uint8_rgb():
    data = np.arange(24, dtype=np.uint8).reshape(3, 2, 4)
    image = GeoTiffImageAdapter().to_image(make(data))
    assert image.mode == "RGB" and image.size == (4, 2)
    np.testing.assert_array_equal(np.asarray(image), np.moveaxis(data, 0, -1))


def test_nodata_black():
    data = np.full((3, 2, 2), 100, dtype=np.uint8)
    mask = np.array([[False, True], [True, True]])
    pixels = np.asarray(GeoTiffImageAdapter().to_image(make(data, mask)))
    np.testing.assert_array_equal(pixels[0, 0], [0, 0, 0])


@pytest.mark.parametrize("bands", [1, 2, 4])
def test_bad_band_count(bands):
    with pytest.raises(ValueError, match="exactly 3 bands"):
        GeoTiffImageAdapter().to_image(make(np.zeros((bands, 2, 2), dtype=np.uint8)))


def test_uint16_scaled():
    data = np.arange(12, dtype=np.uint16).reshape(3, 2, 2) * 1000
    pixels = np.asarray(GeoTiffImageAdapter().to_image(make(data)))
    assert pixels.dtype == np.uint8 and pixels.min() == 0 and pixels.max() == 255


def test_invalid_ignored_during_scaling():
    data = np.array([[[65000, 10], [20, 30]]] * 3, dtype=np.uint16)
    mask = np.array([[False, True], [True, True]])
    pixels = np.asarray(GeoTiffImageAdapter().to_image(make(data, mask)))
    np.testing.assert_array_equal(pixels[0, 0], [0, 0, 0])
    np.testing.assert_array_equal(pixels[1, 1], [255, 255, 255])


def test_all_invalid_black():
    data = np.full((3, 2, 2), 1000, dtype=np.uint16)
    mask = np.zeros((2, 2), dtype=bool)
    assert not np.asarray(GeoTiffImageAdapter().to_image(make(data, mask))).any()


def test_non_finite_rejected():
    data = np.ones((3, 2, 2), dtype=np.float32)
    data[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        GeoTiffImageAdapter().to_image(make(data))

def test_selected_bands_are_converted_to_rgb():
    data = np.zeros((4, 2, 2), dtype=np.uint8)
    data[0] = 10
    data[1] = 20
    data[2] = 30
    data[3] = 40

    image = GeoTiffImageAdapter().to_image(
        make(data),
        bands=(3, 2, 1),
    )

    pixels = np.asarray(image)

    np.testing.assert_array_equal(pixels[0, 0], [40, 30, 20])


def test_band_selection_preserves_requested_order():
    data = np.zeros((4, 2, 2), dtype=np.uint8)
    data[0] = 10
    data[1] = 20
    data[2] = 30
    data[3] = 40

    image = GeoTiffImageAdapter().to_image(
        make(data),
        bands=(0, 2, 3),
    )

    pixels = np.asarray(image)

    np.testing.assert_array_equal(pixels[0, 0], [10, 30, 40])


def test_band_selection_requires_exactly_three_bands():
    data = np.zeros((4, 2, 2), dtype=np.uint8)

    with pytest.raises(ValueError, match="exactly 3 bands"):
        GeoTiffImageAdapter().to_image(
            make(data),
            bands=(0, 1),
        )


def test_band_selection_rejects_out_of_range_band():
    data = np.zeros((4, 2, 2), dtype=np.uint8)

    with pytest.raises(ValueError, match="out of range"):
        GeoTiffImageAdapter().to_image(
            make(data),
            bands=(0, 1, 4),
        )