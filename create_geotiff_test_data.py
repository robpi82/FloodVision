"""Generate synthetic before/after GeoTIFF test data for FloodVision.

This is a STANDALONE utility script. It lives outside the FloodVision
package (``src/``), imports nothing from it, and never touches any
FloodVision project file or data directory. It only uses NumPy and
Rasterio to write two small GeoTIFF rasters to a dedicated output folder:

    <output_dir>/before.tif
    <output_dir>/after.tif

Purpose
-------
Prepare controlled, spatially compatible GeoTIFF Before/After test data
for the next manual end-to-end test of FloodVision's GeoTIFF workflow
(GeoTiffLoader -> GeoTiffCompatibilityValidator -> BatchProcessor ->
HSV water detection -> change detection -> GUI).

Scene design
------------
Both rasters share identical width, height, CRS, affine transform,
pixel resolution and data type (3-band uint8 RGB), so they are
spatially compatible by construction. They depict a simple synthetic
landscape:

    * land            -- noisy green/brown base terrain
    * vegetation       -- darker green elliptical forest patches
    * an existing lake -- identical in both rasters (unchanged water)
    * a flooded area   -- present ONLY in after.tif (the "new water"
                          FloodVision's change detection is meant to find)

All three land-cover colours were deliberately chosen relative to
FloodVision's default HSV water-detection window
(H 85-135, S >= 40, V >= 40 on OpenCV's 0-179 hue scale, see
``config.yaml`` / ``src/config.py``):

    WATER_RGB      = (30, 65, 145)  -> H=110, S=202, V=145  (inside window)
    VEGETATION_RGB = (25, 90, 40)   -> H= 67, S=184, V= 90  (outside window)
    land (typical) = (100, 155, 80) -> H= 52, S=123, V=155  (outside window)

so the existing HSV water detector should classify the lake and flood
area as water while land and vegetation stay unclassified -- without
requiring any change to FloodVision itself.

Usage
-----
    python create_geotiff_test_data.py [output_dir]

``output_dir`` is optional and defaults to ``./geotiff_test_data``.
The script does not copy anything into FloodVision's ``data/before`` or
``data/after`` folders -- seeing the exact copy commands (with a
*shared* filename, which FloodVision's pairing requires) is left to the
user and printed at the end of the run.
"""

from __future__ import annotations

import argparse
import colorsys
import sys
from pathlib import Path
from typing import Final

import numpy as np
import rasterio
from numpy.typing import NDArray
from rasterio.transform import Affine, from_origin

# ---------------------------------------------------------------------------
# Raster geometry (identical for before.tif and after.tif by construction)
# ---------------------------------------------------------------------------
WIDTH: Final[int] = 512
HEIGHT: Final[int] = 512
BAND_COUNT: Final[int] = 3
DTYPE: Final[str] = "uint8"
NODATA: Final[float] = 0.0

CRS: Final[str] = "EPSG:32632"  # UTM zone 32N -- realistic for Central Europe
PIXEL_SIZE: Final[float] = 10.0  # metres per pixel (matches Sentinel-2 10 m bands)
# Upper-left corner: a real Sentinel-2 / Copernicus tile corner coordinate,
# reused here purely as a realistic, recognisable anchor point.
ORIGIN_X: Final[float] = 699_960.0
ORIGIN_Y: Final[float] = 5_300_040.0

TRANSFORM: Final[Affine] = from_origin(ORIGIN_X, ORIGIN_Y, PIXEL_SIZE, PIXEL_SIZE)

SEED: Final[int] = 42  # fixed seed -> identical output on every run

# ---------------------------------------------------------------------------
# Land-cover colours (RGB), tuned against FloodVision's default HSV window
# ---------------------------------------------------------------------------
WATER_RGB: Final[tuple[int, int, int]] = (30, 65, 145)
VEGETATION_RGB: Final[tuple[int, int, int]] = (25, 90, 40)
LAND_BASE_RGB: Final[tuple[int, int, int]] = (90, 140, 70)
LAND_NOISE_RANGE: Final[tuple[int, int, int]] = (25, 35, 20)  # per-channel jitter

# ---------------------------------------------------------------------------
# Scene geometry (fixed, not randomised, so the layout is easy to reason
# about and always identical between runs)
# ---------------------------------------------------------------------------
LAKE_CENTER: Final[tuple[int, int]] = (150, 150)  # (row, col)
LAKE_RADIUS: Final[tuple[int, int]] = (55, 50)  # (row radius, col radius)

