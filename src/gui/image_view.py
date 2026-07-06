"""Tabbed image preview with professional zoom, pan and linked views.

v0.7 upgrades the viewer to full image-tool behaviour:

* plain mouse-wheel zoom, anchored under the cursor,
* left-drag panning (``ScrollHandDrag``),
* double click = Fit to Window,
* **linked views**: zooming or panning one tab mirrors the exact
  transform and scroll position onto the other three, so switching
  Before/After compares the identical image region -- the core visual
  workflow of change detection,
* adaptive pixmap filtering: smooth interpolation while zoomed out,
  crisp nearest-neighbour pixels beyond 200 % so masks stay inspectable
  and rendering stays fast on large images.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPainter, QPixmap, QResizeEvent, QWheelEvent
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
#: Above this scale the pixmap switches to nearest-neighbour rendering:
#: smooth interpolation would blur the very pixels the user zoomed in
#: to inspect, and is markedly slower at high magnification.
_SMOOTH_LIMIT: Final[float] = 2.0


class ZoomableImageView(QGraphicsView):
    """Single-image viewer with zoom, pan and fit-to-window.

    Two modes: *fit* (default) keeps the image fitted on every resize;
    any manual zoom switches to *manual* mode with a fixed scale until
    the user chooses Fit again (button, menu or double click).

    Signals:
        view_transformed: Emitted after a **user interaction** changed
            this view (wheel zoom, double-click fit, drag pan). The
            programmatic API (:meth:`zoom_in` etc.) intentionally does
            not emit -- the owning :class:`ImageView` broadcasts those
            itself, which keeps the sync logic loop-free.
    """

    view_transformed = Signal()

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
        # Drag panning moves the scrollbars; forwarding their changes lets
        # the owner mirror the pan onto the linked sibling views.
        self.horizontalScrollBar().valueChanged.connect(self._emit_transformed)
        self.verticalScrollBar().valueChanged.connect(self._emit_transformed)
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
        else:
            self._update_pixmap_mode()

    def clear_image(self) -> None:
        """Remove the current image and show the placeholder text."""
        self._item = None
        self._show_placeholder()

    # ------------------------------------------------------------------
    # Zoom API (programmatic -- does not emit view_transformed)
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
            self._update_pixmap_mode()

    def reset_zoom(self) -> None:
        """Show the image at its native 1:1 pixel scale (manual mode)."""
        self._fit_mode = False
        self.resetTransform()
        self._update_pixmap_mode()

    @property
    def current_scale(self) -> float:
        """Current magnification (1.0 = native pixel size)."""
        return self.transform().m11()

    @property
    def is_fit_mode(self) -> bool:
        """Whether the view currently follows fit-to-window."""
        return self._fit_mode

    def copy_view_state(self, source: "ZoomableImageView") -> None:
        """Mirror another view's transform, mode and scroll position.

        Encapsulates the linked-view synchronisation so the owning tab
        widget never touches private state of its children.

        Args:
            source: The view whose state is copied onto this one.
        """
        self._fit_mode = source.is_fit_mode
        self.setTransform(source.transform())
        self.horizontalScrollBar().setValue(source.horizontalScrollBar().value())
        self.verticalScrollBar().setValue(source.verticalScrollBar().value())
        self._update_pixmap_mode()

    # ------------------------------------------------------------------
    # Qt events (user interaction -- emits view_transformed)
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
        """Zoom with the plain mouse wheel, anchored under the cursor.

        Scrolling the canvas by wheel is pointless in an image viewer --
        drag panning covers navigation -- so the wheel is dedicated to
        zoom, matching the convention of GIS and image tools.

        Args:
            event: Qt wheel event.
        """
        if self._item is None:
            event.ignore()
            return
        self._apply_zoom(_ZOOM_STEP if event.angleDelta().y() > 0 else 1.0 / _ZOOM_STEP)
        self.view_transformed.emit()
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Double click resets the image to fit-to-window.

        Args:
            event: Qt mouse event.
        """
        if event.button() is Qt.MouseButton.LeftButton and self._item is not None:
            self.fit_to_window()
            self.view_transformed.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

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
        if not _MIN_SCALE <= self.current_scale * factor <= _MAX_SCALE:
            return
        self.scale(factor, factor)
        self._update_pixmap_mode()

    def _update_pixmap_mode(self) -> None:
        """Pick smooth vs. crisp pixmap filtering for the current scale."""
        if self._item is None:
            return
        mode = (
            Qt.TransformationMode.SmoothTransformation
            if self.current_scale <= _SMOOTH_LIMIT
            else Qt.TransformationMode.FastTransformation
        )
        self._item.setTransformationMode(mode)

    def _emit_transformed(self) -> None:
        """Forward scrollbar movement (drag pan) as a view change."""
        if self._item is not None:
            self.view_transformed.emit()

    def _show_placeholder(self) -> None:
        """Render the placeholder text into the empty scene."""
        self._scene.clear()
        self._item = None
        text = self._scene.addText(self._placeholder)
        text.setDefaultTextColor(Qt.GlobalColor.gray)
        self._scene.setSceneRect(text.boundingRect())


