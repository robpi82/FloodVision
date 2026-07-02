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

from src import change_detection, config, mask_generator, visualization
from src.change_detection import MaskComparison
from src.image_loader import ImageLoader, ImagePair, find_image_pairs
from src.water_detection import WaterDetectionResult, WaterSegmentationStrategy

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
    ) -> None:
        """Initialise the batch processor.

        Args:
            loader: Used to load individual image files.
            detector: Water segmentation implementation (applied to both
                images of every pair).
            before_dir: Directory with pre-event images.
            after_dir: Directory with post-event images.
            output_dir: Root directory receiving one subdirectory per pair.
        """
        self._loader = loader
        self._detector = detector
        self._before_dir = before_dir
        self._after_dir = after_dir
        self._output_dir = output_dir

    def run(self) -> BatchResult:
        """Process all matching image pairs.

        Returns:
            A :class:`BatchResult` with one record per pair, in
            deterministic filename order.

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
            logger.info("[%d/%d] Processing pair %s", index, total, pair.name)
            records.append(self._process_single(pair))

        result = BatchResult(records=tuple(records))
        logger.info(
            "Batch finished: %d successful, %d failed",
            len(result.successful),
            len(result.failed),
        )
        return result

    def _process_single(self, pair: ImagePair) -> FloodComparisonResult:
        """Process one pair inside its own failure boundary.

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
            before = self._detector.detect(self._loader.load(pair.before_path))
            after = self._detector.detect(self._loader.load(pair.after_path))
            comparison = change_detection.compare_masks(before.mask, after.mask)
            self._save_products(pair, before, after, comparison)
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

    def _save_products(
        self,
        pair: ImagePair,
        before: WaterDetectionResult,
        after: WaterDetectionResult,
        comparison: MaskComparison,
    ) -> None:
        """Write all products of one pair into its own output subdirectory.

        Layout (requirement of v0.4)::

            data/output/<pair-stem>/
                before_mask.png     binary pre-event water mask
                after_mask.png      binary post-event water mask
                new_flood_mask.png  red-on-black newly flooded areas
                overlay.png         AFTER image + semi-transparent red layer
                comparison.png      four-panel review figure

        Figures are saved with ``show=False``: opening dozens of blocking
        matplotlib windows would make batch mode unusable.

        Args:
            pair: The processed pair (used for directory naming).
            before: Detection result of the pre-event image.
            after: Detection result of the post-event image.
            comparison: Mask comparison result.
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
