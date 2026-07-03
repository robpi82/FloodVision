"""Background execution of the batch on a Qt worker thread.

The GUI must never freeze (requirement), so the entire backend run lives
on a :class:`~PySide6.QtCore.QThread`. Communication back to the GUI uses
Qt signals exclusively -- cross-thread signal delivery is queued by Qt,
which makes it the safe channel for results, progress and errors.

The worker contains **zero processing logic**: it instantiates the
existing backend objects (:class:`~src.water_detection.HSVWaterDetector`,
:class:`~src.batch_processor.BatchProcessor`) and forwards their results.
GUI settings flow into the backend exclusively through its existing
dependency-injection parameters -- the payoff of the architecture built
since v0.2.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src import report_generator
from src.batch_processor import BatchProcessor, FloodComparisonResult
from src.exceptions import FloodVisionError
from src.gui.app_settings import AppSettings
from src.image_loader import ImageLoader
from src.water_detection import HSVRange, HSVWaterDetector

logger = logging.getLogger(__name__)


class BatchWorker(QThread):
    """Runs one complete batch on a background thread.

    Signals:
        pair_completed: Emitted after every pair with
            ``(record, index, total)``. ``object`` is used for the record
            because Qt signals cannot carry arbitrary dataclass types
            natively.
        batch_finished: Emitted with the final
            :class:`~src.batch_processor.BatchResult` (also after a
            user cancellation, then with the partial result).
        batch_failed: Emitted with ``(title, message)`` when the batch
            could not run at all (e.g. no image pairs found).
    """

    pair_completed = Signal(object, int, int)
    batch_finished = Signal(object)
    batch_failed = Signal(str, str)

    def __init__(self, settings: AppSettings) -> None:
        """Capture an immutable settings snapshot for this run.

        Args:
            settings: The GUI settings at the moment the run was started.
                Taking a snapshot (frozen dataclass) means later edits in
                the settings dialog cannot race a running batch.
        """
        super().__init__()
        self._settings = settings
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        """Ask the running batch to stop after the current pair.

        Thread-safe by construction: :class:`threading.Event` is the
        standard primitive for exactly this one-way flag, and the backend
        polls it between pairs via its ``is_cancelled`` hook.
        """
        logger.info("Cancellation requested by user")
        self._cancel_event.set()

    @property
    def was_cancelled(self) -> bool:
        """Whether the user requested cancellation for this run."""
        return self._cancel_event.is_set()

    def run(self) -> None:
        """Execute the batch (called by Qt on the worker thread).

        Expected domain problems (empty directories, no pairs) surface as
        ``batch_failed`` with a user-friendly message; unexpected bugs are
        logged with traceback and reported generically -- the GUI must
        survive anything the backend throws.
        """
        try:
            detector = HSVWaterDetector(
                hsv_range=HSVRange(
                    lower=self._settings.hsv_lower, upper=self._settings.hsv_upper
                )
            )
            output_dir = Path(self._settings.output_dir)
            processor = BatchProcessor(
                loader=ImageLoader(),
                detector=detector,
                before_dir=Path(self._settings.before_dir),
                after_dir=Path(self._settings.after_dir),
                output_dir=output_dir,
                on_pair_done=self._on_pair_done,
                is_cancelled=self._cancel_event.is_set,
            )
            result = processor.run()
            if result.records:
                report_generator.save_report_csv(result, path=output_dir / "report.csv")
            self.batch_finished.emit(result)
        except FloodVisionError as error:
            logger.error("%s", error)
            self.batch_failed.emit("Batch could not start", str(error))
        except Exception:  # noqa: BLE001 -- GUI must never crash from backend
            logger.exception("Unexpected error in batch worker")
            self.batch_failed.emit(
                "Unexpected error",
                "The batch aborted unexpectedly. See the log panel and "
                "logs/floodvision.log for the full traceback.",
            )

    def _on_pair_done(
        self, record: FloodComparisonResult, index: int, total: int
    ) -> None:
        """Backend observer hook: forward per-pair progress as a signal.

        Runs on the worker thread; the signal emission is the thread
        boundary crossing.

        Args:
            record: Result record of the finished pair.
            index: 1-based pair index.
            total: Total number of pairs.
        """
        self.pair_completed.emit(record, index, total)
