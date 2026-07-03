"""FloodVision GUI entry point.

Start with::

    python gui_main.py

This file mirrors ``main.py`` (the CLI entry point): it only wires the
application together -- logging, settings, theme, main window -- and
contains no logic of its own. The CLI remains fully functional; both
entry points share the identical backend.
"""

from __future__ import annotations

import sys

# The batch worker saves matplotlib figures on a background thread.
# The non-interactive "Agg" backend must be selected *before* pyplot is
# imported anywhere (src.visualization does), otherwise Qt's own
# matplotlib backend would try to touch GUI state from the worker thread.
import matplotlib

matplotlib.use("Agg")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from src.exceptions import FloodVisionError  # noqa: E402


def main() -> None:
    """Launch the FloodVision desktop application."""
    app = QApplication(sys.argv)
    try:
        # Imported here so that a broken config.yaml surfaces as a
        # friendly dialog instead of a bare traceback: importing these
        # modules triggers the validated configuration load.
        from src import utils
        from src.gui import theme
        from src.gui.app_settings import load_settings
        from src.gui.main_window import MainWindow

        utils.setup_logging()
        settings = load_settings()
        theme.apply_theme(app, dark=settings.dark_mode)
        window = MainWindow(settings)
        window.show()
    except FloodVisionError as error:
        QMessageBox.critical(None, "FloodVision cannot start", str(error))
        sys.exit(1)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
