"""Automated tests for :mod:`src.gui.settings_dialog`.

Focus: the detection-method selection added alongside the existing HSV,
output-folder and dark-mode controls -- specifically that the combo box
reflects the settings it was opened with, that switching it toggles the
HSV threshold box, and that ``result_settings()`` reports the selection
without disturbing unrelated fields.
"""

from __future__ import annotations

import pytest

from src.gui.app_settings import (
    DETECTION_MODE_HSV,
    DETECTION_MODE_SPECTRAL,
    AppSettings,
)
from src.gui.settings_dialog import SettingsDialog
from src.spectral_indices import SPECTRAL_INDEX_MNDWI, SPECTRAL_INDEX_NDWI


def test_stored_hsv_mode_is_shown_and_hsv_box_enabled(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_HSV)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    assert dialog._detection_mode_combo.currentData() == DETECTION_MODE_HSV
    assert dialog._hsv_box.isEnabled()


def test_stored_spectral_mode_is_shown_and_hsv_box_disabled(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_SPECTRAL)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    assert dialog._detection_mode_combo.currentData() == DETECTION_MODE_SPECTRAL
    assert not dialog._hsv_box.isEnabled()


def test_switching_to_spectral_disables_hsv_box(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_HSV)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    spectral_index = dialog._detection_mode_combo.findData(DETECTION_MODE_SPECTRAL)
    dialog._detection_mode_combo.setCurrentIndex(spectral_index)

    assert not dialog._hsv_box.isEnabled()


def test_switching_back_to_hsv_re_enables_hsv_box(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_SPECTRAL)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    hsv_index = dialog._detection_mode_combo.findData(DETECTION_MODE_HSV)
    dialog._detection_mode_combo.setCurrentIndex(hsv_index)

    assert dialog._hsv_box.isEnabled()


def test_result_settings_reports_selected_spectral_mode(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_HSV)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    spectral_index = dialog._detection_mode_combo.findData(DETECTION_MODE_SPECTRAL)
    dialog._detection_mode_combo.setCurrentIndex(spectral_index)

    result = dialog.result_settings()

    assert result.detection_mode == DETECTION_MODE_SPECTRAL


def test_result_settings_reports_selected_hsv_mode(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_SPECTRAL)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    hsv_index = dialog._detection_mode_combo.findData(DETECTION_MODE_HSV)
    dialog._detection_mode_combo.setCurrentIndex(hsv_index)

    result = dialog.result_settings()

    assert result.detection_mode == DETECTION_MODE_HSV


def test_detection_hint_changes_with_selection(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_HSV)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    hsv_hint = dialog._detection_hint.text()

    spectral_index = dialog._detection_mode_combo.findData(DETECTION_MODE_SPECTRAL)
    dialog._detection_mode_combo.setCurrentIndex(spectral_index)

    assert dialog._detection_hint.text() != hsv_hint
    assert "Sentinel-2" in dialog._detection_hint.text()


def test_changing_detection_mode_preserves_other_settings(qtbot) -> None:
    """Switching detection mode must not disturb unrelated settings fields."""
    settings = AppSettings(
        before_dir="/tmp/before",
        after_dir="/tmp/after",
        output_dir="/tmp/output",
        hsv_lower=(10, 20, 30),
        hsv_upper=(100, 200, 250),
        detection_mode=DETECTION_MODE_HSV,
        dark_mode=False,
    )
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    spectral_index = dialog._detection_mode_combo.findData(DETECTION_MODE_SPECTRAL)
    dialog._detection_mode_combo.setCurrentIndex(spectral_index)

    result = dialog.result_settings()

    assert result.before_dir == settings.before_dir
    assert result.after_dir == settings.after_dir
    assert result.output_dir == settings.output_dir
    assert result.hsv_lower == settings.hsv_lower
    assert result.hsv_upper == settings.hsv_upper
    assert result.dark_mode == settings.dark_mode
    assert result.detection_mode == DETECTION_MODE_SPECTRAL


# ---------------------------------------------------------------------------
# Spectral index selection (NDWI vs MNDWI)
# ---------------------------------------------------------------------------
def test_stored_spectral_index_is_shown(qtbot) -> None:
    settings = AppSettings(
        detection_mode=DETECTION_MODE_SPECTRAL,
        spectral_index=SPECTRAL_INDEX_MNDWI,
    )
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    assert dialog._spectral_index_combo.currentData() == SPECTRAL_INDEX_MNDWI


def test_spectral_index_combo_disabled_in_hsv_mode(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_HSV)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    assert not dialog._spectral_index_combo.isEnabled()


def test_spectral_index_combo_enabled_in_spectral_mode(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_SPECTRAL)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    assert dialog._spectral_index_combo.isEnabled()


def test_switching_to_spectral_enables_index_combo(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_HSV)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    spectral_position = dialog._detection_mode_combo.findData(DETECTION_MODE_SPECTRAL)
    dialog._detection_mode_combo.setCurrentIndex(spectral_position)

    assert dialog._spectral_index_combo.isEnabled()


