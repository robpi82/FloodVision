"""Right-hand statistics panel with live per-pair metrics.

Pure presentation: the panel formats and displays values from backend
records, it computes nothing itself (the backend's ``BatchResult``
properties own all statistics -- Single Source of Truth).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from src.batch_processor import BatchResult, FloodComparisonResult, ProcessingStatus

_PLACEHOLDER = "\u2014"  # em dash


class StatisticsPanel(QWidget):
    """Displays batch progress and the metrics of the current pair."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the label grid.

        Args:
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._values: dict[str, QLabel] = {}

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        for key, caption in (
            ("pairs", "Image pairs"),
            ("current", "Current image"),
            ("progress", "Progress"),
            ("status", "Status"),
            ("before", "Water before"),
            ("after", "Water after"),
            ("increase", "Flood increase"),
            ("time", "Processing time"),
        ):
            value = QLabel(_PLACEHOLDER)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._values[key] = value
            form.addRow(f"{caption}:", value)

        box = QGroupBox("Statistics")
        box.setLayout(form)
        layout = QVBoxLayout(self)
        layout.addWidget(box)
        layout.addStretch(1)

    def reset(self, total_pairs: int | None = None) -> None:
        """Clear all values, optionally pre-filling the pair count.

        Args:
            total_pairs: Known number of pairs, or ``None`` before start.
        """
        for label in self._values.values():
            label.setText(_PLACEHOLDER)
        if total_pairs is not None:
            self._values["pairs"].setText(str(total_pairs))

    def show_record(
        self, record: FloodComparisonResult, index: int, total: int
    ) -> None:
        """Display the metrics of one finished pair.

        Args:
            record: The pair's result record.
            index: 1-based pair index.
            total: Total number of pairs.
        """
        ok = record.status is ProcessingStatus.SUCCESS
        self._values["pairs"].setText(str(total))
        self._values["current"].setText(record.filename)
        self._values["progress"].setText(f"{index} / {total}")
        self._values["status"].setText("OK" if ok else "FAILED")
        self._values["status"].setStyleSheet(
            "color: #4caf50;" if ok else "color: #e05555; font-weight: bold;"
        )
        self._values["before"].setText(_percent(record.water_before_percent))
        self._values["after"].setText(_percent(record.water_after_percent))
        self._values["increase"].setText(_points(record.increase_percent))
        self._values["time"].setText(f"{record.processing_time_seconds:.2f} s")

    def show_batch_result(self, result: BatchResult) -> None:
        """Switch the panel to end-of-batch averages.

        Args:
            result: The finished batch result.
        """
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
