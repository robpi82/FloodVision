"""FloodVision desktop GUI (PySide6).

This package is a *presentation layer only*: it calls the existing
backend modules and never duplicates processing logic.

Modules:
    * :mod:`src.gui.app_settings`     -- persisted GUI settings (JSON)
    * :mod:`src.gui.theme`            -- dark/light theme application
    * :mod:`src.gui.log_handler`      -- logging bridge into the GUI
    * :mod:`src.gui.worker`           -- QThread wrapper around the batch
    * :mod:`src.gui.image_view`       -- tabbed, scaling image preview
    * :mod:`src.gui.statistics_panel` -- live per-pair statistics
    * :mod:`src.gui.settings_dialog`  -- settings editor dialog
    * :mod:`src.gui.log_console`      -- colorised, exportable log console
    * :mod:`src.gui.navigator`        -- navigation model over processed pairs
    * :mod:`src.gui.summary_dialog`   -- end-of-batch summary dialog
    * :mod:`src.gui.main_window`      -- window composition and wiring
"""