def test_result_settings_reports_selected_spectral_index(qtbot) -> None:
    settings = AppSettings(
        detection_mode=DETECTION_MODE_SPECTRAL,
        spectral_index=SPECTRAL_INDEX_NDWI,
    )
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    mndwi_position = dialog._spectral_index_combo.findData(SPECTRAL_INDEX_MNDWI)
    dialog._spectral_index_combo.setCurrentIndex(mndwi_position)

    result = dialog.result_settings()

    assert result.spectral_index == SPECTRAL_INDEX_MNDWI


def test_hint_changes_with_spectral_index_selection(qtbot) -> None:
    settings = AppSettings(
        detection_mode=DETECTION_MODE_SPECTRAL,
        spectral_index=SPECTRAL_INDEX_NDWI,
    )
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    ndwi_hint = dialog._detection_hint.text()

    mndwi_position = dialog._spectral_index_combo.findData(SPECTRAL_INDEX_MNDWI)
    dialog._spectral_index_combo.setCurrentIndex(mndwi_position)

    assert dialog._detection_hint.text() != ndwi_hint
    assert "MNDWI" in dialog._detection_hint.text()


def test_hsv_mode_selection_is_unaffected_by_spectral_index_field(qtbot) -> None:
    """The spectral-index combo carries a value even in HSV mode, but it is
    not surfaced in the hint text while HSV is selected."""
    settings = AppSettings(
        detection_mode=DETECTION_MODE_HSV,
        spectral_index=SPECTRAL_INDEX_MNDWI,
    )
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    assert "MNDWI" not in dialog._detection_hint.text()
    assert dialog._detection_hint.text() == (
        "Use HSV detection for PNG, JPEG and standard RGB imagery."
    )


def test_changing_spectral_index_preserves_other_settings(qtbot) -> None:
    """Switching spectral index must not disturb unrelated settings fields."""
    settings = AppSettings(
        before_dir="/tmp/before",
        after_dir="/tmp/after",
        output_dir="/tmp/output",
        hsv_lower=(10, 20, 30),
        hsv_upper=(100, 200, 250),
        detection_mode=DETECTION_MODE_SPECTRAL,
        spectral_index=SPECTRAL_INDEX_NDWI,
        dark_mode=False,
    )
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    mndwi_position = dialog._spectral_index_combo.findData(SPECTRAL_INDEX_MNDWI)
    dialog._spectral_index_combo.setCurrentIndex(mndwi_position)

    result = dialog.result_settings()

    assert result.before_dir == settings.before_dir
    assert result.after_dir == settings.after_dir
    assert result.output_dir == settings.output_dir
    assert result.hsv_lower == settings.hsv_lower
    assert result.hsv_upper == settings.hsv_upper
    assert result.dark_mode == settings.dark_mode
    assert result.detection_mode == DETECTION_MODE_SPECTRAL
    assert result.spectral_index == SPECTRAL_INDEX_MNDWI


# ---------------------------------------------------------------------------
# Spectral threshold
# ---------------------------------------------------------------------------
def test_stored_threshold_is_shown(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_SPECTRAL, spectral_threshold=0.2)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    assert dialog._spectral_threshold_spin.value() == pytest.approx(0.2)


def test_threshold_spin_disabled_in_hsv_mode(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_HSV)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    assert not dialog._spectral_threshold_spin.isEnabled()


def test_threshold_spin_enabled_in_spectral_mode(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_SPECTRAL)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    assert dialog._spectral_threshold_spin.isEnabled()


def test_result_settings_reports_edited_threshold(qtbot) -> None:
    settings = AppSettings(detection_mode=DETECTION_MODE_SPECTRAL, spectral_threshold=0.1)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    dialog._spectral_threshold_spin.setValue(0.4)

    result = dialog.result_settings()

    assert result.spectral_threshold == pytest.approx(0.4)


def test_threshold_cannot_be_set_outside_valid_range(qtbot) -> None:
    """The spin box itself clamps input to [-1.0, 1.0] -- validation by construction."""
    settings = AppSettings(detection_mode=DETECTION_MODE_SPECTRAL)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    dialog._spectral_threshold_spin.setValue(5.0)

    assert dialog._spectral_threshold_spin.value() <= 1.0


def test_changing_threshold_preserves_other_settings(qtbot) -> None:
    """Editing the threshold must not disturb unrelated settings fields."""
    settings = AppSettings(
        before_dir="/tmp/before",
        after_dir="/tmp/after",
        output_dir="/tmp/output",
        hsv_lower=(10, 20, 30),
        hsv_upper=(100, 200, 250),
        detection_mode=DETECTION_MODE_SPECTRAL,
        spectral_index=SPECTRAL_INDEX_MNDWI,
        spectral_threshold=0.1,
        dark_mode=False,
    )
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)

    dialog._spectral_threshold_spin.setValue(0.5)

    result = dialog.result_settings()

    assert result.before_dir == settings.before_dir
    assert result.after_dir == settings.after_dir
    assert result.output_dir == settings.output_dir
    assert result.hsv_lower == settings.hsv_lower
    assert result.hsv_upper == settings.hsv_upper
    assert result.dark_mode == settings.dark_mode
    assert result.detection_mode == DETECTION_MODE_SPECTRAL
    assert result.spectral_index == SPECTRAL_INDEX_MNDWI
    assert result.spectral_threshold == pytest.approx(0.5)

