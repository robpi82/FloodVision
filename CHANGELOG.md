# Changelog

All notable changes to FloodVision are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/); the
project follows semantic versioning.

## [0.7.0] - 2026-07-04

Professional image viewing.

### Modified files
- `src/gui/image_view.py` — plain mouse-wheel zoom anchored under the
  cursor (modifier no longer required); double click resets to Fit to
  Window; **linked views**: zoom and pan are mirrored across all four
  tabs via a new `view_transformed` signal and `copy_view_state()`
  (re-entrancy guarded); adaptive pixmap filtering (smooth ≤ 200 %,
  crisp nearest-neighbour above); new `zoom_changed(scale, fit)` signal.
- `src/gui/main_window.py` — toolbar buttons relabelled to *Zoom In /
  Zoom Out / Fit Image / Actual Size* with shortcut tooltips; live zoom
  indicator label wired to `zoom_changed`; View-menu entries renamed
  (*Fit Image*, *Actual Size (100%)*).
- `src/__init__.py` — version bump to 0.7.0.

### New files
- `README.md` — project overview, screenshots section, quick start,
  architecture notes, roadmap.
- `CHANGELOG.md` — this file.
- `docs/screenshots/main_window_dark.png` — README screenshot.

### Unchanged
- Entire backend (`src/*.py` outside `src/gui/`), all detection
  algorithms, `worker.py`, `theme.py`, dialogs, settings, entry points.

## [0.6.1] - 2026-07-04
GUI/UX polish: pair navigation (Previous/Next), zoomable QGraphicsView
tabs, statistics dock with live counters, colorized log console with
timestamps and export, end-of-batch summary dialog with "Open Output
Folder", File/View menus with shortcuts, recent folders, busy cursor and
double-start guard.

## [0.6.0] - 2026-07-03
PySide6 desktop application: threaded batch execution (QThread +
signals), live previews, settings dialog with JSON persistence,
dark/light theme. Backend gained optional `on_pair_done` observer and
`is_cancelled` hook (backward compatible).

## [0.5.0] - 2026-07-03
Validated YAML configuration (`config.yaml`) with fail-fast errors
naming the exact dotted key; new `ConfigurationError`.

## [0.4.0] - 2026-07-02
Before/after change detection: pair matching, mask comparison
(`NEW = AFTER AND NOT BEFORE`), red new-flood products, pair batch and
extended CSV report.

## [0.3.0] - 2026-07-02
Fault-tolerant batch processing with per-image records, statistics and
pandas CSV report.

## [0.2.0] - 2026-07-02
HSV water detection, Lee-free speckle handling via Gaussian blur,
morphological cleanup, overlay generation, three-panel comparison.

## [0.1.0] - 2026-07-02
Project foundation: modular architecture, image loading with metadata,
matplotlib preview, logging, custom exceptions.
