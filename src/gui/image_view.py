"""Tabbed image preview with professional zoom and pan.

v0.6.1 replaces the label-based preview with ``QGraphicsView`` -- Qt's
canonical widget for zoomable, pannable image display. Each tab hosts a
:class:`ZoomableImageView`; zoom commands are broadcast to *all* tabs so
Before/After/Overlay stay at the same magnification, which is exactly
what visual comparison needs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QTabWidget,
    QWidget,
)

_ZOOM_STEP: Final[float] = 1.25
_MIN_SCALE: Final[float] = 0.05
_MAX_SCALE: Final[float] = 40.0


class ZoomableImageView(QGraphicsView):
    """Single-image viewer with zoom, pan and fit-to-window.

    Two modes: *fit* (default) keeps the image fitted on every resize;
    any manual zoom switches to *manual* mode with a fixed scale until
    the user chooses Fit again. Panning works by mouse drag
    (``ScrollHandDrag``), zooming additionally via Ctrl + mouse wheel.
    """

    def __init__(self, placeholder: str, parent: QWidget | None = None) -> None:
        """Create an empty viewer showing a placeholder text.

        Args:
            placeholder: Text displayed while no image is loaded.
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._placeholder = placeholder
        self._scene = QGraphicsScene(self)
        self._item: QGraphicsPixmapItem | None = None
        self._fit_mode = True

        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMinimumSize(240, 180)
        self._show_placeholder()

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------
    def show_image(self, path: Path) -> None:
        """Load and display an image file, or the placeholder on failure.

        Keeps the current mode: in fit mode the new image is fitted, in
        manual mode the current magnification is preserved so the user
        can step through locations at a fixed zoom level.

        Args:
            path: Image file to display.
        """
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.clear_image()
            return
        self._scene.clear()
        self._item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(self._item.boundingRect())
        if self._fit_mode:
            self.fit_to_window()

    def clear_image(self) -> None:
        """Remove the current image and show the placeholder text."""
        self._item = None
        self._show_placeholder()

    # ------------------------------------------------------------------
    # Zoom API
    # ------------------------------------------------------------------
    def zoom_in(self) -> None:
        """Magnify by one step (switches to manual mode)."""
        self._apply_zoom(_ZOOM_STEP)

    def zoom_out(self) -> None:
        """Shrink by one step (switches to manual mode)."""
        self._apply_zoom(1.0 / _ZOOM_STEP)

    def fit_to_window(self) -> None:
        """Fit the whole image into the viewport and stay fitted."""
        self._fit_mode = True
        if self._item is not None:
            self.fitInView(self._item, Qt.AspectRatioMode.KeepAspectRatio)

    def reset_zoom(self) -> None:
        """Show the image at its native 1:1 pixel scale (manual mode)."""
        self._fit_mode = False
        self.resetTransform()

    # ------------------------------------------------------------------
    # Qt events
    # ------------------------------------------------------------------
    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt API)
        """Re-fit on resize while in fit mode.

        Args:
            event: Qt resize event.
        """
        super().resizeEvent(event)
        if self._fit_mode:
            self.fit_to_window()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 (Qt API)
        """Ctrl + wheel zooms; plain wheel scrolls as usual.

        Args:
            event: Qt wheel event.
        """
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._apply_zoom(
                _ZOOM_STEP if event.angleDelta().y() > 0 else 1.0 / _ZOOM_STEP
            )
            event.accept()
            return
        super().wheelEvent(event)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _apply_zoom(self, factor: float) -> None:
        """Scale the view by ``factor``, clamped to sane limits.

        Args:
            factor: Multiplicative zoom factor.
        """
        if self._item is None:
            return
        self._fit_mode = False
        current = self.transform().m11()  # horizontal scale component
        if not _MIN_SCALE <= current * factor <= _MAX_SCALE:
            return
        self.scale(factor, factor)

    def _show_placeholder(self) -> None:
        """Render the placeholder text into the empty scene."""
        self._scene.clear()
        text = self._scene.addText(self._placeholder)
        text.setDefaultTextColor(Qt.GlobalColor.gray)
        self._scene.setSceneRect(text.boundingRect())


class ImageView(QTabWidget):
    """Central preview widget with one zoomable tab per product image."""

    _TABS: tuple[tuple[str, str], ...] = (
        ("before", "Before"),
        ("after", "After"),
        ("overlay", "Overlay"),
        ("new_flood", "New Flood Mask"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the four preview tabs.

        Args:
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._views: dict[str, ZoomableImageView] = {}
        for key, title in self._TABS:
            view = ZoomableImageView(placeholder=f"{title}: no image yet")
            self._views[key] = view
            self.addTab(view, title)

    def show_pair(
        self,
        before_image: Path,
        after_image: Path,
        overlay: Path,
        new_flood_mask: Path,
    ) -> None:
        """Display all four images of one processed pair.

        Args:
            before_image: Original pre-event image.
            after_image: Original post-event image.
            overlay: Generated overlay product.
            new_flood_mask: Generated red-on-black change product.
        """
        self._views["before"].show_image(before_image)
        self._views["after"].show_image(after_image)
        self._views["overlay"].show_image(overlay)
        self._views["new_flood"].show_image(new_flood_mask)

    def clear_all(self) -> None:
        """Reset every tab to its placeholder."""
        for view in self._views.values():
            view.clear_image()

    # Zoom commands are broadcast so all tabs share one magnification --
    # switching Before/After at identical zoom is the comparison workflow.
    def zoom_in(self) -> None:
        """Zoom all tabs in by one step."""
        for view in self._views.values():
            view.zoom_in()

    def zoom_out(self) -> None:
        """Zoom all tabs out by one step."""
        for view in self._views.values():
            view.zoom_out()

    def fit_to_window(self) -> None:
        """Fit all tabs to their viewports."""
        for view in self._views.values():
            view.fit_to_window()

    def reset_zoom(self) -> None:
        """Set all tabs to native 1:1 scale."""
        for view in self._views.values():
            view.reset_zoom()
