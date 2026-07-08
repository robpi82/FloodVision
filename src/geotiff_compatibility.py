"""GeoTIFF pair compatibility validation (metadata-based).

Determines whether two rasters are spatially compatible for **direct
pixel-by-pixel comparison** -- the precondition of FloodVision's change
detection. The validator works exclusively on
:class:`~src.geotiff_loader.GeoTiffMetadata`; it never opens raster
files itself (loading stays the loader's responsibility).

Compatibility semantics:
    *Spatial* fields decide compatibility -- CRS, width, height, pixel
    resolution, bounds and the non-scale parts of the affine transform
    (origin, rotation/shear). *Non-spatial* fields never do: differing
    data types, NoData values, band counts, filenames, paths or drivers
    do not affect whether pixel ``(row, col)`` covers the same ground in
    both rasters, so they are deliberately ignored here.

CRS policy (explicit by design):
    * both CRS present and equal -> compatible (Rasterio ``CRS.__eq__``
      compares definitions robustly across representations, so an EPSG
      code and an equivalent PROJ string match -- EPSG-only comparison
      would reject valid pairs).
    * both CRS missing -> the CRS check *passes* with a logged warning:
      two non-georeferenced rasters can still be exactly pixel-aligned,
      matching FloodVision's existing plain-image workflow. What cannot
      be asserted is *where* on Earth they are -- hence the warning.
    * exactly one CRS missing -> incompatible: alignment between a
      georeferenced and a non-georeferenced raster cannot be verified.

Tolerance strategy:
    Geospatial floats accumulate rounding noise (GDAL round-trips,
    projection arithmetic), so coordinate-like values (bounds, origin,
    shear) and pixel resolutions are compared with an **absolute**
    tolerance in CRS units, defaulting to ``1e-6`` -- one micrometre in
    metric systems, far below any real spatial difference yet far above
    float noise. Both tolerances are injectable per validator instance
    and validated fail-fast. Scale coefficients of the transform are
    covered by the resolution check and excluded from the transform
    check, so one physical mismatch is never reported twice.

An incompatible result means the pair would need a future reprojection,
resampling or alignment step (deliberately out of scope here); this
module only *classifies*.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from src.geotiff_loader import GeoTiffMetadata

logger = logging.getLogger(__name__)

#: Absolute tolerance for coordinate-like values (bounds, origin, shear)
#: in CRS units. One micrometre for metric CRS -- pure float-noise guard.
DEFAULT_COORDINATE_TOLERANCE: Final[float] = 1e-6

#: Absolute tolerance for pixel-resolution comparison in CRS units.
DEFAULT_RESOLUTION_TOLERANCE: Final[float] = 1e-6


class CompatibilityAspect(StrEnum):
    """The spatial aspects evaluated for pair compatibility.

    A :class:`enum.StrEnum` keeps the set of aspects closed and
    typo-proof while serialising naturally for logs and future reports
    (mirroring :class:`~src.batch_processor.ProcessingStatus`).
    """

    CRS = "crs"
    DIMENSIONS = "dimensions"
    RESOLUTION = "resolution"
    BOUNDS = "bounds"
    TRANSFORM = "transform"


@dataclass(frozen=True)
class CompatibilityIssue:
    """One detected incompatibility.

    Attributes:
        aspect: The spatial aspect that failed.
        description: Human-readable explanation naming both values.
    """

    aspect: CompatibilityAspect
    description: str


@dataclass(frozen=True)
class GeoTiffCompatibilityResult:
    """Immutable outcome of validating one raster pair.

    The result stores only the detected issues; everything else --
    overall verdict, per-aspect verdicts, summary text -- is derived,
    so the data model cannot become self-contradictory.
    """

    issues: tuple[CompatibilityIssue, ...]

    @property
    def is_compatible(self) -> bool:
        """``True`` when no spatial issue was detected."""
        return not self.issues

    @property
    def failed_aspects(self) -> frozenset[CompatibilityAspect]:
        """The set of aspects with at least one issue."""
        return frozenset(issue.aspect for issue in self.issues)

    def passed(self, aspect: CompatibilityAspect) -> bool:
        """Whether one individual aspect is compatible.

        Args:
            aspect: The aspect to query.

        Returns:
            ``True`` if no issue was recorded for that aspect.
        """
        return aspect not in self.failed_aspects

    def summary(self) -> str:
        """One-line human-readable summary for logs, GUI and reports.

        Returns:
            ``"compatible"`` or the joined issue descriptions.
        """
        if self.is_compatible:
            return "compatible"
        return "; ".join(issue.description for issue in self.issues)


class GeoTiffCompatibilityValidator:
    """Compares two :class:`GeoTiffMetadata` instances spatially.

    All checks always run (no early exit), so a single validation
    reports *every* mismatch at once -- essential for useful error
    messages when a pair fails for several reasons.
    """

    def __init__(
        self,
        coordinate_tolerance: float = DEFAULT_COORDINATE_TOLERANCE,
        resolution_tolerance: float = DEFAULT_RESOLUTION_TOLERANCE,
    ) -> None:
        """Initialise the validator with explicit tolerances.

        Args:
            coordinate_tolerance: Absolute tolerance for bounds, origin
                and shear comparisons, in CRS units.
            resolution_tolerance: Absolute tolerance for pixel-size
                comparisons, in CRS units.

        Raises:
            ValueError: If a tolerance is not a positive number
                (fail fast: a zero/negative tolerance silently degrades
                every float comparison to brittle equality).
        """
        for name, value in (
            ("coordinate_tolerance", coordinate_tolerance),
            ("resolution_tolerance", resolution_tolerance),
        ):
            if not value > 0.0:
                raise ValueError(f"{name} must be positive, got {value!r}.")
        self._coordinate_tolerance = coordinate_tolerance
        self._resolution_tolerance = resolution_tolerance

    def validate(
        self, before: GeoTiffMetadata, after: GeoTiffMetadata
    ) -> GeoTiffCompatibilityResult:
        """Validate one before/after pair for pixel-by-pixel comparison.

        Spatial incompatibility is a *result*, never an exception; only
        programmer misuse raises.

        Args:
            before: Metadata of the pre-event raster.
            after: Metadata of the post-event raster.

        Returns:
            The structured compatibility result with all detected
            issues (empty for a compatible pair).

        Raises:
            TypeError: If either argument is not a
                :class:`GeoTiffMetadata` instance.
        """
        for name, candidate in (("before", before), ("after", after)):
            if not isinstance(candidate, GeoTiffMetadata):
                raise TypeError(
                    f"validate() expects GeoTiffMetadata for '{name}', "
                    f"got {type(candidate).__name__}."
                )

        issues: list[CompatibilityIssue] = []
        issues.extend(self._check_crs(before, after))
        issues.extend(self._check_dimensions(before, after))
        issues.extend(self._check_resolution(before, after))
        issues.extend(self._check_bounds(before, after))
        issues.extend(self._check_transform(before, after))

        result = GeoTiffCompatibilityResult(issues=tuple(issues))
        if result.is_compatible:
            logger.info(
                "Compatible raster pair: %s / %s", before.filename, after.filename
            )
        else:
            logger.warning(
                "Incompatible raster pair %s / %s: %s",
                before.filename,
                after.filename,
                result.summary(),
            )
        return result

    # ------------------------------------------------------------------
    # Individual checks (each returns a list of issues, possibly empty)
    # ------------------------------------------------------------------
    def _check_crs(
        self, before: GeoTiffMetadata, after: GeoTiffMetadata
    ) -> list[CompatibilityIssue]:
        """Compare coordinate reference systems (see module CRS policy).

        Args:
            before: Pre-event metadata.
            after: Post-event metadata.

        Returns:
            Issues for mixed or differing CRS; empty otherwise.
        """
        if before.crs is None and after.crs is None:
            logger.warning(
                "Both rasters lack a CRS (%s / %s): pixel alignment is "
                "checkable, geographic location is not",
                before.filename,
                after.filename,
            )
            return []
        if (before.crs is None) != (after.crs is None):
            missing = "before" if before.crs is None else "after"
            return [
                CompatibilityIssue(
                    aspect=CompatibilityAspect.CRS,
                    description=(
                        f"CRS missing on {missing} raster "
                        f"({before.crs_display} vs {after.crs_display})"
                    ),
                )
            ]
        if before.crs != after.crs:
            return [
                CompatibilityIssue(
                    aspect=CompatibilityAspect.CRS,
                    description=(
                        f"CRS differs ({before.crs_display} vs {after.crs_display})"
                    ),
                )
            ]
        return []

    @staticmethod
    def _check_dimensions(
        before: GeoTiffMetadata, after: GeoTiffMetadata
    ) -> list[CompatibilityIssue]:
        """Compare raster width and height exactly (integers).

        Args:
            before: Pre-event metadata.
            after: Post-event metadata.

        Returns:
            One issue per differing dimension.
        """
        issues: list[CompatibilityIssue] = []
        if before.width != after.width:
            issues.append(
                CompatibilityIssue(
                    aspect=CompatibilityAspect.DIMENSIONS,
                    description=(f"width differs ({before.width} vs {after.width} px)"),
                )
            )
        if before.height != after.height:
            issues.append(
                CompatibilityIssue(
                    aspect=CompatibilityAspect.DIMENSIONS,
                    description=(
                        f"height differs ({before.height} vs {after.height} px)"
                    ),
                )
            )
        return issues

    def _check_resolution(
        self, before: GeoTiffMetadata, after: GeoTiffMetadata
    ) -> list[CompatibilityIssue]:
        """Compare pixel resolution per axis within tolerance.

        Args:
            before: Pre-event metadata.
            after: Post-event metadata.

        Returns:
            One issue per axis whose pixel size differs meaningfully.
        """
        issues: list[CompatibilityIssue] = []
        for axis, index in (("x", 0), ("y", 1)):
            first, second = before.pixel_size[index], after.pixel_size[index]
            if not self._close(first, second, self._resolution_tolerance):
                issues.append(
                    CompatibilityIssue(
                        aspect=CompatibilityAspect.RESOLUTION,
                        description=(
                            f"pixel resolution {axis} differs ({first:g} vs {second:g})"
                        ),
                    )
                )
        return issues

    def _check_bounds(
        self, before: GeoTiffMetadata, after: GeoTiffMetadata
    ) -> list[CompatibilityIssue]:
        """Compare the geographic extent edge by edge within tolerance.

        Args:
            before: Pre-event metadata.
            after: Post-event metadata.

        Returns:
            A single issue naming all differing edges, or empty.
        """
        differing = [
            f"{edge} ({first:g} vs {second:g})"
            for edge, first, second in (
                ("left", before.bounds.left, after.bounds.left),
                ("bottom", before.bounds.bottom, after.bounds.bottom),
                ("right", before.bounds.right, after.bounds.right),
                ("top", before.bounds.top, after.bounds.top),
            )
            if not self._close(first, second, self._coordinate_tolerance)
        ]
        if not differing:
            return []
        return [
            CompatibilityIssue(
                aspect=CompatibilityAspect.BOUNDS,
                description="bounds differ: " + ", ".join(differing),
            )
        ]

    def _check_transform(
        self, before: GeoTiffMetadata, after: GeoTiffMetadata
    ) -> list[CompatibilityIssue]:
        """Compare origin and rotation/shear of the affine transforms.

        The scale coefficients (``a``, ``e``) are intentionally *not*
        checked here: pixel scale is owned by the resolution check, so a
        scale mismatch is reported exactly once.

        Args:
            before: Pre-event metadata.
            after: Post-event metadata.

        Returns:
            Issues for origin and/or rotation-shear differences.
        """
        issues: list[CompatibilityIssue] = []
        first, second = before.transform, after.transform
        if not (
            self._close(first.c, second.c, self._coordinate_tolerance)
            and self._close(first.f, second.f, self._coordinate_tolerance)
        ):
            issues.append(
                CompatibilityIssue(
                    aspect=CompatibilityAspect.TRANSFORM,
                    description=(
                        f"raster origin differs "
                        f"(({first.c:g}, {first.f:g}) vs "
                        f"({second.c:g}, {second.f:g}))"
                    ),
                )
            )
        if not (
            self._close(first.b, second.b, self._coordinate_tolerance)
            and self._close(first.d, second.d, self._coordinate_tolerance)
        ):
            issues.append(
                CompatibilityIssue(
                    aspect=CompatibilityAspect.TRANSFORM,
                    description=(
                        f"rotation/shear differs "
                        f"((b={first.b:g}, d={first.d:g}) vs "
                        f"(b={second.b:g}, d={second.d:g}))"
                    ),
                )
            )
        return issues

    @staticmethod
    def _close(first: float, second: float, tolerance: float) -> bool:
        """Absolute-tolerance float comparison (deterministic, documented).

        Args:
            first: First value.
            second: Second value.
            tolerance: Maximum accepted absolute difference.

        Returns:
            ``True`` if the values differ by at most ``tolerance``.
        """
        return math.isclose(first, second, rel_tol=0.0, abs_tol=tolerance)
