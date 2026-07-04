"""Colorised, exportable log console widget.

Colour is applied through ``QTextCharFormat`` on the document cursor
rather than injected HTML: no escaping pitfalls, no whitespace collapse,
and the plain text stays trivially exportable via ``toPlainText()``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QWidget

from src.gui.log_handler import SUCCESS

#: Level -> colour; INFO stays at the theme's default text colour so it
#: remains readable in both dark ("white") and light mode.
_LEVEL_COLORS: Final[dict[int, str]] = {
    SUCCESS: "#4caf50",
    logging.WARNING: "#e0c341",
    logging.ERROR: "#e05555",
    logging.CRITICAL: "#e05555",
}


class LogConsole(QPlainTextEdit):
    """Read-only console rendering log lines in level colours."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Configure the console: read-only, bounded, unwrapped.

        Args:
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(2000)  # bounded memory on long batches
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def append_record(self, level: int, text: str) -> None:
        """Append one log line in the colour of its level.

        Args:
            level: Numeric logging level of the record.
            text: Pre-formatted log line (timestamp, level, message).
        """
        colour = self._colour_for(level)
        char_format = QTextCharFormat()
        if colour is not None:
            char_format.setForeground(QColor(colour))
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + "\n", char_format)
        self.setTextCursor(cursor)  # auto-scroll to the newest line

    def save_to_file(self, path: Path) -> None:
        """Write the current console content as plain text.

        Args:
            path: Target file path.
        """
        path.write_text(self.toPlainText(), encoding="utf-8")

    @staticmethod
    def _colour_for(level: int) -> str | None:
        """Map a logging level to its display colour.

        ERROR and above share red; unknown in-between levels fall back to
        the nearest defined bucket below them.

        Args:
            level: Numeric logging level.

        Returns:
            A hex colour string, or ``None`` for the theme default.
        """
        if level >= logging.ERROR:
            return _LEVEL_COLORS[logging.ERROR]
        return _LEVEL_COLORS.get(level)
