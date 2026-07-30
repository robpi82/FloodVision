"""Dialog for combining individual Sentinel-2 band files into one GeoTIFF.

Bridges :func:`src.sentinel2_import.combine_sentinel2_bands_to_geotiff`
(backend -- see its module docstring for the full rationale) into the
desktop GUI: a user picks individual band files or a whole folder, the
dialog guesses each file's band code from its filename, and one click
writes a combined, georeferenced GeoTIFF straight into the Before or
After folder -- ready for a completely normal batch run, no further
steps required anywhere else in the application.
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.exceptions import FloodVisionError
from src.sentinel2_bands import SENTINEL2_BANDS
from src.sentinel2_import import combine_sentinel2_bands_to_geotiff

#: Known codes, longest first, so a code like "B8A" is tried before any
#: shorter code that might otherwise match a prefix of it.
_BAND_CODES_BY_LENGTH: tuple[str, ...] = tuple(
    sorted(SENTINEL2_BANDS, key=len, reverse=True)
)


def guess_band_code(filename: str) -> str | None:
    """Best-effort detection of a Sentinel-2 band code from a filename.

    Real Sentinel-2 filenames embed the band code as a segment, e.g.
    ``T33UUP_20230615T101031_B03_10m.jp2``. This checks each known code
    as a substring with a word-boundary-ish guard on both sides, so
    (for example) a code is not matched inside a longer alphanumeric
    run it merely happens to be a substring of. Matching is
    case-insensitive, since a user renaming or re-saving a file (e.g.
    to ``b03.tif``) is a routine, harmless variation, not a reason to
    fail detection.

    Args:
        filename: The file's name (not full path).

    Returns:
        The matched Sentinel-2 band code (in its canonical uppercase
        form, e.g. ``"B03"``), or ``None`` if no known code was found
        in the filename.
    """
    for code in _BAND_CODES_BY_LENGTH:
        pattern = rf"(?<![A-Za-z0-9]){re.escape(code)}(?![A-Za-z0-9])"
        if re.search(pattern, filename, re.IGNORECASE):
            return code
    return None


class Sentinel2ImportDialog(QDialog):
    """Combine individually-selected Sentinel-2 band files into one GeoTIFF."""

    def __init__(
        self,
        before_dir: str,
        after_dir: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import Sentinel-2 Bands")
        self.setModal(True)
        self.resize(600, 440)

        self._before_dir = before_dir
        self._after_dir = after_dir
        self._band_files: dict[str, Path] = {}

        self._target_before = QRadioButton("Before")
        self._target_after = QRadioButton("After")
        self._target_before.setChecked(True)
        target_row = QHBoxLayout()
        target_row.addWidget(self._target_before)
        target_row.addWidget(self._target_after)
        target_row.addStretch(1)

        self._filename_edit = QLineEdit("sentinel2_scene.tif")

        target_layout = QVBoxLayout()
        target_layout.addLayout(target_row)
        target_layout.addWidget(QLabel("Output file name:"))
        target_layout.addWidget(self._filename_edit)
        target_box = QGroupBox("Target")
        target_box.setLayout(target_layout)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Band", "Resolution", "File"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        add_files_button = QPushButton("Add band files...")
        add_files_button.clicked.connect(self._on_add_files)
        add_folder_button = QPushButton("Add folder...")
        add_folder_button.clicked.connect(self._on_add_folder)
        remove_button = QPushButton("Remove selected")
        remove_button.clicked.connect(self._on_remove_selected)
        table_buttons = QHBoxLayout()
        table_buttons.addWidget(add_files_button)
        table_buttons.addWidget(add_folder_button)
        table_buttons.addWidget(remove_button)
        table_buttons.addStretch(1)

        files_layout = QVBoxLayout()
        files_layout.addLayout(table_buttons)
        files_layout.addWidget(self._table)
        files_box = QGroupBox("Band files")
        files_box.setLayout(files_layout)

        self._status_label = QLabel(
            "Add band files, then choose Before or After and Combine."
        )
        self._status_label.setWordWrap(True)

        buttons = QDialogButtonBox()
        self._combine_button = buttons.addButton(
            "Combine", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self._combine_button.clicked.connect(self._on_combine)
        close_button = buttons.addButton(QDialogButtonBox.StandardButton.Close)
        close_button.clicked.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(target_box)
        layout.addWidget(files_box, stretch=1)
        layout.addWidget(self._status_label)
        layout.addWidget(buttons)

    def _on_add_files(self) -> None:
        """Let the user pick one or more individual band files explicitly."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Sentinel-2 band files",
            self._before_dir,
            "Raster files (*.tif *.tiff *.jp2);;All files (*.*)",
        )
        for path_str in paths:
            self._add_band_file(Path(path_str), warn_if_unrecognised=True)

    def _on_add_folder(self) -> None:
        """Scan a folder and add every file with a recognisable band code.

        Unlike :meth:`_on_add_files`, files the folder happens to also
        contain that carry no recognisable band code (metadata XML,
        thumbnails, etc. -- routine contents of a real ``.SAFE`` band
        folder) are skipped silently rather than warned about one by
        one; only "nothing at all was found" is surfaced.
        """
        folder = QFileDialog.getExistingDirectory(
            self, "Select folder with Sentinel-2 band files", self._before_dir
        )
        if not folder:
            return

        added = 0
        for path in sorted(Path(folder).iterdir()):
            if not path.is_file():
                continue
            if self._add_band_file(path, warn_if_unrecognised=False):
                added += 1

        if added == 0:
            self._status_label.setText(
                f"No recognisable Sentinel-2 band files found in '{folder}'."
            )
        else:
            self._status_label.setText(f"Added {added} band file(s) from '{folder}'.")

    def _add_band_file(self, path: Path, warn_if_unrecognised: bool) -> bool:
        """Detect a file's band code and add it to the table if new.

        Args:
            path: Candidate band file.
            warn_if_unrecognised: Whether to pop up a warning when no
                band code could be detected (suppressed during folder
                scans, shown for explicit file selection).

        Returns:
            ``True`` if the file was added, ``False`` if it was skipped
            (unrecognised code, or that band was already present).
        """
        code = guess_band_code(path.name)
        if code is None:
            if warn_if_unrecognised:
                QMessageBox.warning(
                    self,
                    "Unrecognised band file",
                    f"Could not detect a Sentinel-2 band code in '{path.name}'.\n"
                    "Expected a filename containing a band code such as "
                    "B03 or B11.",
                )
            return False

        if code in self._band_files:
            if warn_if_unrecognised:
                QMessageBox.warning(
                    self,
                    "Band already added",
                    f"Band {code} is already in the list "
                    f"({self._band_files[code].name}). Remove it first to "
                    "replace it.",
                )
            return False

        self._band_files[code] = path
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(code))
        resolution = SENTINEL2_BANDS[code].resolution_m
        self._table.setItem(row, 1, QTableWidgetItem(f"{resolution} m"))
        self._table.setItem(row, 2, QTableWidgetItem(str(path)))
        return True

    def _on_remove_selected(self) -> None:
        selected_rows = sorted(
            {item.row() for item in self._table.selectedItems()}, reverse=True
        )
        for row in selected_rows:
            code_item = self._table.item(row, 0)
            if code_item is not None:
                self._band_files.pop(code_item.text(), None)
            self._table.removeRow(row)

    def _on_combine(self) -> None:
        """Write the combined GeoTIFF, reporting success or failure inline."""
        if not self._band_files:
            self._status_label.setText("Add at least one band file first.")
            return

        filename = self._filename_edit.text().strip()
        if not filename:
            self._status_label.setText("Enter an output file name first.")
            return

        target_dir = Path(
            self._before_dir if self._target_before.isChecked() else self._after_dir
        )
        output_path = target_dir / filename

        try:
            combine_sentinel2_bands_to_geotiff(self._band_files, output_path)
        except (FloodVisionError, ValueError) as error:
            self._status_label.setText(f"Failed: {error}")
            return

        self._status_label.setText(f"Saved: {output_path}")
        QMessageBox.information(
            self, "Import complete", f"Combined GeoTIFF saved to:\n{output_path}"
        )
