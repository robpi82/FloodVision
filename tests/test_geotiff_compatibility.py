"""Automated tests for :mod:`src.geotiff_compatibility`.

Test strategy: the validator is metadata-based, so the unit tests build
:class:`GeoTiffMetadata` instances directly via a small factory -- fast,
deterministic, and each spatial aspect can be varied *surgically* (one
field at a time, keeping derived fields fixed) so every check is tested
in isolation. Two integration tests additionally go through real tiny
synthetic GeoTIFF files and :class:`GeoTiffLoader`, proving the whole
metadata -> validation chain. The 12-line raster writer is duplicated
locally on purpose: importing helpers across test modules would require
turning ``tests/`` into a package or modifying ``conftest.py`` for a
single function -- isolation wins over DRY at this size.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine
from rasterio.coords import BoundingBox
from rasterio.crs import CRS
from rasterio.transform import from_origin

from src.geotiff_compatibility import (
    CompatibilityAspect,
    GeoTiffCompatibilityResult,
    GeoTiffCompatibilityValidator,
)
from src.geotiff_loader import GeoTiffLoader, GeoTiffMetadata

WIDTH = 64
HEIGHT = 48
ORIGIN_X = 699_960.0
ORIGIN_Y = 5_300_040.0
PIXEL = 10.0
UTM32 = "EPSG:32632"


def make_metadata(
    *,
    filename: str = "site.tif",
    width: int = WIDTH,
    height: int = HEIGHT,
    band_count: int = 3,
    dtypes: tuple[str, ...] | None = None,
    driver: str = "GTiff",
    crs: str | CRS | None = UTM32,
    origin: tuple[float, float] = (ORIGIN_X, ORIGIN_Y),
    pixel: tuple[float, float] = (PIXEL, PIXEL),
    nodata: float | None = 0.0,
    pixel_size: tuple[float, float] | None = None,
    bounds: BoundingBox | None = None,
    transform: Affine | None = None,
) -> GeoTiffMetadata:
    """Build consistent metadata, with surgical overrides for tests.

    Derived fields (bounds, transform, pixel_size, epsg) are computed
    from ``origin``/``pixel`` unless explicitly overridden -- overriding
    exactly one field lets a test trigger exactly one validator check.

    Args:
        filename: Base filename.
        width: Raster width in pixels.
        height: Raster height in pixels.
        band_count: Number of bands.
        dtypes: Per-band dtypes (defaults to uint8 per band).
        driver: Driver name.
        crs: CRS definition, or ``None`` for a non-georeferenced raster.
        origin: Upper-left corner in CRS units.
        pixel: Pixel size per axis in CRS units.
        nodata: NoData value.
        pixel_size: Surgical override for the stored pixel size.
        bounds: Surgical override for the stored bounds.
        transform: Surgical override for the stored transform.

    Returns:
        A fully populated :class:`GeoTiffMetadata`.
    """
    crs_object = (
        crs if isinstance(crs, CRS) or crs is None else CRS.from_user_input(crs)
    )
    derived_transform = from_origin(origin[0], origin[1], pixel[0], pixel[1])
    derived_bounds = BoundingBox(
        left=origin[0],
        bottom=origin[1] - height * pixel[1],
        right=origin[0] + width * pixel[0],
        top=origin[1],
    )
    return GeoTiffMetadata(
        filename=filename,
        path=Path("/synthetic") / filename,
        width=width,
        height=height,
        band_count=band_count,
        dtypes=dtypes if dtypes is not None else ("uint8",) * band_count,
        driver=driver,
        crs=crs_object,
        epsg=crs_object.to_epsg() if crs_object is not None else None,
        bounds=bounds if bounds is not None else derived_bounds,
        pixel_size=pixel_size if pixel_size is not None else pixel,
        transform=transform if transform is not None else derived_transform,
        nodata=nodata,
    )


def write_raster(path: Path, *, origin: tuple[float, float]) -> None:
    """Write a tiny real GeoTIFF for the integration tests.

    Args:
        path: Target file path.
        origin: Upper-left corner in EPSG:32632 coordinates.
    """
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=WIDTH,
        height=HEIGHT,
        count=3,
        dtype="uint8",
        crs=UTM32,
        transform=from_origin(origin[0], origin[1], PIXEL, PIXEL),
        nodata=0,
    ) as dataset:
        dataset.write(np.full((3, HEIGHT, WIDTH), 100, dtype=np.uint8))


@pytest.fixture
def validator() -> GeoTiffCompatibilityValidator:
    """A validator with default tolerances."""
    return GeoTiffCompatibilityValidator()


def assert_only_aspect_failed(
    result: GeoTiffCompatibilityResult, aspect: CompatibilityAspect
) -> None:
    """Assert that exactly one aspect failed and all others passed.

    Args:
        result: The validation result under test.
        aspect: The aspect expected to fail.
    """
    assert result.is_compatible is False
    assert result.failed_aspects == frozenset({aspect})
    for other in CompatibilityAspect:
        assert result.passed(other) is (other is not aspect)


# ---------------------------------------------------------------------------
# Fully compatible pairs (task 15)
# ---------------------------------------------------------------------------
class TestCompatiblePair:
    """Compatible pairs report no issues at all."""

    def test_fully_compatible_pair(
        self, validator: GeoTiffCompatibilityValidator
    ) -> None:
        """Identical spatial metadata is compatible on every aspect."""
        result = validator.validate(
            make_metadata(filename="before.tif"),
            make_metadata(filename="after.tif"),
        )
        assert result.is_compatible is True
        assert result.issues == ()
        assert result.failed_aspects == frozenset()
        assert all(result.passed(aspect) for aspect in CompatibilityAspect)
        assert result.summary() == "compatible"

    def test_integration_compatible_real_files(
        self, validator: GeoTiffCompatibilityValidator, tmp_path: Path
    ) -> None:
        """Loader metadata of two aligned real files validates as compatible."""
        loader = GeoTiffLoader()
        before, after = tmp_path / "before.tif", tmp_path / "after.tif"
        write_raster(before, origin=(ORIGIN_X, ORIGIN_Y))
        write_raster(after, origin=(ORIGIN_X, ORIGIN_Y))
        result = validator.validate(
            loader.read_metadata(before), loader.read_metadata(after)
        )
        assert result.is_compatible is True

    def test_integration_shifted_real_files(
        self, validator: GeoTiffCompatibilityValidator, tmp_path: Path
    ) -> None:
        """A really shifted raster fails on transform origin and bounds."""
        loader = GeoTiffLoader()
        before, after = tmp_path / "before.tif", tmp_path / "after.tif"
        write_raster(before, origin=(ORIGIN_X, ORIGIN_Y))
        write_raster(after, origin=(ORIGIN_X + 100.0, ORIGIN_Y))
        result = validator.validate(
            loader.read_metadata(before), loader.read_metadata(after)
        )
        assert result.is_compatible is False
        assert CompatibilityAspect.TRANSFORM in result.failed_aspects
        assert CompatibilityAspect.BOUNDS in result.failed_aspects


# ---------------------------------------------------------------------------
# CRS checks (tasks 16-17)
# ---------------------------------------------------------------------------
class TestCrsChecks:
    """CRS policy: equal passes, differing fails, mixed fails, none passes."""

    def test_different_crs_is_incompatible(
        self, validator: GeoTiffCompatibilityValidator
    ) -> None:
        """Two different CRS definitions fail the CRS check with names."""
        result = validator.validate(
            make_metadata(crs=UTM32), make_metadata(crs="EPSG:4326")
        )
        assert result.is_compatible is False
        assert CompatibilityAspect.CRS in result.failed_aspects
        crs_issue = next(
            issue for issue in result.issues if issue.aspect is CompatibilityAspect.CRS
        )
        assert "EPSG:32632" in crs_issue.description
        assert "EPSG:4326" in crs_issue.description

    def test_both_crs_missing_passes_with_warning(
        self,
        validator: GeoTiffCompatibilityValidator,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Two non-georeferenced rasters pass, but the gap is logged."""
        caplog.set_level(logging.WARNING, logger="src.geotiff_compatibility")
        result = validator.validate(make_metadata(crs=None), make_metadata(crs=None))
        assert result.is_compatible is True
        assert result.passed(CompatibilityAspect.CRS) is True
        assert any("CRS" in record.message for record in caplog.records)

    @pytest.mark.parametrize("missing_side", ["before", "after"])
    def test_mixed_crs_is_incompatible(
        self, validator: GeoTiffCompatibilityValidator, missing_side: str
    ) -> None:
        """A georeferenced/non-georeferenced mix fails and names the side."""
        before = make_metadata(crs=None if missing_side == "before" else UTM32)
        after = make_metadata(crs=None if missing_side == "after" else UTM32)
        result = validator.validate(before, after)
        assert_only_aspect_failed(result, CompatibilityAspect.CRS)
        assert missing_side in result.issues[0].description


