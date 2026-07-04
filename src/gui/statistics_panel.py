"""Statistics panel content: live batch counters plus current-pair metrics.

The panel aggregates only what arrives as a *stream* (counts, cumulative
pixels, wall-clock time) -- all end-of-batch statistics still come from
the backend's :class:`~src.batch_processor.BatchResult` properties
(Single Source of Truth). Hosted inside a ``QDockWidget`` by the main
window, so users can float or re-dock it like in any professional
desktop tool.
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from src.batch_processor import BatchResult, FloodComparisonResult, ProcessingStatus

_PLACEHOLDER = "\u2014"  # em dash

_BATCH_ROWS: tuple[tuple[str, str], ...] = (
    ("processed", "Processed pairs"),
    ("successful", "Successful"),
    ("failed", "Failed"),
    ("pixels", "Flooded pixels"),
    ("total_time", "Total runtime"),
    ("avg_time", "Average runtime"),
    ("progress", "Progress"),
)

_PAIR_ROWS: tuple[tuple[str, str], ...] = (
    ("current", "Current image"),
    ("status", "Status"),
    ("before", "Water before"),
    ("after", "Water after"),
    ("increase", "Flood increase"),
    ("time", "Processing time"),
)


class StatisticsPanel(QWidget):
    """Displays live batch counters and the metrics of one pair."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build both label groups.

        Args:
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._values: dict[str, QLabel] = {}
        self._start_time: float | None = None
        self._processed = 0
        self._successful = 0
        self._failed = 0
        self._flooded_pixels = 0

        layout = QVBoxLayout(self)
        layout.addWidget(self._make_group("Batch", _BATCH_ROWS))
        layout.addWidget(self._make_group("Current pair", _PAIR_ROWS))
        layout.addStretch(1)

    def _make_group(self, title: str, rows: tuple[tuple[str, str], ...]) -> QGroupBox:
        """Create one labelled form group and register its value labels.

        Args:
            title: Group box title.
            rows: ``(key, caption)`` pairs for the form rows.

        Returns:
            The assembled group box.
        """
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        for key, caption in rows:
            value = QLabel(_PLACEHOLDER)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._values[key] = value
            form.addRow(f"{caption}:", value)
        box = QGroupBox(title)
        box.setLayout(form)
        return box

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def reset(self) -> None:
        """Clear everything and start the wall-clock timer.

        ``time.monotonic`` is used because runtime measurement must never
        jump backwards with system clock adjustments.
        """
        for label in self._values.values():
            label.setText(_PLACEHOLDER)
            label.setStyleSheet("")
        self._start_time = time.monotonic()
        self._processed = 0
        self._successful = 0
        self._failed = 0
        self._flooded_pixels = 0

    def on_pair(self, record: FloodComparisonResult, index: int, total: int) -> None:
        """Update counters and current-pair rows for one finished pair.

        Args:
            record: The pair's result record.
            index: 1-based pair index.
            total: Total number of pairs.
        """
        ok = record.status is ProcessingStatus.SUCCESS
        self._processed += 1
        self._successful += 1 if ok else 0
        self._failed += 0 if ok else 1
        self._flooded_pixels += record.new_flood_pixels or 0

        elapsed = self.elapsed_seconds
        self._values["processed"].setText(f"{self._processed} / {total}")
        self._values["successful"].setText(str(self._successful))
        self._values["failed"].setText(str(self._failed))
        self._values["pixels"].setText(f"{self._flooded_pixels:,}")
        self._values["total_time"].setText(f"{elapsed:.1f} s")
        self._values["avg_time"].setText(f"{elapsed / self._processed:.2f} s")
        self._values["progress"].setText(f"{100 * index // total} %")

        self.show_pair_details(record)

    def show_pair_details(self, record: FloodComparisonResult) -> None:
        """Fill the current-pair group (also used while navigating).

        Args:
            record: The record to display.
        """
        ok = record.status is ProcessingStatus.SUCCESS
        self._values["current"].setText(record.filename)
        self._values["status"].setText("OK" if ok else "FAILED")
        self._values["status"].setStyleSheet(
            "color: #4caf50;" if ok else "color: #e05555; font-weight: bold;"
        )
        self._values["before"].setText(_percent(record.water_before_percent))
        self._values["after"].setText(_percent(record.water_after_percent))
        self._values["increase"].setText(_points(record.increase_percent))
        self._values["time"].setText(f"{record.processing_time_seconds:.2f} s")

    def show_batch_result(self, result: BatchResult) -> None:
        """Switch the pair group to end-of-batch averages.

        Args:
            result: The finished batch result.
        """
        self._values["progress"].setText("done")
        self._values["current"].setText("(batch finished)")
        self._values["status"].setStyleSheet("")
        self._values["status"].setText(
            f"{len(result.successful)} OK / {len(result.failed)} failed"
        )
        self._values["before"].setText(
            _percent(result.average_water_before_percent) + " (avg)"
        )
        self._values["after"].setText(
            _percent(result.average_water_after_percent) + " (avg)"
        )
        self._values["increase"].setText(
            _points(result.average_increase_percent) + " (avg)"
        )

    @property
    def elapsed_seconds(self) -> float:
        """Wall-clock seconds since :meth:`reset` (0.0 before first use)."""
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time


def _percent(value: float | None) -> str:
    """Format an optional percentage.

    Args:
        value: Percentage or ``None``.

    Returns:
        ``"12.3 %"`` or a placeholder.
    """
    return _PLACEHOLDER if value is None else f"{value:.1f} %"


def _points(value: float | None) -> str:
    """Format an optional percentage-point change (signed).

    Args:
        value: Change in percentage points or ``None``.

    Returns:
        ``"+4.2 pp"`` or a placeholder.
    """
    return _PLACEHOLDER if value is None else f"{value:+.1f} pp"
