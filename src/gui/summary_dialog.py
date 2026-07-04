"""End-of-batch summary dialog with quick access to the output folder."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.batch_processor import BatchResult


class SummaryDialog(QDialog):
    """Shows the batch outcome and offers to open the output folder."""

    def __init__(
        self,
        result: BatchResult,
        output_dir: Path,
        runtime_seconds: float,
        cancelled: bool,
        parent: QWidget | None = None,
    ) -> None:
        """Build the dialog from the finished batch data.

        Args:
            result: The (possibly partial) batch result.
            output_dir: Folder containing the generated products.
            runtime_seconds: Wall-clock runtime of the whole batch.
            cancelled: Whether the user cancelled the run.
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._output_dir = output_dir
        self.setWindowTitle("Batch cancelled" if cancelled else "Batch finished")
        self.setModal(True)

        form = QFormLayout()
        for caption, value in (
            ("Processed images", str(len(result.records))),
            ("Successful pairs", str(len(result.successful))),
            ("Failed pairs", str(len(result.failed))),
            ("Output folder", str(output_dir)),
            ("Runtime", f"{runtime_seconds:.1f} s"),
        ):
            label = QLabel(value)
            label.setTextInteractionFlags(
                label.textInteractionFlags()
                | label.textInteractionFlags().TextSelectableByMouse
            )
            form.addRow(f"{caption}:", label)

        open_button = QPushButton("Open Output Folder")
        open_button.clicked.connect(self._open_output_folder)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.addButton(open_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _open_output_folder(self) -> None:
        """Reveal the output folder in the platform's file manager.

        ``QDesktopServices`` delegates to the OS (Explorer, Finder,
        xdg-open) -- the portable way to open folders from Qt.
        """
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_dir)))