class ImageView(QTabWidget):
    """Central preview widget: four zoomable tabs, kept in lockstep.

    Signals:
        zoom_changed: ``(scale, fit_mode)`` after any zoom/pan change,
            for a zoom indicator in the owning window.
    """

    zoom_changed = Signal(float, bool)

    _TABS: tuple[tuple[str, str], ...] = (
        ("before", "Before"),
        ("after", "After"),
        ("overlay", "Overlay"),
        ("new_flood", "New Flood Mask"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the four preview tabs and wire the link-sync.

        Args:
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._views: dict[str, ZoomableImageView] = {}
        self._syncing = False
        for key, title in self._TABS:
            view = ZoomableImageView(placeholder=f"{title}: no image yet")
            view.view_transformed.connect(lambda v=view: self._on_view_transformed(v))
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
        self._syncing = True
        try:
            self._views["before"].show_image(before_image)
            self._views["after"].show_image(after_image)
            self._views["overlay"].show_image(overlay)
            self._views["new_flood"].show_image(new_flood_mask)
        finally:
            self._syncing = False
        self._emit_zoom_changed()

    def clear_all(self) -> None:
        """Reset every tab to its placeholder."""
        self._syncing = True
        try:
            for view in self._views.values():
                view.clear_image()
        finally:
            self._syncing = False

    # ------------------------------------------------------------------
    # Broadcast zoom API (toolbar / menu)
    # ------------------------------------------------------------------
    def zoom_in(self) -> None:
        """Zoom all tabs in by one step."""
        self._broadcast("zoom_in")

    def zoom_out(self) -> None:
        """Zoom all tabs out by one step."""
        self._broadcast("zoom_out")

    def fit_to_window(self) -> None:
        """Fit all tabs to their viewports."""
        self._broadcast("fit_to_window")

    def reset_zoom(self) -> None:
        """Set all tabs to native 1:1 scale (Actual Size)."""
        self._broadcast("reset_zoom")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _broadcast(self, method_name: str) -> None:
        """Invoke one zoom method on every tab, then report the state.

        Args:
            method_name: Name of the :class:`ZoomableImageView` method.
        """
        self._syncing = True
        try:
            for view in self._views.values():
                getattr(view, method_name)()
        finally:
            self._syncing = False
        self._emit_zoom_changed()

    def _on_view_transformed(self, source: ZoomableImageView) -> None:
        """Mirror a user interaction from one tab onto the other three.

        The ``_syncing`` guard breaks the feedback loop: copying state
        moves the siblings' scrollbars, which would otherwise re-enter
        this slot forever.

        Args:
            source: The view the user interacted with.
        """
        if self._syncing:
            return
        self._syncing = True
        try:
            for view in self._views.values():
                if view is not source:
                    view.copy_view_state(source)
        finally:
            self._syncing = False
        self._emit_zoom_changed()

    def _emit_zoom_changed(self) -> None:
        """Publish the current magnification of the linked views."""
        reference = self._views["before"]
        self.zoom_changed.emit(reference.current_scale, reference.is_fit_mode)
