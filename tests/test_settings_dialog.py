"""Automated tests for :mod:`src.gui.settings_dialog`.

Focus: the detection-method selection added alongside the existing HSV,
output-folder and dark-mode controls -- specifically that the combo box
reflects the settings it was opened with, that switching it toggles the
HSV threshold box, and that ``result_settings()`` reports the selection
without disturbing unrelated fields.
"""

from __future__ import annotations

from src.gui.app_settings import (
    DETECTION_MODE_HSV,
    DETECTION_MODE_SPECTRAL,
    AppSettings,
)
from src.gui.settings_dialog import SettingsDialog


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
