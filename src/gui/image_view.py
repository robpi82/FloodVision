"""Tabbed image preview: Before, After, Overlay, New Flood Mask.

Contains a reusable :class:`ScalingImageLabel` that keeps the aspect
ratio on resize -- naive ``QLabel.setPixmap`` either crops or distorts,
which is unacceptable for image inspection.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QTabWidget, QWidget


class ScalingImageLabel(QLabel):
    """A label that displays a pixmap scaled to fit, keeping aspect ratio.

    The *original* pixmap is stored separately and rescaled from the
    source on every resize; rescaling an already-scaled pixmap would
    accumulate blur with each resize event.
    """

    def __init__(self, placeholder: str, parent: QWidget | None = None) -> None:
        """Initialise with a placeholder text shown while no image is set.

        Args:
            placeholder: Text displayed when no pixmap is loaded.
            parent: Optional Qt parent.
        """
        super().__init__(placeholder, parent)
        self._source: QPixmap | None = None
        self._placeholder = placeholder
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(240, 180)

    def show_image(self, path: Path) -> None:
        """Load and display an image file, or the placeholder on failure.

        Args:
            path: Image file to display.
        """
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.clear_image()
            return
        self._source = pixmap
        self._rescale()

    def clear_image(self) -> None:
        """Remove the current image and show the placeholder text."""
        self._source = None
        self.setPixmap(QPixmap())
        self.setText(self._placeholder)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt API)
        """Rescale the stored source pixmap when the widget resizes.

        Args:
            event: Qt resize event.
        """
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        """Fit the source pixmap into the current widget size."""
        if self._source is None:
            return
        self.setPixmap(
            self._source.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class ImageView(QTabWidget):
    """Central preview widget with one tab per product image."""

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
        self._labels: dict[str, ScalingImageLabel] = {}
        for key, title in self._TABS:
            label = ScalingImageLabel(placeholder=f"{title}: no image yet")
            self._labels[key] = label
            self.addTab(label, title)

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
        self._labels["before"].show_image(before_image)
        self._labels["after"].show_image(after_image)
        self._labels["overlay"].show_image(overlay)
        self._labels["new_flood"].show_image(new_flood_mask)

    def clear_all(self) -> None:
        """Reset every tab to its placeholder."""
        for label in self._labels.values():
            label.clear_image()
