"""Tests for :mod:`src.gui.image_view`.

Focus: the fifth "Spectral Index" tab added alongside Before/After/Overlay/
New Flood Mask -- specifically that it exists, that a missing or ``None``
path falls back to the placeholder rather than crashing (the normal case
for HSV-mode results, which have no spectral index to show), and that
``clear_all`` resets it like every other tab.
"""

from __future__ import annotations

from pathlib import Path

from src.gui.image_view import ImageView


def test_image_view_has_five_tabs(qtbot) -> None:
    view = ImageView()
    qtbot.addWidget(view)

    assert view.count() == 5
    assert [view.tabText(i) for i in range(view.count())] == [
        "Before",
        "After",
        "Overlay",
        "New Flood Mask",
        "Spectral Index",
    ]


def test_show_pair_with_missing_spectral_index_file_does_not_raise(
    qtbot, tmp_path: Path
) -> None:
    """A non-existent spectral-index path (the normal HSV case) must not crash.

    ``ZoomableImageView.show_image`` already falls back to its placeholder
    for any file it cannot load; this confirms the fifth tab is wired the
    same way as the other four rather than requiring the file to exist.
    """
    view = ImageView()
    qtbot.addWidget(view)

    view.show_pair(
        before_image=tmp_path / "before.png",
        after_image=tmp_path / "after.png",
        overlay=tmp_path / "overlay.png",
        new_flood_mask=tmp_path / "mask.png",
        spectral_index=tmp_path / "after_index.png",
    )

    assert view._views["spectral_index"]._item is None


def test_show_pair_without_spectral_index_argument_clears_the_tab(
    qtbot, tmp_path: Path
) -> None:
    """Omitting spectral_index entirely (default None) also clears the tab."""
    view = ImageView()
    qtbot.addWidget(view)

    view.show_pair(
        before_image=tmp_path / "before.png",
        after_image=tmp_path / "after.png",
        overlay=tmp_path / "overlay.png",
        new_flood_mask=tmp_path / "mask.png",
    )

    assert view._views["spectral_index"]._item is None


def test_clear_all_resets_the_spectral_index_tab(qtbot, tmp_path: Path) -> None:
    view = ImageView()
    qtbot.addWidget(view)

    view.show_pair(
        before_image=tmp_path / "before.png",
        after_image=tmp_path / "after.png",
        overlay=tmp_path / "overlay.png",
        new_flood_mask=tmp_path / "mask.png",
        spectral_index=tmp_path / "after_index.png",
    )
    view.clear_all()

    assert view._views["spectral_index"]._item is None
