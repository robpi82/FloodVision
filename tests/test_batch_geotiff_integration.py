"""Integration tests: GeoTIFF gate inside the batch workflow.

Focus: the *integration boundary* in :class:`BatchProcessor` -- file
classification, routing, rejection and batch continuation. The
individual comparison rules are exhaustively covered by
``test_geotiff_compatibility.py`` and are not re-tested here.

Strategy: real tiny synthetic files (Pillow for images, Rasterio for
GeoTIFFs) run through the *real* pipeline with the real
``HSVWaterDetector`` -- no mocking of processing. The single test double
is ``ForbiddenValidator``, injected via the processor's DI seam to
*prove* that non-GeoTIFF pairs never reach compatibility validation.

Documented capability: compatible GeoTIFF pairs are processed by the
existing Pillow/OpenCV pixel pipeline like ordinary images for
detection; since v0.8's export step, the resulting flood mask is
additionally written as a georeferenced ``new_flood_mask.tif`` (see
``tests/test_geotiff_export.py`` for exhaustive coverage of that
export itself -- this file only asserts it is correctly *triggered*
here).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from PIL import Image
from rasterio.transform import from_origin

from src.batch_processor import BatchProcessor, BatchResult, ProcessingStatus
from src.geotiff_compatibility import GeoTiffCompatibilityValidator
from src.geotiff_loader import GeoTiffMetadata
from src.image_loader import ImageLoader
from src.water_detection import HSVWaterDetector

WIDTH = 64
HEIGHT = 48
PIXEL = 10.0
ORIGIN = (699_960.0, 5_300_040.0)
UTM32 = "EPSG:32632"
WATER_RGB = (30, 65, 145)  # falls into the configured HSV water window
LAND_RGB = (80, 150, 70)


def write_image(path: Path, *, water: bool) -> None:
    """Write a plain raster image (PNG/JPG/TIFF chosen by suffix).

    Args:
        path: Target file; the suffix selects the Pillow format.
        water: Whether to paint a detectable water block.
    """
    array = np.full((HEIGHT, WIDTH, 3), LAND_RGB, dtype=np.uint8)
    if water:
        array[10:38, 20:50] = WATER_RGB
    Image.fromarray(array).save(path)


def write_geotiff(
    path: Path,
    *,
    water: bool,
    crs: str = UTM32,
    origin: tuple[float, float] = ORIGIN,
    width: int = WIDTH,
) -> None:
    """Write a small georeferenced uint8 RGB GeoTIFF.

    Args:
        path: Target file path.
        water: Whether to paint a detectable water block.
        crs: CRS definition.
        origin: Upper-left corner in CRS units.
        width: Raster width (variation triggers dimension rejection).
    """
    array = np.full((HEIGHT, width, 3), LAND_RGB, dtype=np.uint8)
    if water:
        array[10:38, 20 : min(50, width)] = WATER_RGB
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=HEIGHT,
        count=3,
        dtype="uint8",
        crs=crs,
        transform=from_origin(origin[0], origin[1], PIXEL, PIXEL),
    ) as dataset:
        dataset.write(array.transpose(2, 0, 1))


class ForbiddenValidator(GeoTiffCompatibilityValidator):
    """Test double proving that validation is *not* reached.

    Injected for pairs that must bypass the geospatial gate (normal
    images, plain TIFFs); any call is an integration-routing bug.
    """

    def validate(self, before: GeoTiffMetadata, after: GeoTiffMetadata):  # noqa: D102
        raise AssertionError(
            "Compatibility validation must not run for non-GeoTIFF pairs"
        )


def run_batch(
    tmp_path: Path,
    validator: GeoTiffCompatibilityValidator | None = None,
) -> tuple[BatchResult, Path]:
    """Run a real batch over ``tmp_path``'s before/after directories.

    Args:
        tmp_path: Base directory containing ``before/`` and ``after/``.
        validator: Optional validator override (DI seam).

    Returns:
        The batch result and the output directory.
    """
    output_dir = tmp_path / "output"
    processor = BatchProcessor(
        loader=ImageLoader(),
        detector=HSVWaterDetector(),
        before_dir=tmp_path / "before",
        after_dir=tmp_path / "after",
        output_dir=output_dir,
        compatibility_validator=validator,
    )
    return processor.run(), output_dir


@pytest.fixture
def pair_dirs(tmp_path: Path) -> Path:
    """Create empty before/after directories under ``tmp_path``."""
    (tmp_path / "before").mkdir()
    (tmp_path / "after").mkdir()
    return tmp_path


def record_by_name(result: BatchResult, filename: str):
    """Fetch the record of one pair by filename.

    Args:
        result: Batch result to search.
        filename: Pair filename.

    Returns:
        The matching record.
    """
    return next(r for r in result.records if r.filename == filename)


# ---------------------------------------------------------------------------
# Existing workflow protection (task 12)
# ---------------------------------------------------------------------------
class TestNormalImagePairs:
    """PNG/JPG pairs keep the pre-v0.8 behaviour, untouched by the gate."""

    def test_png_pair_processes_and_never_touches_validation(
        self, pair_dirs: Path
    ) -> None:
        """A PNG pair succeeds; the injected validator proves no geo call."""
        write_image(pair_dirs / "before" / "site.png", water=False)
        write_image(pair_dirs / "after" / "site.png", water=True)
        result, output_dir = run_batch(pair_dirs, validator=ForbiddenValidator())

        record = record_by_name(result, "site.png")
        assert record.status is ProcessingStatus.SUCCESS
        assert record.new_flood_pixels and record.new_flood_pixels > 0
        assert (output_dir / "site" / "overlay.png").is_file()

    def test_plain_tiff_pair_uses_existing_workflow(self, pair_dirs: Path) -> None:
        """Plain TIFFs are *not* GeoTIFFs: normal pipeline, no validation."""
        write_image(pair_dirs / "before" / "site.tif", water=False)
        write_image(pair_dirs / "after" / "site.tif", water=True)
        result, output_dir = run_batch(pair_dirs, validator=ForbiddenValidator())

        record = record_by_name(result, "site.tif")
        assert record.status is ProcessingStatus.SUCCESS
        assert (output_dir / "site" / "new_flood_mask.png").is_file()


# ---------------------------------------------------------------------------
# Compatible GeoTIFF pair (task 13)
# ---------------------------------------------------------------------------
class TestCompatibleGeoTiffPair:
    """Aligned GeoTIFF pairs pass the gate into the existing pipeline."""

    def test_compatible_pair_is_validated_and_processed(
        self, pair_dirs: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Gate runs, pair proceeds, a georeferenced flood mask is written."""
        caplog.set_level("INFO")
        write_geotiff(pair_dirs / "before" / "flood.tif", water=False)
        write_geotiff(pair_dirs / "after" / "flood.tif", water=True)
        result, output_dir = run_batch(pair_dirs)

        record = record_by_name(result, "flood.tif")
        assert record.status is ProcessingStatus.SUCCESS
        assert record.error_message is None
        assert record.new_flood_pixels and record.new_flood_pixels > 0
        assert any("GeoTIFF pair detected" in r.message for r in caplog.records)
        # Since v0.8's export step: PNG products are unchanged, and the
        # flood mask is additionally written as a georeferenced GeoTIFF.
        products = output_dir / "flood"
        assert (products / "overlay.png").is_file()
        geo_output = products / "new_flood_mask.tif"
        assert geo_output.is_file()
        with rasterio.open(geo_output) as dataset:
            assert dataset.crs == UTM32
            assert (dataset.width, dataset.height) == (WIDTH, HEIGHT)


