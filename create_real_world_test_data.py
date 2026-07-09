from pathlib import Path
import cv2
import numpy as np
import rasterio
from rasterio.windows import Window

SOURCE = Path(
    r"C:\Users\rob19\Desktop\FloodVision_Test_Image\NE2_50M_SR_W\NE2_50M_SR_W\NE2_50M_SR_W.tif"
)

OUTPUT = Path("real_world_test")
OUTPUT.mkdir(exist_ok=True)

WINDOW = Window(4200, 1800, 1024, 1024)

with rasterio.open(SOURCE) as src:

    before = src.read(window=WINDOW)

    transform = src.window_transform(WINDOW)

    profile = src.profile.copy()

    profile.update(
        width=1024,
        height=1024,
        transform=transform,
    )

before_path = OUTPUT / "real_before.tif"

with rasterio.open(before_path, "w", **profile) as dst:
    dst.write(before)

after = before.copy()


# Raster (Band, Zeile, Spalte) -> RGB
rgb = np.moveaxis(before, 0, -1)

# In HSV umwandeln
hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

# Dieselben Grenzwerte wie FloodVision
lower = np.array([85, 40, 40], dtype=np.uint8)
upper = np.array([135, 255, 255], dtype=np.uint8)

water_mask = cv2.inRange(hsv, lower, upper) > 0
land_mask = ~water_mask

ys, xs = np.where(land_mask)

if len(xs) == 0:
    raise RuntimeError("No land pixels found.")

center = len(xs) // 2

cx = int(xs[center])
cy = int(ys[center])

yy, xx = np.ogrid[:1024, :1024]

radius = 80

new_lake = (
    ((xx - cx) ** 2 + (yy - cy) ** 2 <= radius**2)
    & land_mask
)

water = np.array([30, 65, 145], dtype=np.uint8)

for band in range(3):
    after[band][new_lake] = water[band]

print(f"Artificial lake inserted at ({cx}, {cy})")
print(f"Pixels converted to water: {new_lake.sum()}")

after_path = OUTPUT / "real_after.tif"

with rasterio.open(after_path, "w", **profile) as dst:
    dst.write(after)

print()
print("Created:")
print(before_path)
print(after_path)