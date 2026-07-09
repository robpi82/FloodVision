"""Automated tests for :mod:`src.gui.app_settings`.

Focus: the cross-platform directory-reconciliation behavior added to
guard against ``gui_settings.json`` carrying another machine's absolute
paths (see the module docstring of ``app_settings.py`` for the full
root-cause explanation). Every test uses real ``tmp_path`` directories
and JSON files -- no mocking of the filesystem or of ``Path`` is
needed, since the reconciliation logic is a plain existence check.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src import config
from src.gui.app_settings import AppSettings, load_settings, save_settings


def write_settings_json(path: Path, **overrides: object) -> None:
    """Write a minimal ``gui_settings.json`` with the given field values.

    Args:
        path: Target settings file path.
        **overrides: Field values to include in the JSON document.
    """
    path.write_text(json.dumps(overrides), encoding="utf-8")


# ---------------------------------------------------------------------------
# Baseline behaviour (regression coverage for the existing contract)
# ---------------------------------------------------------------------------
class TestBaselineLoading:
    """Existing load_settings behaviour, unaffected by the directory fix."""

    def test_missing_file_returns_project_relative_defaults(
        self, tmp_path: Path
    ) -> None:
        """No settings file at all yields the plain, portable defaults."""
        settings = load_settings(tmp_path / "does_not_exist.json")
        assert settings == AppSettings()
        assert settings.before_dir == str(config.BEFORE_DATA_DIR)
        assert settings.after_dir == str(config.AFTER_DATA_DIR)
        assert settings.output_dir == str(config.OUTPUT_DATA_DIR)

    def test_corrupted_json_falls_back_to_defaults(self, tmp_path: Path) -> None:
        """Unparseable JSON must not crash startup; defaults are used."""
        settings_path = tmp_path / "gui_settings.json"
        settings_path.write_text("{not valid json", encoding="utf-8")
        assert load_settings(settings_path) == AppSettings()

    def test_hsv_and_dark_mode_load_independently_of_directories(
        self, tmp_path: Path
    ) -> None:
        """Non-directory fields are unaffected by directory reconciliation."""
        settings_path = tmp_path / "gui_settings.json"
        write_settings_json(
            settings_path,
            before_dir="/this/path/does/not/exist/anywhere",
            hsv_lower=[10, 20, 30],
            hsv_upper=[100, 200, 250],
            dark_mode=False,
        )
        settings = load_settings(settings_path)
        assert settings.hsv_lower == (10, 20, 30)
        assert settings.hsv_upper == (100, 200, 250)
        assert settings.dark_mode is False


# ---------------------------------------------------------------------------
# Cross-platform directory reconciliation (the actual fix)
# ---------------------------------------------------------------------------
class TestDirectoryReconciliation:
    """A stored directory is kept only if it exists on this machine."""

    def test_existing_custom_directory_is_preserved(self, tmp_path: Path) -> None:
        """A real, currently existing custom directory is kept verbatim."""
        custom_before = tmp_path / "my_before_images"
        custom_before.mkdir()
        settings_path = tmp_path / "gui_settings.json"
        write_settings_json(settings_path, before_dir=str(custom_before))

        settings = load_settings(settings_path)
        assert settings.before_dir == str(custom_before)

    def test_all_three_existing_custom_directories_are_preserved(
        self, tmp_path: Path
    ) -> None:
        """before_dir, after_dir and output_dir are reconciled independently."""
        before, after, output = (
            tmp_path / "before",
            tmp_path / "after",
            tmp_path / "output",
        )
        before.mkdir()
        after.mkdir()
        output.mkdir()
        settings_path = tmp_path / "gui_settings.json"
        write_settings_json(
            settings_path,
            before_dir=str(before),
            after_dir=str(after),
            output_dir=str(output),
        )

        settings = load_settings(settings_path)
        assert settings.before_dir == str(before)
        assert settings.after_dir == str(after)
        assert settings.output_dir == str(output)

    def test_nonexistent_absolute_path_falls_back_to_project_default(
        self, tmp_path: Path
    ) -> None:
        """A stored path that no longer exists is replaced, not applied."""
        stale_path = str(tmp_path / "this_directory_was_never_created")
        settings_path = tmp_path / "gui_settings.json"
        write_settings_json(settings_path, output_dir=stale_path)

        settings = load_settings(settings_path)
        assert settings.output_dir != stale_path
        assert settings.output_dir == str(config.OUTPUT_DATA_DIR)

    def test_foreign_os_style_path_falls_back_to_project_default(
        self, tmp_path: Path
    ) -> None:
        """A macOS-style path loaded elsewhere is not a real directory.

        Regression test for the reported bug, reproduced with the exact
        style of path from the report -- independent of which OS this
        test itself happens to run on.
        """
        macos_style_path = (
            "/Users/robert/Desktop/Portfolio-Projekte/"
            "FloodVision_Versions/FloodVision/data/output"
        )
        settings_path = tmp_path / "gui_settings.json"
        write_settings_json(settings_path, output_dir=macos_style_path)

        settings = load_settings(settings_path)
        assert settings.output_dir == str(config.OUTPUT_DATA_DIR)

    def test_missing_directory_key_uses_default(self, tmp_path: Path) -> None:
        """A field absent from the JSON (not merely unusable) uses default."""
        settings_path = tmp_path / "gui_settings.json"
        write_settings_json(settings_path, dark_mode=False)  # no dir keys at all

        settings = load_settings(settings_path)
        assert settings.before_dir == str(config.BEFORE_DATA_DIR)
        assert settings.after_dir == str(config.AFTER_DATA_DIR)
        assert settings.output_dir == str(config.OUTPUT_DATA_DIR)

    def test_file_path_instead_of_directory_falls_back(self, tmp_path: Path) -> None:
        """A stored path that exists but is a file, not a directory, is rejected."""
        stray_file = tmp_path / "not_a_directory.txt"
        stray_file.write_text("oops", encoding="utf-8")
        settings_path = tmp_path / "gui_settings.json"
        write_settings_json(settings_path, before_dir=str(stray_file))

        settings = load_settings(settings_path)
        assert settings.before_dir == str(config.BEFORE_DATA_DIR)

    def test_mixed_valid_and_stale_directories_are_reconciled_independently(
        self, tmp_path: Path
    ) -> None:
        """One valid and two stale fields are each resolved on their own merits."""
        valid_after = tmp_path / "real_after_folder"
        valid_after.mkdir()
        settings_path = tmp_path / "gui_settings.json"
        write_settings_json(
            settings_path,
            before_dir=str(tmp_path / "gone_before"),
            after_dir=str(valid_after),
            output_dir="/Users/someone/old_machine/output",
        )

        settings = load_settings(settings_path)
        assert settings.before_dir == str(config.BEFORE_DATA_DIR)
        assert settings.after_dir == str(valid_after)
        assert settings.output_dir == str(config.OUTPUT_DATA_DIR)


# ---------------------------------------------------------------------------
# Round trip (save then load)
# ---------------------------------------------------------------------------
class TestSaveLoadRoundTrip:
    """save_settings() followed by load_settings() preserves valid state."""

    def test_round_trip_preserves_existing_directories(self, tmp_path: Path) -> None:
        """Saving and reloading on the same machine changes nothing."""
        before, after, output = (
            tmp_path / "before",
            tmp_path / "after",
            tmp_path / "output",
        )
        before.mkdir()
        after.mkdir()
        output.mkdir()
        settings_path = tmp_path / "gui_settings.json"
        original = AppSettings(
            before_dir=str(before),
            after_dir=str(after),
            output_dir=str(output),
            hsv_lower=(50, 60, 70),
            hsv_upper=(120, 200, 220),
            dark_mode=False,
        )

        save_settings(original, settings_path)
        reloaded = load_settings(settings_path)

        assert reloaded == original

    def test_round_trip_after_directory_deletion_falls_back(
        self, tmp_path: Path
    ) -> None:
        """If a previously valid directory is later removed, it is dropped."""
        output = tmp_path / "output"
        output.mkdir()
        settings_path = tmp_path / "gui_settings.json"
        save_settings(AppSettings(output_dir=str(output)), settings_path)

        output.rmdir()  # simulate the folder disappearing (or another machine)
        reloaded = load_settings(settings_path)

        assert reloaded.output_dir == str(config.OUTPUT_DATA_DIR)


@pytest.mark.parametrize("field", ["before_dir", "after_dir", "output_dir"])
def test_each_directory_field_is_reconciled(tmp_path: Path, field: str) -> None:
    """Every one of the three directory fields goes through reconciliation.

    Args:
        tmp_path: Pytest-provided temporary directory.
        field: The ``AppSettings`` field under test.
    """
    settings_path = tmp_path / "gui_settings.json"
    write_settings_json(settings_path, **{field: "/no/such/machine/path"})

    settings = load_settings(settings_path)
    assert getattr(settings, field) == getattr(AppSettings(), field)