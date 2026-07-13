"""Batch processing of before/after image pairs into change products.

This module is the *application service* of the change-detection workflow:
it orchestrates loader, detector, change detection and product export for
many image pairs, isolates failures per pair and collects structured
results. It contains no image-processing logic itself -- detection stays
in :mod:`src.water_detection`, comparison in :mod:`src.change_detection`
and mask products in :mod:`src.mask_generator` (Single Responsibility).

Error-handling contract:
    One damaged pair must never abort the batch. Each pair is therefore
    processed inside its own failure boundary; errors are logged with full
    traceback and recorded in the result instead of being raised.

Public API:
    * :class:`ProcessingStatus`     -- success/failure enum.
    * :class:`FloodComparisonResult` -- immutable per-pair result row.
    * :class:`BatchResult`          -- all records plus derived statistics.
    * :class:`BatchProcessor`       -- runs the batch.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from PIL import Image

from src import change_detection, config, geotiff_export, mask_generator, visualization
from src.change_detection import MaskComparison
from src.exceptions import GeoTiffPairError
from src.geotiff_compatibility import GeoTiffCompatibilityValidator
from src.geotiff_image_adapter import GeoTiffImageAdapter
from src.geotiff_loader import GeoTiffLoader, GeoTiffMetadata
from src.geotiff_raster_loader import GeoTiffRasterData, GeoTiffRasterLoader
from src.image_loader import ImageLoader, ImagePair, find_image_pairs
from src.sentinel2_band_resolver import Sentinel2BandResolver
from src.stretch import compute_shared_stretch
from src.water_detection import WaterDetectionResult, WaterSegmentationStrategy
from src.spectral_detector import SpectralWaterDetector

logger = logging.getLogger(__name__)


class ProcessingStatus(StrEnum):
    """Outcome of processing a single image pair.

    A :class:`enum.StrEnum` is used (instead of plain strings) so that the
    set of valid states is closed and typo-proof, while members still
    serialise naturally as ``"success"`` / ``"failed"`` in CSV files.
    """

    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class FloodComparisonResult:
    """Immutable result row for exactly one processed image pair.

    Attributes:
        filename: Shared name of the before/after pair.
        status: Whether processing succeeded or failed.
        water_before_percent: Water coverage before the event (percent);
            ``None`` on failure.
        water_after_percent: Water coverage after the event (percent);
            ``None`` on failure.
        new_water_percent: Share of the image newly flooded (percent);
            ``None`` on failure.
        new_flood_pixels: Absolute count of newly flooded pixels;
            ``None`` on failure.
        increase_percent: Net coverage change in percentage points
            (after - before); ``None`` on failure.
        processing_time_seconds: Wall-clock duration of the attempt,
            measured with a monotonic clock.
        error_message: Human-readable error description; ``None`` on
            success.
    """

    filename: str
    status: ProcessingStatus
    water_before_percent: float | None
    water_after_percent: float | None
    new_water_percent: float | None
    new_flood_pixels: int | None
    increase_percent: float | None
    processing_time_seconds: float
    error_message: str | None = None

    def to_dict(self) -> dict[str, str | float | int | None]:
        """Convert the record to plain primitives for tabular export.

        Explicit conversion (instead of :func:`dataclasses.asdict`) keeps
        full control over the CSV schema: the enum becomes its string
        value and floats are rounded to a sensible report precision. The
        schema lives in exactly one place -- next to the record itself.

        Returns:
            A dictionary with one entry per report column.
        """

        def rounded(value: float | None, digits: int) -> float | None:
            return None if value is None else round(value, digits)

        return {
            "filename": self.filename,
            "status": self.status.value,
            "water_before_percent": rounded(self.water_before_percent, 2),
            "water_after_percent": rounded(self.water_after_percent, 2),
            "increase_percent": rounded(self.increase_percent, 2),
            "new_flood_pixels": self.new_flood_pixels,
            "new_water_percent": rounded(self.new_water_percent, 2),
            "processing_time_seconds": round(self.processing_time_seconds, 3),
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class BatchResult:
    """All per-pair records of one batch run plus derived statistics.

    Records are stored as a tuple (not a list) so the result object is
    deeply immutable. Statistics are computed on demand from the
    successful records only; every property handles the empty case
    explicitly and returns ``None`` instead of raising when nothing
    succeeded.
    """

    records: tuple[FloodComparisonResult, ...]

    @property
    def successful(self) -> tuple[FloodComparisonResult, ...]:
        """All records that finished successfully."""
        return tuple(r for r in self.records if r.status is ProcessingStatus.SUCCESS)

    @property
    def failed(self) -> tuple[FloodComparisonResult, ...]:
        """All records that failed."""
        return tuple(r for r in self.records if r.status is ProcessingStatus.FAILED)

    @property
    def average_water_before_percent(self) -> float | None:
        """Mean pre-event water coverage over successful pairs."""
        return self._average(lambda r: r.water_before_percent)

    @property
    def average_water_after_percent(self) -> float | None:
        """Mean post-event water coverage over successful pairs."""
        return self._average(lambda r: r.water_after_percent)

    @property
    def average_increase_percent(self) -> float | None:
        """Mean net coverage change (percentage points) over successes."""
        return self._average(lambda r: r.increase_percent)

    @property
    def largest_increase_record(self) -> FloodComparisonResult | None:
        """The successful record with the largest net increase."""
        candidates = [r for r in self.successful if r.increase_percent is not None]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.increase_percent or 0.0)

    def _average(
        self, selector: Callable[[FloodComparisonResult], float | None]
    ) -> float | None:
        """Average a metric over successful records, ``None`` if empty.

        Args:
            selector: Extracts the metric from a record.

        Returns:
            The mean value, or ``None`` when no successful record carries
            the metric (avoids ``ZeroDivisionError`` by construction).
        """
        values = [value for r in self.successful if (value := selector(r)) is not None]
        if not values:
            return None
        return sum(values) / len(values)


class BatchProcessor:
    """Processes every before/after pair into flood-change products.

    Collaborators are injected via the constructor: the *loader* reads
    image files, the *detector* -- typed against the
    :class:`WaterSegmentationStrategy` protocol -- finds water. The
    processor itself only coordinates (Dependency Inversion); swapping in
    an ML segmenter requires zero changes here.
    """

    def __init__(
            self,
            loader: ImageLoader,
            detector: WaterSegmentationStrategy,
            before_dir: Path = config.BEFORE_DATA_DIR,
            after_dir: Path = config.AFTER_DATA_DIR,
            output_dir: Path = config.OUTPUT_DATA_DIR,
            on_pair_done: Callable[[FloodComparisonResult, int, int], None] | None = None,
            is_cancelled: Callable[[], bool] | None = None,
            geotiff_loader: GeoTiffLoader | None = None,
            compatibility_validator: GeoTiffCompatibilityValidator | None = None,
            geotiff_raster_loader: GeoTiffRasterLoader | None = None,
            geotiff_image_adapter: GeoTiffImageAdapter | None = None,
            sentinel2_band_resolver: Sentinel2BandResolver | None = None,
            multispectral_rgb_bands: tuple[int, int, int] = config.MULTISPECTRAL_RGB_BANDS,
    ) -> None:
        """Initialise the batch processor.

        Args:
            loader: Used to load individual image files.
            detector: Water segmentation implementation (applied to both
                images of every pair).
            before_dir: Directory with pre-event images.
            after_dir: Directory with post-event images.
            output_dir: Root directory receiving one subdirectory per pair.
            on_pair_done: Optional observer called after every pair with
                ``(record, index, total)`` -- e.g. a GUI progress hook.
                Exceptions raised by the observer are logged and never
                abort the batch. ``None`` (default) preserves the exact
                pre-v0.6 behaviour.
            is_cancelled: Optional callable polled before each pair; when
                it returns ``True`` the batch stops gracefully and returns
                the records processed so far. ``None`` disables
                cancellation (pre-v0.6 behaviour).
            geotiff_loader: Classifies files and reads geospatial
                metadata; a default instance is created when omitted, so
                existing callers need no changes.
            compatibility_validator: Validates GeoTIFF pairs spatially;
                default instance created when omitted.
        """
        self._loader = loader
        self._detector = detector
        self._before_dir = before_dir
        self._after_dir = after_dir
        self._output_dir = output_dir
        self._on_pair_done = on_pair_done
        self._is_cancelled = is_cancelled
        self._geotiff_loader = geotiff_loader or GeoTiffLoader()
        self._compatibility_validator = (
                compatibility_validator or GeoTiffCompatibilityValidator()
        )
        self._geotiff_raster_loader = (
                geotiff_raster_loader or GeoTiffRasterLoader()
        )
        self._geotiff_image_adapter = (
                geotiff_image_adapter or GeoTiffImageAdapter()
        )
        self._sentinel2_band_resolver = (
                sentinel2_band_resolver or Sentinel2BandResolver()
        )
        self._multispectral_rgb_bands = multispectral_rgb_bands

    def run(self) -> BatchResult:
        """Process all matching image pairs.

        Returns:
            A :class:`BatchResult` with one record per pair, in
            deterministic filename order. If cancellation was requested,
            the result contains only the pairs processed up to that point.

        Raises:
            NoImagesFoundError: If either input directory is empty.
            NoImagePairsFoundError: If no filename exists in both
                directories. Empty inputs are a domain error for the
                caller -- unlike a *partially* failing batch, which is
                reported via the records.
        """
        pairs = find_image_pairs(self._before_dir, self._after_dir)
        total = len(pairs)
        logger.info("Batch started: %d image pair(s) to process", total)

        records: list[FloodComparisonResult] = []
        for index, pair in enumerate(pairs, start=1):
            if self._is_cancelled is not None and self._is_cancelled():
                logger.warning(
                    "Batch cancelled by user after %d of %d pair(s)",
                    len(records),
                    total,
                )
                break
            logger.info("[%d/%d] Processing pair %s", index, total, pair.name)
            record = self._process_single(pair)
            records.append(record)
            self._notify_pair_done(record, index, total)

        result = BatchResult(records=tuple(records))
        logger.info(
            "Batch finished: %d successful, %d failed",
            len(result.successful),
            len(result.failed),
        )
        return result

    def _notify_pair_done(
        self, record: FloodComparisonResult, index: int, total: int
    ) -> None:
        """Invoke the optional observer, shielding the batch from it.

        An observer (GUI update, metrics push) must never be able to kill
        the processing loop -- its errors are logged with traceback and
        swallowed, mirroring the per-pair failure boundary.

        Args:
            record: The record of the just-finished pair.
            index: 1-based index of the pair within the batch.
            total: Total number of pairs in the batch.
        """
        if self._on_pair_done is None:
            return
        try:
            self._on_pair_done(record, index, total)
        except Exception:  # noqa: BLE001 -- observer isolation boundary
            logger.exception("on_pair_done observer raised; batch continues")

    def _resolve_rgb_bands(
        self,
        raster: GeoTiffRasterData,
    ) -> tuple[int, int, int]:
        """Resolve the RGB band selection for a single raster.

        Band descriptions take precedence over the configured default: they
        describe the *actual* band order of this file, while the configuration
        can only describe an expected one. Rasters without any description
        fall back to the configured multispectral selection.

        Args:
            raster: The raster whose band order is to be resolved.

        Returns:
            Three zero-based band indices in RGB order.
        """
        if any(
            description is not None for description in raster.band_descriptions
        ):
            return self._sentinel2_band_resolver.resolve_rgb_indices(
                raster.band_descriptions,
            )

        return self._multispectral_rgb_bands

    def _load_detection_images(
        self,
        pair: ImagePair,
        is_geotiff: bool,
    ) -> tuple[Image.Image, Image.Image]:
        """Load both images of a pair for water detection.

        The pair -- not the single file -- is the unit of loading, because the
        two rasters have to be converted to RGB *together*.

        A GeoTIFF carries raw sensor values (typically uint16 DNs), which must
        be mapped onto the 0-255 display range the detector works on. If that
        mapping is derived from each raster in isolation, its value range
        differs between the two: newly flooded, dark pixels lower the minimum
        of the *after* raster, and the resulting offset shifts *every* pixel of
        that raster -- including physically unchanged land. Change detection
        would then partly measure the normalisation instead of the scene.

        Both rasters are therefore converted with one shared stretch derived
        from the pair as a whole, which maps identical raster values onto
        identical display values in both images.

        Ordinary image files (PNG, JPEG) are already on an absolute 0-255
        scale and keep using the existing loader unchanged.

        Args:
            pair: The before/after pair to load.
            is_geotiff: Whether the pair was classified as a georeferenced
                GeoTIFF pair by :meth:`_ensure_geospatial_compatibility`.

        Returns:
            The before and after images, ready for detection.

        Raises:
            GeoTiffPairError: If the two rasters resolve to different RGB band
                selections, which would make the images incomparable.
            ImageLoadError: If a file cannot be read.
        """
        if not is_geotiff:
            return (
                self._loader.load(pair.before_path),
                self._loader.load(pair.after_path),
            )

        before_raster = self._geotiff_raster_loader.load(pair.before_path)
        after_raster = self._geotiff_raster_loader.load(pair.after_path)

        before_bands = self._resolve_rgb_bands(before_raster)
        after_bands = self._resolve_rgb_bands(after_raster)

        if before_bands != after_bands:
            raise GeoTiffPairError(
                pair.name,
                "the before and after rasters resolve to different RGB band "
                f"selections ({before_bands} vs {after_bands}); comparing "
                "different spectral bands would be a wrong result",
            )

        stretch = compute_shared_stretch(
            before_raster,
            after_raster,
            bands=before_bands,
        )

        if stretch is None:
            logger.warning(
                "No shared value range could be derived for GeoTIFF pair %s; "
                "falling back to the per-image stretch, which biases the "
                "comparison between the two images",
                pair.name,
            )
        else:
            logger.info(
                "GeoTIFF pair %s uses a shared display stretch [%.4g, %.4g] "
                "over bands %s",
                pair.name,
                stretch.lo,
                stretch.hi,
                before_bands,
            )

        before_image = self._geotiff_image_adapter.to_image(
            before_raster,
            bands=before_bands,
            stretch=stretch,
        )
        after_image = self._geotiff_image_adapter.to_image(
            after_raster,
            bands=after_bands,
            stretch=stretch,
        )

        return before_image, after_image

    def _detect_water(
            self,
            image: Image.Image,
            path: Path,
    ) -> WaterDetectionResult:
        """Run water detection using the configured detection strategy."""

        if isinstance(self._detector, SpectralWaterDetector):
            raster = self._geotiff_raster_loader.load(path)
            return self._detector.detect(raster)

        return self._detector.detect(image)

        return self._detector.detect(image)

    def _process_single(self, pair: ImagePair) -> FloodComparisonResult:
        """Process one pair inside its own failure boundary.

        Since v0.8 the pair first passes the geospatial gate
        (:meth:`_ensure_geospatial_compatibility`); mixed or spatially
        incompatible GeoTIFF pairs fail here as records, exactly like
        any other per-pair error.

        Catching broad ``Exception`` here is *correct* engineering: the
        batch contract ("one bad pair never kills the run") requires
        converting any per-item error into data. ``logger.exception``
        preserves the full traceback, and ``KeyboardInterrupt`` /
        ``SystemExit`` are *not* caught (they derive from
        ``BaseException``), so Ctrl+C still stops the batch.

        Args:
            pair: The before/after pair to process.

        Returns:
            A success record with all metrics, or a failure record with
            the error message -- never raises for per-pair problems.
        """
        start = time.perf_counter()
        try:
            geo_metadata = self._ensure_geospatial_compatibility(pair)
            is_geotiff = geo_metadata is not None

            before_image, after_image = self._load_detection_images(
                pair,
                is_geotiff,
            )

            before = self._detector.detect(before_image)
            after = self._detector.detect(after_image)

            comparison = change_detection.compare_masks(
                before.mask,
                after.mask,
            )
            self._save_products(pair, before, after, comparison, geo_metadata)
        except Exception as error:  # noqa: BLE001 -- intentional batch boundary
            elapsed = time.perf_counter() - start
            logger.exception("Processing failed for pair %s", pair.name)
            return FloodComparisonResult(
                filename=pair.name,
                status=ProcessingStatus.FAILED,
                water_before_percent=None,
                water_after_percent=None,
                new_water_percent=None,
                new_flood_pixels=None,
                increase_percent=None,
                processing_time_seconds=elapsed,
                error_message=str(error),
            )

        elapsed = time.perf_counter() - start
        logger.info(
            "Done: %s -> new flood %.2f %% (net %+.2f pp) in %.2f s",
            pair.name,
            comparison.new_water_percent,
            comparison.increase_percent,
            elapsed,
        )
        return FloodComparisonResult(
            filename=pair.name,
            status=ProcessingStatus.SUCCESS,
            water_before_percent=comparison.water_before_percent,
            water_after_percent=comparison.water_after_percent,
            new_water_percent=comparison.new_water_percent,
            new_flood_pixels=comparison.new_water_pixels,
            increase_percent=comparison.increase_percent,
            processing_time_seconds=elapsed,
        )

    def _ensure_geospatial_compatibility(
        self, pair: ImagePair
    ) -> GeoTiffMetadata | None:
        """Gate: reject geospatially unusable pairs before detection.

        Classification semantics (mirrored by the integration tests):

        * **Neither** file is a georeferenced GeoTIFF (normal images,
          plain TIFFs, unreadable files): no gate -- the existing pixel
          workflow proceeds exactly as before v0.8.
        * **Exactly one** file is a georeferenced GeoTIFF: the pair is
          rejected; alignment between a georeferenced and a
          non-georeferenced file cannot be verified, and silently
          comparing them would be a wrong result waiting to happen.
        * **Both** are GeoTIFFs: metadata is read by the loader and
          compared by the validator; incompatible pairs are rejected
          with the validator's one-line summary as the reason.

        A *compatible* GeoTIFF pair still continues into the existing
        Pillow/OpenCV pixel pipeline for detection -- that part is
        unchanged. Since v0.8's export step, the returned metadata lets
        the caller additionally write a georeferenced GeoTIFF of the
        flood result alongside the existing PNG products. The *after*
        raster's metadata is returned (not *before*): compatibility
        already guarantees an identical grid, and the flood result is
        conceptually anchored to the post-event scene.

        Args:
            pair: The pair to gate.

        Returns:
            The *after* raster's :class:`~src.geotiff_loader.GeoTiffMetadata`
            for a compatible GeoTIFF pair, so the caller can export a
            georeferenced result; ``None`` for an ordinary (non-GeoTIFF)
            pair, which needs no georeferenced output.

        Raises:
            GeoTiffPairError: If the pair mixes georeferencing or is
                spatially incompatible.
            ImageLoadError: If a file classified as GeoTIFF cannot be
                read during metadata extraction.
        """
        before_is_geo = self._geotiff_loader.is_geotiff(pair.before_path)
        after_is_geo = self._geotiff_loader.is_geotiff(pair.after_path)
        if not before_is_geo and not after_is_geo:
            return None
        if before_is_geo != after_is_geo:
            non_geo_side = "after" if before_is_geo else "before"
            raise GeoTiffPairError(
                pair.name,
                f"mixed georeferencing: the {non_geo_side} file is not a "
                f"georeferenced GeoTIFF",
            )
        logger.info("GeoTIFF pair detected: %s", pair.name)
        before_metadata = self._geotiff_loader.read_metadata(pair.before_path)
        after_metadata = self._geotiff_loader.read_metadata(pair.after_path)
        result = self._compatibility_validator.validate(before_metadata, after_metadata)
        if not result.is_compatible:
            raise GeoTiffPairError(pair.name, result.summary())
        logger.info(
            "GeoTIFF pair %s is spatially compatible; the flood result will "
            "be exported as a georeferenced GeoTIFF",
            pair.name,
        )
        return after_metadata

    def _save_products(
        self,
        pair: ImagePair,
        before: WaterDetectionResult,
        after: WaterDetectionResult,
        comparison: MaskComparison,
        geo_metadata: GeoTiffMetadata | None,
    ) -> None:
        """Write all products of one pair into its own output subdirectory.

        Layout (requirement of v0.4, ``new_flood_mask.tif`` added in v0.8)::

            data/output/<pair-stem>/
                before_mask.png     binary pre-event water mask
                after_mask.png      binary post-event water mask
                new_flood_mask.png  red-on-black newly flooded areas
                overlay.png         AFTER image + semi-transparent red layer
                comparison.png      four-panel review figure
                new_flood_mask.tif  georeferenced flood mask (GeoTIFF pairs only)

        Figures are saved with ``show=False``: opening dozens of blocking
        matplotlib windows would make batch mode unusable.

        Args:
            pair: The processed pair (used for directory naming).
            before: Detection result of the pre-event image.
            after: Detection result of the post-event image.
            comparison: Mask comparison result.
            geo_metadata: The *after* raster's metadata for a compatible
                GeoTIFF pair (triggers the additional georeferenced
                export below); ``None`` for an ordinary image pair,
                which leaves the existing PNG-only workflow untouched.
        """
        out_dir = self._output_dir / pair.stem
        new_flood_rgb = mask_generator.colorize_mask(comparison.new_water_mask)
        overlay = mask_generator.create_overlay(
            after.image_rgb,
            comparison.new_water_mask,
            color=config.NEW_FLOOD_COLOR_RGB,
            alpha=config.CHANGE_OVERLAY_ALPHA,
        )

        visualization.save_image(before.mask, out_dir / "before_mask.png")
        visualization.save_image(after.mask, out_dir / "after_mask.png")
        visualization.save_image(new_flood_rgb, out_dir / "new_flood_mask.png")
        visualization.save_image(overlay, out_dir / "overlay.png")
        visualization.display_panels(
            [
                ("Before", before.image_rgb),
                ("After", after.image_rgb),
                ("New flood (red)", new_flood_rgb),
                (f"Overlay ({comparison.new_water_percent:.1f} % new water)", overlay),
            ],
            suptitle=f"FloodVision change detection - {pair.name}",
            save_path=out_dir / "comparison.png",
            show=False,
        )

        if geo_metadata is not None:
            geotiff_export.export_flood_mask_geotiff(
                comparison.new_water_mask, geo_metadata, out_dir / "new_flood_mask.tif"
            )