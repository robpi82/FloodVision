"""FloodVision -- flood detection and visualization from satellite imagery.

This package contains the application's core modules:

* :mod:`src.config`        -- central paths and constants
* :mod:`src.exceptions`    -- domain-specific exception hierarchy
* :mod:`src.utils`         -- generic reusable helpers
* :mod:`src.image_loader`  -- image discovery and loading
* :mod:`src.visualization`  -- matplotlib-based display and export utilities
* :mod:`src.water_detection` -- HSV-based water segmentation (strategy seam)
* :mod:`src.mask_generator`  -- mask cleanup, metrics and overlay products
* :mod:`src.change_detection` -- before/after mask comparison
* :mod:`src.batch_processor` -- fault-tolerant pair batch orchestration
* :mod:`src.report_generator` -- CSV report and batch summary
* :mod:`src.gui`             -- PySide6 desktop application (presentation only)
"""

__version__ = "0.9.0"