# ---------------------------------------------------------------------------
# Dimension checks (tasks 18-20)
# ---------------------------------------------------------------------------
class TestDimensionChecks:
    """Width and height must match exactly."""

    def test_width_mismatch(self, validator: GeoTiffCompatibilityValidator) -> None:
        """A differing width fails the dimensions check."""
        before = make_metadata()
        after = make_metadata(
            width=WIDTH * 2, bounds=before.bounds, transform=before.transform
        )
        result = validator.validate(before, after)
        assert_only_aspect_failed(result, CompatibilityAspect.DIMENSIONS)
        assert "width" in result.issues[0].description

    def test_height_mismatch(self, validator: GeoTiffCompatibilityValidator) -> None:
        """A differing height fails the dimensions check."""
        before = make_metadata()
        after = make_metadata(
            height=HEIGHT + 8, bounds=before.bounds, transform=before.transform
        )
        result = validator.validate(before, after)
        assert_only_aspect_failed(result, CompatibilityAspect.DIMENSIONS)
        assert "height" in result.issues[0].description

    def test_width_and_height_mismatch(
        self, validator: GeoTiffCompatibilityValidator
    ) -> None:
        """Both dimensions differing yields one issue per dimension."""
        before = make_metadata()
        after = make_metadata(
            width=WIDTH * 2,
            height=HEIGHT + 8,
            bounds=before.bounds,
            transform=before.transform,
        )
        result = validator.validate(before, after)
        assert_only_aspect_failed(result, CompatibilityAspect.DIMENSIONS)
        descriptions = " | ".join(issue.description for issue in result.issues)
        assert "width" in descriptions
        assert "height" in descriptions
        assert len(result.issues) == 2