FLOOD_CENTER: Final[tuple[int, int]] = (370, 340)  # (row, col)
FLOOD_RADIUS: Final[tuple[int, int]] = (85, 115)  # (row radius, col radius)

VEGETATION_PATCHES: Final[tuple[tuple[int, int, int, int], ...]] = (
    # (row, col, row_radius, col_radius)
    (80, 400, 45, 60),
    (420, 90, 50, 40),
    (250, 60, 35, 45),
    (60, 230, 30, 35),
    (330, 420, 40, 30),
)


def build_land_base(rng: np.random.Generator) -> NDArray[np.uint8]:
    """Create the noisy green/brown base terrain.

    Args:
        rng: Seeded random generator (for deterministic output).

    Returns:
        A ``(3, HEIGHT, WIDTH)`` uint8 array in band-first order, as
        expected by Rasterio's ``dataset.write``.
    """
    image = np.empty((BAND_COUNT, HEIGHT, WIDTH), dtype=np.uint8)
    for band in range(BAND_COUNT):
        base_value = LAND_BASE_RGB[band]
        jitter = LAND_NOISE_RANGE[band]
        noise = rng.integers(0, jitter + 1, size=(HEIGHT, WIDTH), dtype=np.uint8)
        image[band] = base_value + noise
    return image


def elliptical_mask(
    center: tuple[int, int], radius: tuple[int, int]
) -> NDArray[np.bool_]:
    """Build a boolean elliptical mask over the raster grid.

    Args:
        center: ``(row, col)`` of the ellipse centre.
        radius: ``(row_radius, col_radius)`` of the ellipse.

    Returns:
        A ``(HEIGHT, WIDTH)`` boolean array, ``True`` inside the ellipse.
    """
    rows, cols = np.mgrid[0:HEIGHT, 0:WIDTH]
    row_term = (rows - center[0]) / radius[0]
    col_term = (cols - center[1]) / radius[1]
    return (row_term**2 + col_term**2) <= 1.0


def paint(image: NDArray[np.uint8], mask: NDArray[np.bool_], color: tuple[int, int, int]) -> None:
    """Paint a solid colour into an image wherever ``mask`` is True.

    Args:
        image: ``(3, HEIGHT, WIDTH)`` uint8 array, modified in place.
        mask: ``(HEIGHT, WIDTH)`` boolean array selecting pixels to paint.
        color: RGB colour to apply.
    """
    for band in range(BAND_COUNT):
        image[band][mask] = color[band]


def build_before_scene(rng: np.random.Generator) -> NDArray[np.uint8]:
    """Compose the before-event scene: land, vegetation and the lake.

    Args:
        rng: Seeded random generator.

    Returns:
        The complete before-event raster array.
    """
    image = build_land_base(rng)
    for row, col, row_radius, col_radius in VEGETATION_PATCHES:
        paint(image, elliptical_mask((row, col), (row_radius, col_radius)), VEGETATION_RGB)
    paint(image, elliptical_mask(LAKE_CENTER, LAKE_RADIUS), WATER_RGB)
    return image


def build_after_scene(before: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """Derive the after-event scene by adding the flood on top of ``before``.

    Starting from an exact copy of the before scene (rather than
    rebuilding independently) guarantees that every difference between
    the two rasters is exactly the flood -- precisely what FloodVision's
    change detection (``NEW = AFTER AND NOT BEFORE``) is meant to find.

    Args:
        before: The already-built before-event raster.

    Returns:
        The after-event raster: identical to ``before`` plus the flood.
    """
    after = before.copy()
    paint(after, elliptical_mask(FLOOD_CENTER, FLOOD_RADIUS), WATER_RGB)
    return after


def write_geotiff(path: Path, image: NDArray[np.uint8]) -> None:
    """Write a raster array to disk as a georeferenced GeoTIFF.

    Args:
        path: Target file path.
        image: ``(3, HEIGHT, WIDTH)`` uint8 array to write.
    """
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=WIDTH,
        height=HEIGHT,
        count=BAND_COUNT,
        dtype=DTYPE,
        crs=CRS,
        transform=TRANSFORM,
        nodata=NODATA,
    ) as dataset:
        dataset.write(image)


