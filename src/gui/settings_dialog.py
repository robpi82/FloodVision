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
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.gui.app_settings import (
    DETECTION_MODE_HSV,
    DETECTION_MODE_SPECTRAL,
    AppSettings,
)
from src.spectral_indices import SPECTRAL_INDEX_MNDWI, SPECTRAL_INDEX_NDWI

_HSV_MAXIMA: tuple[int, int, int] = (179, 255, 255)
_HSV_CHANNELS: tuple[str, str, str] = ("H", "S", "V")

_HSV_HINT: str = "Use HSV detection for PNG, JPEG and standard RGB imagery."
_SPECTRAL_HINT_BY_INDEX: dict[str, str] = {
    SPECTRAL_INDEX_NDWI: (
        "Use spectral detection for compatible multispectral Sentinel-2 "
        "GeoTIFF files. NDWI compares Green and Near-Infrared (B03/B08) "
        "and is well suited to open water."
    ),
    SPECTRAL_INDEX_MNDWI: (
        "Use spectral detection for compatible multispectral Sentinel-2 "
        "GeoTIFF files. MNDWI compares Green and Short-Wave Infrared "
        "(B03/B11) and is more robust against turbid water and built-up areas."
    ),
}


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

        self._detection_mode_combo = QComboBox()
        self._detection_mode_combo.addItem(
            "HSV color detection",
            DETECTION_MODE_HSV,
        )
        self._detection_mode_combo.addItem(
            "Sentinel-2 spectral detection",
            DETECTION_MODE_SPECTRAL,
        )
        index = self._detection_mode_combo.findData(settings.detection_mode)
        if index >= 0:
            self._detection_mode_combo.setCurrentIndex(index)
        self._detection_mode_combo.currentIndexChanged.connect(
            self._update_detection_controls
        )

        self._detection_hint = QLabel()
        self._detection_hint.setWordWrap(True)

        self._spectral_index_combo = QComboBox()
        self._spectral_index_combo.addItem(
            "NDWI (Green / NIR)",
            SPECTRAL_INDEX_NDWI,
        )
        self._spectral_index_combo.addItem(
            "MNDWI (Green / SWIR)",
            SPECTRAL_INDEX_MNDWI,
        )
        spectral_index_position = self._spectral_index_combo.findData(
            settings.spectral_index
        )
        if spectral_index_position >= 0:
            self._spectral_index_combo.setCurrentIndex(spectral_index_position)
        self._spectral_index_combo.currentIndexChanged.connect(
            self._update_detection_controls
        )

        detection_form = QFormLayout()
        detection_form.addRow("Detection method:", self._detection_mode_combo)
        detection_form.addRow("Spectral index:", self._spectral_index_combo)
        detection_form.addRow(self._detection_hint)
        detection_box = QGroupBox("Water detection method")
        detection_box.setLayout(detection_form)

        self._lower = self._make_hsv_row(settings.hsv_lower)
        self._upper = self._make_hsv_row(settings.hsv_upper)

        hsv_form = QFormLayout()
        hsv_form.addRow("Lower bound (H, S, V):", _row_widget(self._lower))
        hsv_form.addRow("Upper bound (H, S, V):", _row_widget(self._upper))
        self._hsv_box = QGroupBox("Water detection - HSV thresholds")
        self._hsv_box.setLayout(hsv_form)

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
        layout.addWidget(detection_box)
        layout.addWidget(self._hsv_box)
        layout.addWidget(output_box)
        layout.addWidget(self._dark_check)
        layout.addWidget(buttons)

        self._update_detection_controls()

    def result_settings(self) -> AppSettings:
        """Return a new settings snapshot reflecting the dialog state.

        Returns:
            An updated immutable :class:`AppSettings` copy.
        """
        return replace(
            self._initial,
            detection_mode=self._detection_mode_combo.currentData(),
            spectral_index=self._spectral_index_combo.currentData(),
            hsv_lower=_values(self._lower),
            hsv_upper=_values(self._upper),
            output_dir=self._output_edit.text().strip(),
            dark_mode=self._dark_check.isChecked(),
        )

    def _update_detection_controls(self) -> None:
        """Enable/disable the HSV box and spectral-index combo; update the hint.

        The HSV thresholds are meaningless in spectral mode and the
        spectral-index choice is meaningless in HSV mode, so each is
        disabled rather than hidden -- the user can still see the current
        value, just not edit it, and nothing is lost when switching back.
        """
        is_hsv = self._detection_mode_combo.currentData() == DETECTION_MODE_HSV
        self._hsv_box.setEnabled(is_hsv)
        self._spectral_index_combo.setEnabled(not is_hsv)
        if is_hsv:
            self._detection_hint.setText(_HSV_HINT)
        else:
            spectral_index = self._spectral_index_combo.currentData()
            self._detection_hint.setText(_SPECTRAL_HINT_BY_INDEX[spectral_index])

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
