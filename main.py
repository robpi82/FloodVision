"""FloodVision entry point.

This file contains *no business logic*. Its only job is to wire the
application together (logging, directories) and to orchestrate the
change-detection workflow:

    1. Match before/after image pairs by filename
       (``data/before/`` vs. ``data/after/``); unmatched files are logged
       and skipped.
    2. For every pair: detect water in both images, compute the newly
       flooded areas and export masks, overlay and comparison figure into
       ``data/output/<pair>/``. A damaged pair is logged and skipped,
       never aborts the batch.
    3. Save the per-pair report to ``data/output/report.csv``.
    4. Log the change-detection summary block.

``run()`` wires concrete objects (``ImageLoader``, ``HSVWaterDetector``)
into the :class:`BatchProcessor`, which itself only depends on
abstractions -- composition happens here, at the outermost layer
("composition root" pattern).
"""

from __future__ import annotations

import logging
import sys

from src import __version__, config, report_generator, utils
from src.batch_processor import BatchProcessor
from src.exceptions import FloodVisionError
from src.image_loader import ImageLoader
from src.water_detection import HSVWaterDetector, WaterSegmentationStrategy

logger = logging.getLogger(__name__)


def run() -> int:
    """Execute the change-detection workflow.

    Returns:
        Process exit code: ``0`` if every pair succeeded, ``1`` if the
        batch completed but at least one pair failed. A non-zero code on
        partial failure lets shell scripts and CI pipelines detect
        problems without parsing logs.

    Raises:
        FloodVisionError: For any expected, domain-level failure such as
            an empty input directory (handled in :func:`main`).
    """
    utils.setup_logging()
    utils.ensure_directories(
        config.BEFORE_DATA_DIR, config.AFTER_DATA_DIR, config.OUTPUT_DATA_DIR
    )
    logger.info("FloodVision v%s starting (change-detection batch)", __version__)

    # Composition root: the only place where concrete classes are chosen.
    detector: WaterSegmentationStrategy = HSVWaterDetector()
    processor = BatchProcessor(loader=ImageLoader(), detector=detector)

    result = processor.run()

    report_generator.save_report_csv(result)
    logger.info("\n%s", report_generator.build_summary(result))

    return 0 if not result.failed else 1


def main() -> None:
    """Program entry point with top-level error handling."""
    try:
        sys.exit(run())
    except FloodVisionError as error:
        # Expected domain errors: log a clean message, exit with failure code.
        logger.error("%s", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
