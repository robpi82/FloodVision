"""Modal settings editor: HSV thresholds, output folder, theme.

The dialog edits a *copy* of the settings and returns a new immutable
:class:`~src.gui.app_settings.AppSettings` on accept -- the caller decides
whether to apply and persist it. This keeps the dialog free of side
effects and trivially testable.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.gui.app_settings import AppSettings

_HSV_MAXIMA: tuple[int, int, int] = (179, 255, 255)
_HSV_CHANNELS: tuple[str, str, str] = ("H", "S", "V")


class SettingsDialog(QDialog):
    """Edits HSV thresholds, the output folder and the theme."""

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        """Build the dialog pre-filled with the current settings.

        Args:
            settings: Current application settings.
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self.setWindowTitle("FloodVision Settings")
        self.setModal(True)
        self._initial = settings

        self._lower = self._make_hsv_row(settings.hsv_lower)
        self._upper = self._make_hsv_row(settings.hsv_upper)

        hsv_form = QFormLayout()
        hsv_form.addRow("Lower bound (H, S, V):", _row_widget(self._lower))
        hsv_form.addRow("Upper bound (H, S, V):", _row_widget(self._upper))
        hsv_box = QGroupBox("Water detection - HSV thresholds")
        hsv_box.setLayout(hsv_form)

        self._output_edit = QLineEdit(settings.output_dir)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self._output_edit, stretch=1)
        output_row.addWidget(browse)
        output_box = QGroupBox("Output folder")
        output_box.setLayout(output_row)

        self._dark_check = QCheckBox("Dark mode")
        self._dark_check.setChecked(settings.dark_mode)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(hsv_box)
        layout.addWidget(output_box)
        layout.addWidget(self._dark_check)
        layout.addWidget(buttons)

    def result_settings(self) -> AppSettings:
        """Return a new settings snapshot reflecting the dialog state.

        Returns:
            An updated immutable :class:`AppSettings` copy.
        """
        return replace(
            self._initial,
            hsv_lower=_values(self._lower),
            hsv_upper=_values(self._upper),
            output_dir=self._output_edit.text().strip(),
            dark_mode=self._dark_check.isChecked(),
        )

    def _make_hsv_row(self, values: tuple[int, int, int]) -> list[QSpinBox]:
        """Create three spin boxes with correct OpenCV HSV ranges.

        The widget-level maxima make out-of-range values *unenterable* --
        validation by construction beats validation by dialog.

        Args:
            values: Initial ``(H, S, V)`` values.

        Returns:
            The three configured spin boxes.
        """
        boxes: list[QSpinBox] = []
        for value, maximum in zip(values, _HSV_MAXIMA):
            box = QSpinBox()
            box.setRange(0, maximum)
            box.setValue(value)
            boxes.append(box)
        return boxes

    def _browse_output(self) -> None:
        """Open a directory picker for the output folder."""
        chosen = QFileDialog.getExistingDirectory(
            self, "Select output folder", self._output_edit.text()
        )
        if chosen:
            self._output_edit.setText(chosen)

    def _validate_and_accept(self) -> None:
        """Cross-validate the fields; accept only if consistent.

        Per-field validity is enforced by the spin boxes; what remains is
        the *relationship* lower <= upper and a non-empty output path.
        """
        lower, upper = _values(self._lower), _values(self._upper)
        for channel, low, high in zip(_HSV_CHANNELS, lower, upper):
            if low > high:
                QMessageBox.warning(
                    self,
                    "Invalid HSV window",
                    f"Channel {channel}: lower bound {low} exceeds upper bound {high}.",
                )
                return
        if not self._output_edit.text().strip():
            QMessageBox.warning(
                self, "Invalid output folder", "The output folder cannot be empty."
            )
            return
        self.accept()


def _row_widget(boxes: list[QSpinBox]) -> QWidget:
    """Pack spin boxes into one horizontal widget.

    Args:
        boxes: Spin boxes to arrange.

    Returns:
        A container widget for use in a form layout.
    """
    container = QWidget()
    row = QHBoxLayout(container)
    row.setContentsMargins(0, 0, 0, 0)
    for box in boxes:
        row.addWidget(box)
    return container


def _values(boxes: list[QSpinBox]) -> tuple[int, int, int]:
    """Read three spin boxes into an int triple.

    Args:
        boxes: Exactly three spin boxes.

    Returns:
        Their values as ``(H, S, V)``.
    """
    return (boxes[0].value(), boxes[1].value(), boxes[2].value())
