"""Main window: composition and wiring of all GUI components.

Architecture note: this class is the GUI's *composition root* -- the
counterpart to ``main.py`` on the CLI side. It builds the layout and
menus, owns the settings snapshot and connects worker signals to panel
slots. All domain work happens in the backend; all rendering happens in
the child widgets; this class only coordinates.
"""

from __future__ import annotations

import logging
import shutil
import time
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QGuiApplication, QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.batch_processor import BatchResult, FloodComparisonResult, ProcessingStatus
from src.gui import theme
from src.gui.app_settings import AppSettings, save_settings
from src.gui.folder_field import FolderDropLineEdit
from src.gui.geotiff_info_panel import GeoTiffInfoPanel
from src.gui.image_view import ImageView
from src.gui.log_console import LogConsole
from src.gui.log_handler import SUCCESS, QtLogHandler
from src.gui.navigator import PairEntry, PairNavigator
from src.gui.settings_dialog import SettingsDialog
from src.gui.statistics_panel import StatisticsPanel
from src.gui.summary_dialog import SummaryDialog
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
        self._navigator = PairNavigator()
        self._last_result: BatchResult | None = None
        self._batch_started: float = 0.0

        self.setWindowTitle("FloodVision")
        self.resize(1400, 900)

        self._image_view = ImageView()
        self._statistics = StatisticsPanel()
        self._geotiff_info = GeoTiffInfoPanel()
        self._build_layout()
        self._build_statistics_dock()
        self._build_geotiff_info_dock()
        self._build_menu()
        self._install_log_bridge()
        self._update_navigation_ui()
        logger.info("FloodVision GUI ready")

    # ------------------------------------------------------------------
    # Layout construction
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        """Assemble sidebar, preview column and bottom panel."""
        center = QVBoxLayout()
        center.setSpacing(6)
        center.addWidget(self._image_view, stretch=1)
        center.addWidget(self._build_view_toolbar())

        columns = QHBoxLayout()
        columns.setSpacing(10)
        columns.addWidget(self._build_sidebar())
        columns.addLayout(center, stretch=1)

        root = QVBoxLayout()
        root.setContentsMargins(10, 10, 10, 10)
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

        self._before_edit = FolderDropLineEdit(self._settings.before_dir)
        self._after_edit = FolderDropLineEdit(self._settings.after_dir)
        self._output_edit = FolderDropLineEdit(self._settings.output_dir)
        for caption, edit in (
            ("BEFORE", self._before_edit),
            ("AFTER", self._after_edit),
            ("OUTPUT", self._output_edit),
        ):
            edit.setToolTip(
                f"{caption} folder -- type a path, use the ... button, "
                f"or drop a folder here from your file manager"
            )
            edit.folder_dropped.connect(
                lambda path, c=caption: self._on_folder_dropped(c, path)
            )
            edit.drop_rejected.connect(
                lambda: self.statusBar().showMessage(
                    "Only a single folder can be dropped here.", 4000
                )
            )

        self._start_button = QPushButton("Start Analysis")
        self._start_button.setObjectName("primaryButton")
        self._start_button.setToolTip("Run the analysis on all image pairs (Ctrl+R)")
        self._start_button.clicked.connect(self._on_start)
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setEnabled(False)
        self._cancel_button.setToolTip("Stop after the current pair finishes")
        self._cancel_button.clicked.connect(self._on_cancel)
        self._settings_button = QPushButton("Settings")
        self._settings_button.setToolTip("HSV thresholds, output folder, theme")
        self._settings_button.clicked.connect(self._on_settings)

        layout = QVBoxLayout()
        layout.setSpacing(8)
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
        layout.addWidget(self._settings_button)
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
        browse.setToolTip(f"Select {caption} via dialog")
        browse.setFixedWidth(36)
        browse.clicked.connect(lambda: self._browse_into(edit, caption))
        row = QHBoxLayout()
        row.addWidget(edit, stretch=1)
        row.addWidget(browse)
        block = QVBoxLayout()
        block.setSpacing(2)
        block.addWidget(QLabel(caption))
        block.addLayout(row)
        return block

    def _build_view_toolbar(self) -> QWidget:
        """Create the navigation + zoom bar under the image preview.

        Returns:
            The toolbar widget.
        """
        self._prev_button = QPushButton("\u25c0 Previous")
        self._prev_button.setToolTip("Previous image pair (\u2190 or Alt+\u2190)")
        self._prev_button.clicked.connect(self._on_previous)
        self._next_button = QPushButton("Next \u25b6")
        self._next_button.setToolTip("Next image pair (\u2192 or Alt+\u2192)")
        self._next_button.clicked.connect(self._on_next)
        self._nav_label = QLabel("no results yet")
        self._nav_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._nav_label.setMinimumWidth(220)

        zoom_out = QPushButton("Zoom Out")
        zoom_out.setToolTip("Zoom out (Ctrl+- or mouse wheel)")
        zoom_out.clicked.connect(self._image_view.zoom_out)
        zoom_in = QPushButton("Zoom In")
        zoom_in.setToolTip("Zoom in (Ctrl++ or mouse wheel)")
        zoom_in.clicked.connect(self._image_view.zoom_in)
        fit = QPushButton("Fit Image")
        fit.setToolTip("Fit image to window (Ctrl+0 or double click)")
        fit.clicked.connect(self._image_view.fit_to_window)
        actual = QPushButton("Actual Size")
        actual.setToolTip("Show at 100 % (native resolution)")
        actual.clicked.connect(self._image_view.reset_zoom)

        self._zoom_label = QLabel("Zoom: fit")
        self._zoom_label.setObjectName("appSubtitle")
        self._image_view.zoom_changed.connect(self._on_zoom_changed)

        row = QHBoxLayout()
        row.addWidget(self._prev_button)
        row.addWidget(self._nav_label, stretch=1)
        row.addWidget(self._next_button)
        row.addSpacing(24)
        row.addWidget(zoom_out)
        row.addWidget(zoom_in)
        row.addWidget(fit)
        row.addWidget(actual)
        row.addWidget(self._zoom_label)
        bar = QFrame()
        bar.setLayout(row)
        return bar

    def _build_bottom_panel(self) -> QWidget:
        """Create the bottom panel: progress bar, current file, log console.

        Returns:
            The bottom panel widget.
        """
        self._progress = QProgressBar()
        self._progress.setValue(0)
        self._current_file = QLabel("Ready.")
        self._log_console = LogConsole()
        self._log_console.setFixedHeight(150)
        save_log = QPushButton("Save log...")
        save_log.setFixedWidth(110)
        save_log.clicked.connect(self._on_export_log)

        header = QHBoxLayout()
        header.addWidget(self._current_file, stretch=1)
        header.addWidget(save_log)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.addWidget(self._progress)
        layout.addLayout(header)
        layout.addWidget(self._log_console)
        panel = QFrame()
        panel.setLayout(layout)
        return panel

    def _build_statistics_dock(self) -> None:
        """Wrap the statistics panel into a movable, floatable dock."""
        dock = QDockWidget("Statistics", self)
        dock.setWidget(self._statistics)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def _build_geotiff_info_dock(self) -> None:
        """Wrap the GeoTIFF information panel into a dock."""
        dock = QDockWidget("GeoTIFF Information", self)
        dock.setWidget(self._geotiff_info)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def _build_menu(self) -> None:
        """Create the File and View menus with keyboard shortcuts."""
        file_menu = self.menuBar().addMenu("&File")
        self._add_action(
            file_menu,
            "Open Before Folder...",
            lambda: self._browse_into(self._before_edit, "BEFORE folder"),
            shortcut=QKeySequence.StandardKey.Open,
        )
        self._add_action(
            file_menu,
            "Open After Folder...",
            lambda: self._browse_into(self._after_edit, "AFTER folder"),
        )
        self._add_action(file_menu, "Open Output Folder...", self._on_open_output)
        file_menu.addSeparator()
        self._run_action = self._add_action(
            file_menu, "Run Analysis", self._on_start, shortcut="Ctrl+R"
        )
        file_menu.addSeparator()
        self._export_csv_action = self._add_action(
            file_menu, "Export CSV...", self._on_export_csv
        )
        self._add_action(file_menu, "Export Log...", self._on_export_log)
        file_menu.addSeparator()
        self._add_action(
            file_menu, "Exit", self.close, shortcut=QKeySequence.StandardKey.Quit
        )

        view_menu = self.menuBar().addMenu("&View")
        self._add_action(
            view_menu,
            "Zoom In",
            self._image_view.zoom_in,
            shortcut=QKeySequence.StandardKey.ZoomIn,
        )
        self._add_action(
            view_menu,
            "Zoom Out",
            self._image_view.zoom_out,
            shortcut=QKeySequence.StandardKey.ZoomOut,
        )
        self._add_action(
            view_menu,
            "Fit To Window",
            self._image_view.fit_to_window,
            shortcut="Ctrl+0",
        )
        self._add_action(view_menu, "Reset Zoom (1:1)", self._image_view.reset_zoom)
        view_menu.addSeparator()
        self._add_action(
            view_menu, "Previous Pair", self._on_previous, shortcut="Alt+Left"
        )
        self._add_action(view_menu, "Next Pair", self._on_next, shortcut="Alt+Right")

    def _add_action(
        self,
        menu,
        text: str,
        slot,
        shortcut: QKeySequence.StandardKey | str | None = None,
    ) -> QAction:
        """Create, wire and register one menu action (DRY helper).

        Args:
            menu: Target menu.
            text: Action caption.
            slot: Callable invoked on trigger.
            shortcut: Optional key sequence.

        Returns:
            The created action.
        """
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _install_log_bridge(self) -> None:
        """Route the application log into the GUI console (thread-safe)."""
        handler = QtLogHandler()
        handler.message_emitted.connect(self._log_console.append_record)
        logging.getLogger().addHandler(handler)

    # ------------------------------------------------------------------
    # Slots: user actions
    # ------------------------------------------------------------------
    def _on_start(self) -> None:
        """Validate inputs, snapshot settings and launch the worker."""
        if self._worker is not None and self._worker.isRunning():
            return  # double-start guard (button is disabled, menu too)
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
        self._navigator.clear()
        self._update_navigation_ui()
        self._statistics.reset()
        self._geotiff_info.clear()
        self._progress.setValue(0)
        self._last_result = None
        self._batch_started = time.monotonic()
        self._set_running(True)

        self._worker = BatchWorker(self._settings)
        self._worker.pair_completed.connect(self._on_pair_completed)
        self._worker.batch_finished.connect(self._on_batch_finished)
        self._worker.batch_failed.connect(self._on_batch_failed)
        self._worker.start()
        self.statusBar().showMessage("Analysis running...")

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

    def _on_previous(self) -> None:
        """Navigate to the previous processed pair."""
        self._show_entry(self._navigator.previous())

    def _on_next(self) -> None:
        """Navigate to the next processed pair."""
        self._show_entry(self._navigator.next())

    def _on_open_output(self) -> None:
        """Pick the OUTPUT folder via directory dialog."""
        self._browse_into(self._output_edit, "OUTPUT folder")

    def _on_export_csv(self) -> None:
        """Copy the latest report.csv to a user-chosen location."""
        source = Path(self._output_edit.text().strip()) / "report.csv"
        if not source.is_file():
            QMessageBox.information(
                self,
                "No report yet",
                "Run an analysis first -- report.csv is created per batch.",
            )
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Export CSV report", str(source), "CSV files (*.csv)"
        )
        if target:
            shutil.copyfile(source, target)
            logger.log(SUCCESS, "Report exported to %s", target)

    def _on_export_log(self) -> None:
        """Save the console content to a text file."""
        target, _ = QFileDialog.getSaveFileName(
            self, "Export log", "floodvision_log.txt", "Text files (*.txt)"
        )
        if target:
            self._log_console.save_to_file(Path(target))
            logger.log(SUCCESS, "Log exported to %s", target)

    # ------------------------------------------------------------------
    # Slots: worker signals (delivered on the GUI thread by Qt)
    # ------------------------------------------------------------------
    def _on_pair_completed(
        self, record: FloodComparisonResult, index: int, total: int
    ) -> None:
        """Update progress, statistics, navigator and previews.

        Args:
            record: Result record of the finished pair.
            index: 1-based pair index.
            total: Total number of pairs.
        """
        self._progress.setMaximum(total)
        self._progress.setValue(index)
        self._current_file.setText(f"Processed: {record.filename}")
        self._statistics.on_pair(record, index, total)

        if record.status is ProcessingStatus.SUCCESS:
            logger.log(SUCCESS, "Pair done: %s", record.filename)
            stem = Path(record.filename).stem
            out = Path(self._settings.output_dir) / stem
            entry = PairEntry(
                record=record,
                before_image=Path(self._settings.before_dir) / record.filename,
                after_image=Path(self._settings.after_dir) / record.filename,
                overlay=out / "overlay.png",
                new_flood_mask=out / "new_flood_mask.png",
            )
            self._navigator.add(entry)
            self._show_entry(entry, update_stats=False)

    def _on_batch_finished(self, result: BatchResult) -> None:
        """Present the final summary and restore the idle state.

        Args:
            result: The (possibly partial, if cancelled) batch result.
        """
        cancelled = self._worker.was_cancelled if self._worker else False
        runtime = time.monotonic() - self._batch_started
        self._set_running(False)
        self._last_result = result
        self._statistics.show_batch_result(result)
        level = SUCCESS if not result.failed and not cancelled else logging.WARNING
        logger.log(
            level,
            "Batch %s: %d successful, %d failed, %.1f s",
            "cancelled" if cancelled else "finished",
            len(result.successful),
            len(result.failed),
            runtime,
        )
        SummaryDialog(
            result,
            output_dir=Path(self._settings.output_dir),
            runtime_seconds=runtime,
            cancelled=cancelled,
            parent=self,
        ).exec()
        status = "Batch cancelled." if cancelled else "Batch finished."
        self._current_file.setText(status)
        self.statusBar().showMessage(
            f"{status}  {len(result.successful)} successful, "
            f"{len(result.failed)} failed -- use \u2190/\u2192 to browse results.",
            8000,
        )

    def _on_batch_failed(self, title: str, message: str) -> None:
        """Show a friendly error dialog for a batch that could not run.

        Args:
            title: Short dialog title.
            message: User-facing explanation.
        """
        self._set_running(False)
        QMessageBox.critical(self, title, message)
        self._current_file.setText("Failed: see log.")
        self.statusBar().showMessage("Analysis could not run -- see log panel.", 8000)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _show_entry(self, entry: PairEntry | None, update_stats: bool = True) -> None:
        """Display a navigator entry in previews, label and statistics.

        Args:
            entry: Entry to display; ``None`` is ignored.
            update_stats: Whether to refresh the current-pair statistics
                (skipped during live processing, where ``on_pair`` already
                filled them including the batch counters).
        """
        if entry is None:
            self._update_navigation_ui()
            return
        self._image_view.show_pair(
            before_image=entry.before_image,
            after_image=entry.after_image,
            overlay=entry.overlay,
            new_flood_mask=entry.new_flood_mask,
        )
        if update_stats:
            self._statistics.show_pair_details(entry.record)
        self._geotiff_info.show_file(entry.before_image)
        self._update_navigation_ui()

    def _update_navigation_ui(self) -> None:
        """Sync navigation buttons and position label with the navigator."""
        position, total = self._navigator.position
        current = self._navigator.current
        if current is None:
            self._nav_label.setText("no results yet")
        else:
            self._nav_label.setText(
                f"{current.record.filename}   \u00b7   Image {position} of {total}"
            )
        self._prev_button.setEnabled(self._navigator.has_previous)
        self._next_button.setEnabled(self._navigator.has_next)

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
        """Open a directory picker, apply and persist the choice.

        Persisting immediately implements "recent folders": the next start
        restores whatever was chosen last, even without running a batch.

        Args:
            edit: Target line edit.
            caption: Dialog caption.
        """
        chosen = QFileDialog.getExistingDirectory(
            self, f"Select {caption}", edit.text()
        )
        if chosen:
            edit.setText(chosen)
            self._settings = self._settings_from_sidebar()
            save_settings(self._settings)

    def _set_running(self, running: bool) -> None:
        """Toggle controls and cursor between idle and running state.

        Every control that could start a second batch or change its
        inputs mid-run is disabled; the busy cursor signals background
        work. The cursor override is guarded so it is always restored
        exactly once, on both the success and the failure path.

        Args:
            running: ``True`` while a batch is active.
        """
        self._start_button.setEnabled(not running)
        self._run_action.setEnabled(not running)
        self._settings_button.setEnabled(not running)
        self._cancel_button.setEnabled(running)
        for edit in (self._before_edit, self._after_edit, self._output_edit):
            edit.setEnabled(not running)
        if running:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.BusyCursor)
        else:
            while QGuiApplication.overrideCursor() is not None:
                QGuiApplication.restoreOverrideCursor()

    def _on_zoom_changed(self, scale: float, fit_mode: bool) -> None:
        """Update the zoom indicator in the view toolbar.

        Args:
            scale: Current magnification (1.0 = 100 %).
            fit_mode: Whether the views follow fit-to-window.
        """
        self._zoom_label.setText(
            "Zoom: fit" if fit_mode else f"Zoom: {scale * 100.0:.0f} %"
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt API)
        """Navigate pairs with the plain arrow keys.

        Reaches this handler only when no child consumed the key: line
        edits keep their cursor movement, and the image views explicitly
        ignore Left/Right so navigation works while they have focus.

        Args:
            event: Qt key event.
        """
        if event.key() == Qt.Key.Key_Left:
            self._on_previous()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Right:
            self._on_next()
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_folder_dropped(self, caption: str, path: str) -> None:
        """Persist a folder set via drag & drop and confirm in the UI.

        Args:
            caption: Which field received the drop (BEFORE/AFTER/OUTPUT).
            path: The dropped directory path.
        """
        self._settings = self._settings_from_sidebar()
        save_settings(self._settings)
        self.statusBar().showMessage(f"{caption} folder set: {path}", 4000)

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