# ---------------------------------------------------------------------------
# Incompatible GeoTIFF pairs (tasks 14-16)
# ---------------------------------------------------------------------------
class TestIncompatibleGeoTiffPairs:
    """Spatially incompatible pairs fail as records, before detection."""

    def test_crs_mismatch_is_rejected_before_detection(self, pair_dirs: Path) -> None:
        """Different CRS -> failed record naming CRS, no products written."""
        write_geotiff(pair_dirs / "before" / "site.tif", water=False)
        write_geotiff(pair_dirs / "after" / "site.tif", water=True, crs="EPSG:4326")
        result, output_dir = run_batch(pair_dirs)

        record = record_by_name(result, "site.tif")
        assert record.status is ProcessingStatus.FAILED
        assert record.error_message is not None
        assert "CRS" in record.error_message
        assert record.water_after_percent is None
        assert not (output_dir / "site").exists()  # stopped pre-pipeline

    def test_dimension_mismatch_is_rejected(self, pair_dirs: Path) -> None:
        """Different widths -> failed record naming the width mismatch."""
        write_geotiff(pair_dirs / "before" / "site.tif", water=False)
        write_geotiff(pair_dirs / "after" / "site.tif", water=True, width=128)
        result, output_dir = run_batch(pair_dirs)

        record = record_by_name(result, "site.tif")
        assert record.status is ProcessingStatus.FAILED
        assert "width" in (record.error_message or "")
        assert not (output_dir / "site").exists()

    def test_shifted_origin_is_rejected(self, pair_dirs: Path) -> None:
        """A shifted raster origin -> failed record naming the origin."""
        write_geotiff(pair_dirs / "before" / "site.tif", water=False)
        write_geotiff(
            pair_dirs / "after" / "site.tif",
            water=True,
            origin=(ORIGIN[0] + 100.0, ORIGIN[1]),
        )
        result, _ = run_batch(pair_dirs)

        record = record_by_name(result, "site.tif")
        assert record.status is ProcessingStatus.FAILED
        assert "origin" in (record.error_message or "")


