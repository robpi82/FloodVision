"""Dark/light theme application for the FloodVision GUI.

One function, one responsibility: style the whole ``QApplication``.
Widgets never hardcode colours; re-theming at runtime therefore only
requires calling :func:`apply_theme` again.
"""

from __future__ import annotations

from typing import Final

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

#: Brand accent used for highlights and the primary action button.
ACCENT: Final[str] = "#E9A542"

_BUTTON_STYLE: Final[str] = f"""
QPushButton#primaryButton {{
    background-color: {ACCENT};
    color: #1b1b1b;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
}}
QPushButton#primaryButton:disabled {{
    background-color: #7a6a4a;
    color: #3a3a3a;
}}
QPushButton {{
    border-radius: 6px;
    padding: 8px 12px;
}}
QPushButton:disabled {{
    color: #6f6f6f;
}}
QLabel#appTitle {{ font-size: 20px; font-weight: bold; }}
QLabel#appSubtitle {{ color: gray; }}
QLabel#logoBadge {{
    background-color: {ACCENT};
    color: #1b1b1b;
    font-size: 22px;
    font-weight: bold;
    border-radius: 28px;
    min-width: 56px;
    max-width: 56px;
    min-height: 56px;
    max-height: 56px;
}}
"""


def apply_theme(app: QApplication, dark: bool) -> None:
    """Apply the dark or light theme to the whole application.

    The dark theme is built as a ``QPalette`` on top of Qt's *Fusion*
    style -- the documented, cross-platform way to get a consistent dark
    UI without styling every widget class by hand. The light theme simply
    restores Fusion's standard palette.

    Args:
        app: The running application instance.
        dark: ``True`` for dark mode, ``False`` for light mode.
    """
    app.setStyle("Fusion")
    palette = QPalette() if not dark else _dark_palette()
    app.setPalette(palette)
    app.setStyleSheet(_BUTTON_STYLE)


def _dark_palette() -> QPalette:
    """Build the dark ``QPalette``.

    Returns:
        A palette with near-black surfaces and light text, following the
        common Fusion dark-theme colour set.
    """
    palette = QPalette()
    window = QColor(37, 37, 40)
    base = QColor(25, 25, 28)
    text = QColor(225, 225, 225)
    disabled = QColor(120, 120, 120)

    palette.setColor(QPalette.ColorRole.Window, window)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.AlternateBase, window)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, window)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.ToolTipBase, base)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(27, 27, 27))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled)
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled
    )
    return palette