def validate_pair_compatible(before_path: Path, after_path: Path) -> None:
    """Re-open both files and confirm they are spatially compatible.

    This is a deliberately self-contained check (it re-reads the files
    from disk with Rasterio directly, independent of anything this
    script just held in memory) covering exactly the properties that
    matter for pixel-by-pixel comparison: dimensions, CRS, transform,
    band count and data type.

    Args:
        before_path: Path to the generated before.tif.
        after_path: Path to the generated after.tif.

    Raises:
        AssertionError: If any spatial property differs between the
            two files.
    """
    with rasterio.open(before_path) as before_ds, rasterio.open(after_path) as after_ds:
        checks = {
            "width": (before_ds.width, after_ds.width),
            "height": (before_ds.height, after_ds.height),
            "CRS": (before_ds.crs, after_ds.crs),
            "transform": (before_ds.transform, after_ds.transform),
            "band count": (before_ds.count, after_ds.count),
            "dtype": (before_ds.dtypes, after_ds.dtypes),
        }
        mismatches = [name for name, (a, b) in checks.items() if a != b]

    if mismatches:
        raise AssertionError(
            f"before.tif and after.tif are NOT spatially compatible -- "
            f"mismatched propertie(s): {', '.join(mismatches)}"
        )
    print("Compatibility check: OK -- before.tif and after.tif are spatially compatible.")


def print_raster_info(label: str, path: Path) -> None:
    """Print key metadata of a raster file.

    Args:
        label: Short label for the printout (e.g. "BEFORE").
        path: Path to the raster file.
    """
    with rasterio.open(path) as dataset:
        print(f"[{label}] {path}")
        print(f"    dimensions : {dataset.width} x {dataset.height} px")
        print(f"    bands      : {dataset.count} ({', '.join(dataset.dtypes)})")
        print(f"    CRS        : {dataset.crs}")
        print(f"    transform  : {dataset.transform}")
        print(f"    bounds     : {dataset.bounds}")
        print(f"    pixel size : {abs(dataset.transform.a):g} x {abs(dataset.transform.e):g} m")
        print(f"    nodata     : {dataset.nodata}")


def print_color_reference() -> None:
    """Print the HSV values of the scene colours as a sanity check.

    Purely informational: confirms at run time (not just in the module
    docstring) that WATER/flood colours fall inside FloodVision's
    default HSV water window and land/vegetation stay outside it.
    """
    print("Land-cover colour reference (RGB -> OpenCV HSV, H in 0..179):")
    for name, rgb in (
        ("water / flood", WATER_RGB),
        ("vegetation", VEGETATION_RGB),
        ("land (base)", LAND_BASE_RGB),
    ):
        r, g, b = (channel / 255.0 for channel in rgb)
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        print(
            f"    {name:<14s} RGB={rgb}  ->  "
            f"H={round(h * 179):3d}  S={round(s * 255):3d}  V={round(v * 255):3d}"
        )
    print("    (FloodVision default water window: H 85-135, S >= 40, V >= 40)")


def parse_output_dir() -> Path:
    """Parse the optional output-directory command-line argument.

    Returns:
        The resolved output directory (created if necessary).
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_dir",
        nargs="?",
        default="geotiff_test_data",
        help="Directory to write before.tif / after.tif into "
        "(default: ./geotiff_test_data)",
    )
    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def main() -> int:
    """Generate, write, verify and report the before/after GeoTIFF pair."""
    output_dir = parse_output_dir()
    before_path = output_dir / "before.tif"
    after_path = output_dir / "after.tif"

    print("Generating synthetic FloodVision GeoTIFF test data...\n")
    print_color_reference()
    print()

    rng = np.random.default_rng(SEED)
    before_scene = build_before_scene(rng)
    after_scene = build_after_scene(before_scene)

    write_geotiff(before_path, before_scene)
    write_geotiff(after_path, after_scene)
    print(f"Wrote {before_path}")
    print(f"Wrote {after_path}\n")

    print_raster_info("BEFORE", before_path)
    print()
    print_raster_info("AFTER", after_path)
    print()

    validate_pair_compatible(before_path, after_path)

    flood_pixels = int(elliptical_mask(FLOOD_CENTER, FLOOD_RADIUS).sum())
    flood_percent = 100.0 * flood_pixels / (WIDTH * HEIGHT)
    print(
        f"\nSynthetic flood extent: {flood_pixels:,} px "
        f"({flood_percent:.1f} % of the raster) -- present only in after.tif."
    )

    print("\nTo use this pair with FloodVision's Before/After batch workflow,")
    print("copy both files under a SHARED filename into the app's data folders")
    print("(pairing is done by identical filename across before/ and after/):\n")
    print("    mkdir -p data/before data/after")
    print(f"    cp {before_path} data/before/flood_test_site.tif")
    print(f"    cp {after_path} data/after/flood_test_site.tif")
    return 0


if __name__ == "__main__":
    sys.exit(main())