# ---------------------------------------------------------------------------
# Mixed pairs (task 17)
# ---------------------------------------------------------------------------
class TestMixedPairs:
    """Exactly one georeferenced file -> safe rejection, batch continues."""

    @pytest.mark.parametrize("geo_side", ["before", "after"])
    def test_mixed_pair_is_rejected_with_reason(
        self, pair_dirs: Path, geo_side: str
    ) -> None:
        """PNG+GeoTIFF in either order fails with a 'mixed' reason."""
        # A shared filename is required for pairing; .tif on both sides,
        # but only one side carries georeferencing.
        if geo_side == "before":
            write_geotiff(pair_dirs / "before" / "site.tif", water=False)
            write_image(pair_dirs / "after" / "site.tif", water=True)
            non_geo_side = "after"
        else:
            write_image(pair_dirs / "before" / "site.tif", water=False)
            write_geotiff(pair_dirs / "after" / "site.tif", water=True)
            non_geo_side = "before"
        result, output_dir = run_batch(pair_dirs)

        record = record_by_name(result, "site.tif")
        assert record.status is ProcessingStatus.FAILED
        assert "mixed georeferencing" in (record.error_message or "")
        assert non_geo_side in (record.error_message or "")
        assert not (output_dir / "site").exists()


# ---------------------------------------------------------------------------
# Corrupted files + batch continuation (tasks 18-19)
# ---------------------------------------------------------------------------
class TestCorruptionAndContinuation:
    """One bad pair never kills the batch -- the critical integration test."""

    def test_batch_continues_after_corrupt_and_incompatible_pairs(
        self, pair_dirs: Path
    ) -> None:
        """Corrupt pair fails, incompatible pair fails, valid pair succeeds."""
        # Pair 1: corrupted TIFF (classified non-geo, fails in PIL load).
        (pair_dirs / "before" / "a_corrupt.tif").write_bytes(b"NOT A RASTER")
        write_image(pair_dirs / "after" / "a_corrupt.tif", water=True)
        # Pair 2: incompatible GeoTIFF pair (CRS mismatch).
        write_geotiff(pair_dirs / "before" / "b_geo.tif", water=False)
        write_geotiff(pair_dirs / "after" / "b_geo.tif", water=True, crs="EPSG:4326")
        # Pair 3: perfectly valid PNG pair.
        write_image(pair_dirs / "before" / "c_ok.png", water=False)
        write_image(pair_dirs / "after" / "c_ok.png", water=True)

        result, output_dir = run_batch(pair_dirs)

        assert len(result.records) == 3
        assert len(result.failed) == 2
        assert len(result.successful) == 1

        corrupt = record_by_name(result, "a_corrupt.tif")
        assert corrupt.status is ProcessingStatus.FAILED
        assert corrupt.error_message is not None

        incompatible = record_by_name(result, "b_geo.tif")
        assert incompatible.status is ProcessingStatus.FAILED
        assert "CRS" in (incompatible.error_message or "")

        ok = record_by_name(result, "c_ok.png")
        assert ok.status is ProcessingStatus.SUCCESS
        assert (output_dir / "c_ok" / "comparison.png").is_file()