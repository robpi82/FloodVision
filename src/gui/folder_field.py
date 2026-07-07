"""Folder path field with Finder/Explorer drag & drop support.

Small, reusable widget: a ``QLineEdit`` that accepts exactly one dropped
*directory*, highlights itself while a valid folder hovers over it, and
rejects files or non-local URLs. Validation happens already at
``dragEnterEvent`` time, so the OS shows the "forbidden" cursor for
invalid payloads before the user even releases the mouse -- the drop
target communicates instead of failing silently.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import QLineEdit, QWidget

from src.gui.theme import ACCENT

logger = logging.getLogger(__name__)

_HIGHLIGHT_STYLE = f"border: 2px solid {ACCENT}; border-radius: 4px;"


class FolderDropLineEdit(QLineEdit):
    """Line edit that accepts a directory dropped from the file manager.

    Signals:
        folder_dropped: Emitted with the absolute path after a valid drop.
        drop_rejected: Emitted when the dragged payload is not a folder,
            so the owner can show a helpful status message.
    """

    folder_dropped = Signal(str)
    drop_rejected = Signal()

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        """Initialise the field and enable drop handling.

        Args:
            text: Initial path text.
            parent: Optional Qt parent.
        """
        super().__init__(text, parent)
        self.setAcceptDrops(True)

    # ------------------------------------------------------------------
    # Qt drag & drop events
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        """Accept the drag only if it carries a local directory.

        Args:
            event: Qt drag-enter event.
        """
        if self._extract_directory(event) is not None:
            self.setStyleSheet(_HIGHLIGHT_STYLE)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # noqa: N802
        """Remove the highlight when the drag leaves the field.

        Args:
            event: Qt drag-leave event.
        """
        self.setStyleSheet("")
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """Apply a valid dropped directory to the field.

        Args:
            event: Qt drop event.
        """
        self.setStyleSheet("")
        directory = self._extract_directory(event)
        if directory is None:
            # Defensive double-check: enter-validation normally prevents
            # reaching this branch, but drag payloads can change mid-drag.
            logger.warning("Rejected drop: payload is not a single folder")
            self.drop_rejected.emit()
            event.ignore()
            return
        self.setText(str(directory))
        logger.info("Folder set via drag & drop: %s", directory)
        self.folder_dropped.emit(str(directory))
        event.acceptProposedAction()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_directory(event: QDragEnterEvent | QDropEvent) -> Path | None:
        """Return the dragged local directory, or ``None`` if invalid.

        Args:
            event: A drag or drop event carrying mime data.

        Returns:
            The directory path if the payload is exactly one local
            folder, otherwise ``None`` (files, URLs, multi-selection).
        """
        mime = event.mimeData()
        if not mime.hasUrls() or len(mime.urls()) != 1:
            return None
        url = mime.urls()[0]
        if not url.isLocalFile():
            return None
        path = Path(url.toLocalFile())
        return path if path.is_dir() else None
