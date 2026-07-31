"""Tests for :mod:`src.gui.image_view`.

Focus: the fifth "Spectral Index" tab added alongside Before/After/Overlay/
New Flood Mask -- specifically that it exists, that a missing or ``None``
path falls back to the placeholder rather than crashing (the normal case
for HSV-mode results, which have no spectral index to show), and that
``clear_all`` resets it like every other tab.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from PySide6.QtGui import QImageReader

from src.gui.image_view import ImageView, ZoomableImageView


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


# ---------------------------------------------------------------------------
# Qt image allocation limit (full-resolution real-world previews)
# ---------------------------------------------------------------------------
class TestImageAllocationLimit:
    """A large but legitimate preview image must not silently fail to load.

    A full-resolution Sentinel-2 tile's preview PNG (10980 x 10980 px,
    ~345 MB decoded as RGB) exceeds Qt's default 256 MB decoded-image
    allocation limit -- a safeguard against malicious "decompression
    bomb" images, not something meant to reject this application's own
    locally-generated batch output. ``gui_main.py`` disables the limit
    at startup (``QImageReader.setAllocationLimit(0)``); these tests
    reproduce the failure and its fix at a much smaller, fast-to-write
    scale by lowering the limit instead of generating a genuinely huge
    fixture file, since the underlying mechanism is identical either way.
    """

    def test_image_exceeding_the_allocation_limit_falls_back_to_placeholder(
        self, qtbot, tmp_path: Path
    ) -> None:
        """Documents the bug class: without raising the limit, a large
        (but entirely legitimate) preview silently shows as empty."""
        image_path = tmp_path / "large.png"
        Image.fromarray(np.zeros((2000, 2000, 3), dtype=np.uint8)).save(image_path)

        original_limit = QImageReader.allocationLimit()
        QImageReader.setAllocationLimit(1)  # 1 MB -- far below this image's size
        try:
            view = ZoomableImageView(placeholder="No image yet")
            qtbot.addWidget(view)
            view.show_image(image_path)

            assert view._item is None
        finally:
            QImageReader.setAllocationLimit(original_limit)

    def test_same_image_loads_once_allocation_limit_is_raised(
        self, qtbot, tmp_path: Path
    ) -> None:
        """The actual fix: with the limit disabled (as gui_main.py does),
        the same image that failed above now loads correctly."""
        image_path = tmp_path / "large.png"
        Image.fromarray(np.zeros((2000, 2000, 3), dtype=np.uint8)).save(image_path)

        original_limit = QImageReader.allocationLimit()
        QImageReader.setAllocationLimit(1)  # reproduce the failing baseline
        QImageReader.setAllocationLimit(0)  # 0 = unlimited, matching gui_main.py
        try:
            view = ZoomableImageView(placeholder="No image yet")
            qtbot.addWidget(view)
            view.show_image(image_path)

            assert view._item is not None
        finally:
            QImageReader.setAllocationLimit(original_limit)
