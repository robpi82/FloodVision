"""Tests for :mod:`src.gui.sentinel2_import_dialog`.

``QMessageBox`` and ``QFileDialog`` are mocked throughout: both are
modal/blocking in real use, which would hang an automated test that
doesn't drive them interactively. Mocking them also lets these tests
assert exactly which dialog was shown (or wasn't) for a given
situation, which is the thing actually worth verifying here.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin

from src.gui.sentinel2_import_dialog import Sentinel2ImportDialog, guess_band_code

UTM32 = "EPSG:32632"


def write_band(
    path: Path, width: int, height: int, pixel_size: float, value: int
) -> None:
    """Write a single-band GeoTIFF standing in for a Sentinel-2 band file."""
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=1,
        dtype="uint16",
        crs=UTM32,
        transform=from_origin(699960.0, 5300040.0, pixel_size, pixel_size),
    ) as dataset:
        dataset.write(np.full((height, width), value, dtype=np.uint16), 1)


# ---------------------------------------------------------------------------
# Band-code detection (pure function, no Qt involved)
# ---------------------------------------------------------------------------
class TestGuessBandCode:
    def test_detects_band_code_in_realistic_filename(self) -> None:
        assert (
            guess_band_code("T33UUP_20230615T101031_B03_10m.jp2") == "B03"
        )

    def test_detects_20m_band_code(self) -> None:
        assert guess_band_code("T33UUP_20230615T101031_B11_20m.jp2") == "B11"

    def test_detects_alphanumeric_band_code(self) -> None:
        assert guess_band_code("T33UUP_20230615T101031_B8A_20m.jp2") == "B8A"

    def test_returns_none_for_unrelated_filename(self) -> None:
        assert guess_band_code("MTD_MSIL2A.xml") is None

    def test_does_not_match_a_code_inside_a_longer_alphanumeric_run(self) -> None:
        """A band code embedded in an unrelated longer token must not match."""
        assert guess_band_code("XB03X_report.pdf") is None


# ---------------------------------------------------------------------------
# Dialog construction and default state
# ---------------------------------------------------------------------------
def test_dialog_starts_with_empty_table_and_before_selected(qtbot, tmp_path) -> None:
    dialog = Sentinel2ImportDialog(
        before_dir=str(tmp_path / "before"), after_dir=str(tmp_path / "after")
    )
    qtbot.addWidget(dialog)

    assert dialog._table.rowCount() == 0
    assert dialog._target_before.isChecked()
    assert not dialog._target_after.isChecked()


# ---------------------------------------------------------------------------
# Adding band files
# ---------------------------------------------------------------------------
class TestAddBandFile:
    def test_recognised_file_is_added_to_table_and_dict(
        self, qtbot, tmp_path: Path
    ) -> None:
        write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100)
        dialog = Sentinel2ImportDialog(
            before_dir=str(tmp_path), after_dir=str(tmp_path)
        )
        qtbot.addWidget(dialog)

        added = dialog._add_band_file(tmp_path / "b03.tif", warn_if_unrecognised=True)

        assert added is True
        assert dialog._table.rowCount() == 1
        assert dialog._band_files["B03"] == tmp_path / "b03.tif"
        assert dialog._table.item(0, 0).text() == "B03"
        assert dialog._table.item(0, 1).text() == "10 m"

    def test_unrecognised_file_warns_when_explicitly_selected(
        self, qtbot, tmp_path: Path
    ) -> None:
        (tmp_path / "metadata.xml").write_text("not a band file")
        dialog = Sentinel2ImportDialog(
            before_dir=str(tmp_path), after_dir=str(tmp_path)
        )
        qtbot.addWidget(dialog)

        with patch(
            "src.gui.sentinel2_import_dialog.QMessageBox.warning"
        ) as mock_warning:
            added = dialog._add_band_file(
                tmp_path / "metadata.xml", warn_if_unrecognised=True
            )

        assert added is False
        assert dialog._table.rowCount() == 0
        mock_warning.assert_called_once()

    def test_unrecognised_file_is_silently_skipped_during_folder_scan(
        self, qtbot, tmp_path: Path
    ) -> None:
        (tmp_path / "metadata.xml").write_text("not a band file")
        dialog = Sentinel2ImportDialog(
            before_dir=str(tmp_path), after_dir=str(tmp_path)
        )
        qtbot.addWidget(dialog)

        with patch(
            "src.gui.sentinel2_import_dialog.QMessageBox.warning"
        ) as mock_warning:
            added = dialog._add_band_file(
                tmp_path / "metadata.xml", warn_if_unrecognised=False
            )

        assert added is False
        mock_warning.assert_not_called()

    def test_duplicate_band_is_rejected(self, qtbot, tmp_path: Path) -> None:
        write_band(tmp_path / "b03_a.tif", 10, 10, 10.0, 100)
        write_band(tmp_path / "b03_b.tif", 10, 10, 10.0, 200)
        dialog = Sentinel2ImportDialog(
            before_dir=str(tmp_path), after_dir=str(tmp_path)
        )
        qtbot.addWidget(dialog)

        dialog._add_band_file(tmp_path / "b03_a.tif", warn_if_unrecognised=True)
        with patch("src.gui.sentinel2_import_dialog.QMessageBox.warning"):
            added_again = dialog._add_band_file(
                tmp_path / "b03_b.tif", warn_if_unrecognised=True
            )

        assert added_again is False
        assert dialog._table.rowCount() == 1
        # The original file must still be the one on record, not overwritten.
        assert dialog._band_files["B03"] == tmp_path / "b03_a.tif"


# ---------------------------------------------------------------------------
# Removing band files
# ---------------------------------------------------------------------------
def test_remove_selected_clears_row_and_dict_entry(qtbot, tmp_path: Path) -> None:
    write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100)
    write_band(tmp_path / "b08.tif", 10, 10, 10.0, 200)
    dialog = Sentinel2ImportDialog(before_dir=str(tmp_path), after_dir=str(tmp_path))
    qtbot.addWidget(dialog)
    dialog._add_band_file(tmp_path / "b03.tif", warn_if_unrecognised=True)
    dialog._add_band_file(tmp_path / "b08.tif", warn_if_unrecognised=True)

    dialog._table.selectRow(0)
    dialog._on_remove_selected()

    assert dialog._table.rowCount() == 1
    assert "B03" not in dialog._band_files
    assert "B08" in dialog._band_files


# ---------------------------------------------------------------------------
# Combining
# ---------------------------------------------------------------------------
class TestCombine:
    def test_successful_combine_writes_file_and_reports_success(
        self, qtbot, tmp_path: Path
    ) -> None:
        write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100)
        write_band(tmp_path / "b08.tif", 10, 10, 10.0, 50)
        before_dir = tmp_path / "before"
        before_dir.mkdir()
        dialog = Sentinel2ImportDialog(
            before_dir=str(before_dir), after_dir=str(tmp_path / "after")
        )
        qtbot.addWidget(dialog)
        dialog._add_band_file(tmp_path / "b03.tif", warn_if_unrecognised=True)
        dialog._add_band_file(tmp_path / "b08.tif", warn_if_unrecognised=True)
        dialog._filename_edit.setText("scene.tif")

        with patch("src.gui.sentinel2_import_dialog.QMessageBox.information"):
            dialog._on_combine()

        assert (before_dir / "scene.tif").is_file()
        assert "Saved" in dialog._status_label.text()

    def test_combine_targets_after_folder_when_selected(
        self, qtbot, tmp_path: Path
    ) -> None:
        write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100)
        after_dir = tmp_path / "after"
        after_dir.mkdir()
        dialog = Sentinel2ImportDialog(
            before_dir=str(tmp_path / "before"), after_dir=str(after_dir)
        )
        qtbot.addWidget(dialog)
        dialog._add_band_file(tmp_path / "b03.tif", warn_if_unrecognised=True)
        dialog._target_after.setChecked(True)
        dialog._filename_edit.setText("scene.tif")

        with patch("src.gui.sentinel2_import_dialog.QMessageBox.information"):
            dialog._on_combine()

        assert (after_dir / "scene.tif").is_file()

    def test_combine_without_band_files_shows_inline_message_not_a_popup(
        self, qtbot, tmp_path: Path
    ) -> None:
        dialog = Sentinel2ImportDialog(
            before_dir=str(tmp_path), after_dir=str(tmp_path)
        )
        qtbot.addWidget(dialog)

        with patch(
            "src.gui.sentinel2_import_dialog.QMessageBox.information"
        ) as mock_info:
            dialog._on_combine()

        mock_info.assert_not_called()
        assert "Add at least one band file" in dialog._status_label.text()

    def test_combine_with_empty_filename_shows_inline_message(
        self, qtbot, tmp_path: Path
    ) -> None:
        write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100)
        dialog = Sentinel2ImportDialog(
            before_dir=str(tmp_path), after_dir=str(tmp_path)
        )
        qtbot.addWidget(dialog)
        dialog._add_band_file(tmp_path / "b03.tif", warn_if_unrecognised=True)
        dialog._filename_edit.setText("")

        dialog._on_combine()

        assert "Enter an output file name" in dialog._status_label.text()

    def test_combine_failure_is_shown_inline_not_as_a_crash(
        self, qtbot, tmp_path: Path
    ) -> None:
        """A domain-level failure (mismatched CRS) surfaces in the status
        label instead of propagating as an unhandled exception."""
        write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100)
        with rasterio.open(
            tmp_path / "b08.tif",
            "w",
            driver="GTiff",
            width=10,
            height=10,
            count=1,
            dtype="uint16",
            crs="EPSG:32633",  # different UTM zone on purpose
            transform=from_origin(699960.0, 5300040.0, 10.0, 10.0),
        ) as dataset:
            dataset.write(np.full((10, 10), 200, dtype=np.uint16), 1)

        dialog = Sentinel2ImportDialog(
            before_dir=str(tmp_path), after_dir=str(tmp_path)
        )
        qtbot.addWidget(dialog)
        dialog._add_band_file(tmp_path / "b03.tif", warn_if_unrecognised=True)
        dialog._add_band_file(tmp_path / "b08.tif", warn_if_unrecognised=True)
        dialog._filename_edit.setText("scene.tif")

        dialog._on_combine()

        assert dialog._status_label.text().startswith("Failed:")
        assert not (tmp_path / "scene.tif").is_file()


# ---------------------------------------------------------------------------
# Folder scanning (QFileDialog mocked)
# ---------------------------------------------------------------------------
def test_add_folder_adds_all_recognised_files_and_skips_the_rest(
    qtbot, tmp_path: Path
) -> None:
    band_dir = tmp_path / "R10m"
    band_dir.mkdir()
    write_band(band_dir / "T33UUP_B03_10m.tif", 10, 10, 10.0, 100)
    write_band(band_dir / "T33UUP_B08_10m.tif", 10, 10, 10.0, 200)
    (band_dir / "MTD.xml").write_text("not a band file")

    dialog = Sentinel2ImportDialog(before_dir=str(tmp_path), after_dir=str(tmp_path))
    qtbot.addWidget(dialog)

    with patch(
        "src.gui.sentinel2_import_dialog.QFileDialog.getExistingDirectory",
        return_value=str(band_dir),
    ):
        dialog._on_add_folder()

    assert dialog._table.rowCount() == 2
    assert set(dialog._band_files) == {"B03", "B08"}
    assert "Added 2 band file(s)" in dialog._status_label.text()


def test_add_folder_reports_when_nothing_recognisable_found(
    qtbot, tmp_path: Path
) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    (empty_dir / "MTD.xml").write_text("not a band file")

    dialog = Sentinel2ImportDialog(before_dir=str(tmp_path), after_dir=str(tmp_path))
    qtbot.addWidget(dialog)

    with patch(
        "src.gui.sentinel2_import_dialog.QFileDialog.getExistingDirectory",
        return_value=str(empty_dir),
    ):
        dialog._on_add_folder()

    assert dialog._table.rowCount() == 0
    assert "No recognisable" in dialog._status_label.text()


def test_add_folder_does_nothing_when_dialog_is_cancelled(
    qtbot, tmp_path: Path
) -> None:
    dialog = Sentinel2ImportDialog(before_dir=str(tmp_path), after_dir=str(tmp_path))
    qtbot.addWidget(dialog)

    with patch(
        "src.gui.sentinel2_import_dialog.QFileDialog.getExistingDirectory",
        return_value="",  # Qt returns "" when the user cancels
    ):
        dialog._on_add_folder()

    assert dialog._table.rowCount() == 0


def test_add_files_adds_each_selected_path(qtbot, tmp_path: Path) -> None:
    write_band(tmp_path / "b03.tif", 10, 10, 10.0, 100)
    write_band(tmp_path / "b08.tif", 10, 10, 10.0, 200)

    dialog = Sentinel2ImportDialog(before_dir=str(tmp_path), after_dir=str(tmp_path))
    qtbot.addWidget(dialog)

    with patch(
        "src.gui.sentinel2_import_dialog.QFileDialog.getOpenFileNames",
        return_value=([str(tmp_path / "b03.tif"), str(tmp_path / "b08.tif")], ""),
    ):
        dialog._on_add_files()

    assert dialog._table.rowCount() == 2
    assert set(dialog._band_files) == {"B03", "B08"}
