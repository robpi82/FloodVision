"""Main window: composition and wiring of all GUI components.

Architecture note: this class is the GUI's *composition root* -- the
counterpart to ``main.py`` on the CLI side. It builds the layout, owns
the settings snapshot and connects worker signals to panel slots. All
domain work happens in the backend; all rendering happens in the child
widgets; this class only coordinates.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src import report_generator
from src.batch_processor import BatchResult, FloodComparisonResult, ProcessingStatus
from src.gui import theme
from src.gui.app_settings import AppSettings, save_settings
from src.gui.image_view import ImageView
from src.gui.log_handler import QtLogHandler
from src.gui.settings_dialog import SettingsDialog
from src.gui.statistics_panel import StatisticsPanel
from src.gui.worker import BatchWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """The FloodVision desktop application window."""

    def __init__(self, settings: AppSettings) -> None:
        """Build the window and install the GUI logging bridge.

        Args:
            settings: Settings loaded at startup (JSON or defaults).
        """
        super().__init__()
        self._settings = settings
        self._worker: BatchWorker | None = None

        self.setWindowTitle("FloodVision")
        self.resize(1400, 900)

        self._image_view = ImageView()
        self._statistics = StatisticsPanel()
        self._build_layout()
        self._install_log_bridge()
        logger.info("FloodVision GUI ready")

    # ------------------------------------------------------------------
    # Layout construction
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        """Assemble sidebar, preview, statistics and bottom panel."""
        columns = QHBoxLayout()
        columns.addWidget(self._build_sidebar())
        columns.addWidget(self._image_view, stretch=1)
        columns.addWidget(self._statistics)

        root = QVBoxLayout()
        root.addLayout(columns, stretch=1)
        root.addWidget(self._build_bottom_panel())

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

    def _build_sidebar(self) -> QWidget:
        """Create the left control sidebar.

        Returns:
            The sidebar widget with logo, folder pickers and actions.
        """
        logo = QLabel("FV")
        logo.setObjectName("logoBadge")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("FloodVision")
        title.setObjectName("appTitle")
        subtitle = QLabel("Flood Detection & Change Detection")
        subtitle.setObjectName("appSubtitle")
        subtitle.setWordWrap(True)

        self._before_edit = QLineEdit(self._settings.before_dir)
        self._after_edit = QLineEdit(self._settings.after_dir)
        self._output_edit = QLineEdit(self._settings.output_dir)

        self._start_button = QPushButton("Start Analysis")
        self._start_button.setObjectName("primaryButton")
        self._start_button.clicked.connect(self._on_start)
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setEnabled(False)
        self._cancel_button.clicked.connect(self._on_cancel)
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self._on_settings)

        layout = QVBoxLayout()
        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(12)
        layout.addLayout(self._folder_row("BEFORE folder", self._before_edit))
        layout.addLayout(self._folder_row("AFTER folder", self._after_edit))
        layout.addLayout(self._folder_row("OUTPUT folder", self._output_edit))
        layout.addSpacing(12)
        layout.addWidget(self._start_button)
        layout.addWidget(self._cancel_button)
        layout.addWidget(settings_button)
        layout.addStretch(1)

        sidebar = QFrame()
        sidebar.setLayout(layout)
        sidebar.setFixedWidth(280)
        return sidebar

    def _folder_row(self, caption: str, edit: QLineEdit) -> QVBoxLayout:
        """Build one labelled folder picker row.

        Args:
            caption: Row caption.
            edit: Line edit holding the chosen path.

        Returns:
            The assembled layout.
        """
        browse = QPushButton("...")
        browse.setFixedWidth(36)
        browse.clicked.connect(lambda: self._browse_into(edit, caption))
        row = QHBoxLayout()
        row.addWidget(edit, stretch=1)
        row.addWidget(browse)
        block = QVBoxLayout()
        block.addWidget(QLabel(caption))
        block.addLayout(row)
        return block

    def _build_bottom_panel(self) -> QWidget:
        """Create the bottom panel: progress bar, current file, log console.

        Returns:
            The bottom panel widget.
        """
        self._progress = QProgressBar()
        self._progress.setValue(0)
        self._current_file = QLabel("Ready.")
        self._log_console = QPlainTextEdit()
        self._log_console.setReadOnly(True)
        self._log_console.setMaximumBlockCount(2000)  # bounded memory
        self._log_console.setFixedHeight(140)

        layout = QVBoxLayout()
        layout.addWidget(self._progress)
        layout.addWidget(self._current_file)
        layout.addWidget(self._log_console)
        panel = QFrame()
        panel.setLayout(layout)
        return panel

    def _install_log_bridge(self) -> None:
        """Route the application log into the GUI console (thread-safe)."""
        handler = QtLogHandler()
        handler.message_emitted.connect(self._log_console.appendPlainText)
        logging.getLogger().addHandler(handler)

    # ------------------------------------------------------------------
    # Slots: user actions
    # ------------------------------------------------------------------
    def _on_start(self) -> None:
        """Validate inputs, snapshot settings and launch the worker."""
        self._settings = self._settings_from_sidebar()
        missing = [
            caption
            for caption, path in (
                ("BEFORE", self._settings.before_dir),
                ("AFTER", self._settings.after_dir),
            )
            if not Path(path).is_dir()
        ]
        if missing:
            QMessageBox.warning(
                self,
                "Folder missing",
                f"The following folder(s) do not exist: {', '.join(missing)}.",
            )
            return

        save_settings(self._settings)
        self._image_view.clear_all()
        self._statistics.reset()
        self._progress.setValue(0)
        self._set_running(True)

        self._worker = BatchWorker(self._settings)
        self._worker.pair_completed.connect(self._on_pair_completed)
        self._worker.batch_finished.connect(self._on_batch_finished)
        self._worker.batch_failed.connect(self._on_batch_failed)
        self._worker.start()

    def _on_cancel(self) -> None:
        """Forward a cancellation request to the running worker."""
        if self._worker is not None:
            self._cancel_button.setEnabled(False)
            self._worker.request_cancel()

    def _on_settings(self) -> None:
        """Open the settings dialog and apply the result on accept."""
        dialog = SettingsDialog(self._settings_from_sidebar(), parent=self)
        if dialog.exec():
            self._settings = dialog.result_settings()
            self._output_edit.setText(self._settings.output_dir)
            save_settings(self._settings)
            app = QApplication.instance()
            if isinstance(app, QApplication):
                theme.apply_theme(app, dark=self._settings.dark_mode)

    # ------------------------------------------------------------------
    # Slots: worker signals (delivered on the GUI thread by Qt)
    # ------------------------------------------------------------------
    def _on_pair_completed(
        self, record: FloodComparisonResult, index: int, total: int
    ) -> None:
        """Update progress, statistics and previews for one pair.

        Args:
            record: Result record of the finished pair.
            index: 1-based pair index.
            total: Total number of pairs.
        """
        self._progress.setMaximum(total)
        self._progress.setValue(index)
        self._current_file.setText(f"Processed: {record.filename}")
        self._statistics.show_record(record, index, total)
        if record.status is ProcessingStatus.SUCCESS:
            stem = Path(record.filename).stem
            out = Path(self._settings.output_dir) / stem
            self._image_view.show_pair(
                before_image=Path(self._settings.before_dir) / record.filename,
                after_image=Path(self._settings.after_dir) / record.filename,
                overlay=out / "overlay.png",
                new_flood_mask=out / "new_flood_mask.png",
            )

    def _on_batch_finished(self, result: BatchResult) -> None:
        """Present the final summary and restore the idle state.

        Args:
            result: The (possibly partial, if cancelled) batch result.
        """
        cancelled = self._worker.was_cancelled if self._worker else False
        self._set_running(False)
        self._statistics.show_batch_result(result)
        summary = report_generator.build_summary(result)
        logger.info("\n%s", summary)

        title = "Batch cancelled" if cancelled else "Batch finished"
        icon = QMessageBox.Icon.Warning if cancelled else QMessageBox.Icon.Information
        box = QMessageBox(icon, title, summary, parent=self)
        box.exec()
        self._current_file.setText(title + ".")

    def _on_batch_failed(self, title: str, message: str) -> None:
        """Show a friendly error dialog for a batch that could not run.

        Args:
            title: Short dialog title.
            message: User-facing explanation.
        """
        self._set_running(False)
        QMessageBox.critical(self, title, message)
        self._current_file.setText("Failed: see log.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _settings_from_sidebar(self) -> AppSettings:
        """Merge the sidebar folder fields into a new settings snapshot.

        Returns:
            Updated immutable settings.
        """
        return replace(
            self._settings,
            before_dir=self._before_edit.text().strip(),
            after_dir=self._after_edit.text().strip(),
            output_dir=self._output_edit.text().strip(),
        )

    def _browse_into(self, edit: QLineEdit, caption: str) -> None:
        """Open a directory picker and write the choice into a line edit.

        Args:
            edit: Target line edit.
            caption: Dialog caption.
        """
        chosen = QFileDialog.getExistingDirectory(
            self, f"Select {caption}", edit.text()
        )
        if chosen:
            edit.setText(chosen)

    def _set_running(self, running: bool) -> None:
        """Toggle the button states between idle and running.

        Args:
            running: ``True`` while a batch is active.
        """
        self._start_button.setEnabled(not running)
        self._cancel_button.setEnabled(running)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        """Persist settings and stop a running worker on window close.

        Args:
            event: Qt close event.
        """
        save_settings(self._settings_from_sidebar())
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(5000)
        logging.shutdown()  # flush handlers so the log file stays complete
        super().closeEvent(event)