# ---------------------------------------------------------------------------
# Resolution checks (task 21)
# ---------------------------------------------------------------------------
class TestResolutionChecks:
    """Pixel size comparison uses the documented absolute tolerance."""

    def test_meaningful_resolution_difference(
        self, validator: GeoTiffCompatibilityValidator
    ) -> None:
        """10 m vs 10.5 m pixels fail on both axes."""
        before = make_metadata()
        after = make_metadata(pixel_size=(10.5, 10.5))
        result = validator.validate(before, after)
        assert_only_aspect_failed(result, CompatibilityAspect.RESOLUTION)
        assert len(result.issues) == 2  # x and y reported individually

    def test_float_noise_within_tolerance_is_compatible(
        self, validator: GeoTiffCompatibilityValidator
    ) -> None:
        """Differences far below the tolerance never cause a failure."""
        before = make_metadata()
        after = make_metadata(pixel_size=(PIXEL + 1e-9, PIXEL - 1e-9))
        assert validator.validate(before, after).is_compatible is True


# ---------------------------------------------------------------------------
# Bounds checks (task 22)
# ---------------------------------------------------------------------------
class TestBoundsChecks:
    """Extent comparison names the differing edges, with tolerance."""

    def test_meaningful_bounds_difference(
        self, validator: GeoTiffCompatibilityValidator
    ) -> None:
        """A 100 m eastward shift is reported on the left and right edges."""
        before = make_metadata()
        shifted = BoundingBox(
            left=before.bounds.left + 100.0,
            bottom=before.bounds.bottom,
            right=before.bounds.right + 100.0,
            top=before.bounds.top,
        )
        after = make_metadata(bounds=shifted)
        result = validator.validate(before, after)
        assert_only_aspect_failed(result, CompatibilityAspect.BOUNDS)
        assert "left" in result.issues[0].description
        assert "right" in result.issues[0].description

    def test_bounds_float_noise_is_compatible(
        self, validator: GeoTiffCompatibilityValidator
    ) -> None:
        """Nanometre-scale bound differences stay within tolerance."""
        before = make_metadata()
        noisy = BoundingBox(
            left=before.bounds.left + 1e-9,
            bottom=before.bounds.bottom - 1e-9,
            right=before.bounds.right + 1e-9,
            top=before.bounds.top - 1e-9,
        )
        after = make_metadata(bounds=noisy)
        assert validator.validate(before, after).is_compatible is True


# ---------------------------------------------------------------------------
# Transform checks (task 23)
# ---------------------------------------------------------------------------
class TestTransformChecks:
    """Origin and rotation/shear are validated; scale belongs elsewhere."""

    def test_origin_difference(self, validator: GeoTiffCompatibilityValidator) -> None:
        """A shifted transform origin fails with an 'origin' issue."""
        before = make_metadata()
        after = make_metadata(
            transform=from_origin(ORIGIN_X + 100.0, ORIGIN_Y, PIXEL, PIXEL),
            bounds=before.bounds,
        )
        result = validator.validate(before, after)
        assert_only_aspect_failed(result, CompatibilityAspect.TRANSFORM)
        assert "origin" in result.issues[0].description

    def test_rotation_shear_difference(
        self, validator: GeoTiffCompatibilityValidator
    ) -> None:
        """Non-zero shear coefficients fail with a 'rotation/shear' issue."""
        before = make_metadata()
        sheared = Affine(PIXEL, 0.5, ORIGIN_X, 0.3, -PIXEL, ORIGIN_Y)
        after = make_metadata(transform=sheared, bounds=before.bounds)
        result = validator.validate(before, after)
        assert_only_aspect_failed(result, CompatibilityAspect.TRANSFORM)
        assert "rotation/shear" in result.issues[0].description

    def test_origin_float_noise_is_compatible(
        self, validator: GeoTiffCompatibilityValidator
    ) -> None:
        """Nanometre origin noise stays within the coordinate tolerance."""
        before = make_metadata()
        after = make_metadata(
            transform=from_origin(ORIGIN_X + 1e-9, ORIGIN_Y - 1e-9, PIXEL, PIXEL),
            bounds=before.bounds,
        )
        assert validator.validate(before, after).is_compatible is True


# ---------------------------------------------------------------------------
# Multiple simultaneous mismatches (task 24)
# ---------------------------------------------------------------------------
class TestMultipleMismatches:
    """The validator reports every mismatch instead of stopping early."""

    def test_all_aspects_reported_at_once(
        self, validator: GeoTiffCompatibilityValidator
    ) -> None:
        """A completely different raster fails on all five aspects."""
        before = make_metadata()
        after = make_metadata(
            crs="EPSG:4326",
            width=128,
            height=100,
            origin=(11.0, 48.0),
            pixel=(30.0, 30.0),
        )
        result = validator.validate(before, after)
        assert result.is_compatible is False
        assert result.failed_aspects == frozenset(CompatibilityAspect)
        assert len(result.issues) >= 5
        assert ";" in result.summary()


# ---------------------------------------------------------------------------
# Non-spatial metadata (task 25)
# ---------------------------------------------------------------------------
class TestNonSpatialSemantics:
    """Documented semantics: non-spatial fields never affect compatibility."""

    def test_non_spatial_differences_are_compatible(
        self, validator: GeoTiffCompatibilityValidator
    ) -> None:
        """dtype, NoData, band count, name, path and driver are ignored."""
        before = make_metadata()
        after = make_metadata(
            filename="other_name.tiff",
            band_count=1,
            dtypes=("uint16",),
            nodata=None,
            driver="COG",
        )
        result = validator.validate(before, after)
        assert result.is_compatible is True
        assert result.issues == ()


# ---------------------------------------------------------------------------
# Programmer misuse (task 12)
# ---------------------------------------------------------------------------
class TestValidatorMisuse:
    """Invalid inputs raise immediately instead of producing results."""

    def test_non_metadata_argument_raises_type_error(
        self, validator: GeoTiffCompatibilityValidator
    ) -> None:
        """Passing anything but GeoTiffMetadata is programmer misuse."""
        with pytest.raises(TypeError):
            validator.validate("not metadata", make_metadata())  # type: ignore[arg-type]

    @pytest.mark.parametrize("tolerance", [0.0, -1.0])
    def test_non_positive_tolerance_raises_value_error(self, tolerance: float) -> None:
        """Zero or negative tolerances are rejected fail-fast."""
        with pytest.raises(ValueError):
            GeoTiffCompatibilityValidator(coordinate_tolerance=tolerance)
