# Changelog

All notable changes to this project will be documented in this file.

---

### [0.10.0] - In Development

### Added

- GUI selection between HSV color detection and Sentinel-2 spectral detection
- `DETECTION_MODE_HSV` / `DETECTION_MODE_SPECTRAL` constants and a `VALID_DETECTION_MODES` set, replacing free-standing detection-mode strings
- Persistent detection-mode setting, restored on the next application start
- Validation of persisted `detection_mode` values, with a safe fallback to HSV for missing, unknown, or wrong-type values
- Automatic activation and deactivation of the HSV threshold controls based on the selected detection method
- Explanatory hint text in the settings dialog describing when to use HSV versus Sentinel-2 spectral detection
- Explicit `FloodVisionError` from the GUI worker's detector factory for an unsupported detection mode
- Automated tests for detection-mode persistence and validation (`tests/test_app_settings.py`)
- Automated tests for HSV/spectral detector creation, including the invalid-mode error path (`tests/test_worker.py`)
- Automated GUI tests for the settings dialog's detection-method selection (`tests/test_settings_dialog.py`)
- Configurable spectral index (NDWI or MNDWI) in `SpectralWaterDetector`, replacing the previous NDWI-only implementation
- `SPECTRAL_INDEX_NDWI` / `SPECTRAL_INDEX_MNDWI` constants and a `VALID_SPECTRAL_INDICES` set in `src/spectral_indices.py`
- Automatic Sentinel-2 band resolution per selected index: B03/B08 for NDWI, B03/B11 for MNDWI
- GUI selection between NDWI and MNDWI, enabled only while spectral detection is active
- Persistent, validated `spectral_index` setting, with a safe fallback to NDWI for missing, unknown, or wrong-type values
- Index-specific hint text in the settings dialog describing the trade-off between NDWI and MNDWI
- Automated tests for MNDWI-based detection and per-index band resolution (`tests/test_spectral_detector.py`)
- Automated tests for spectral-index persistence and validation (`tests/test_app_settings.py`)
- Automated tests for spectral-index pass-through in the GUI worker (`tests/test_worker.py`)
- Automated GUI tests for the settings dialog's spectral-index selection (`tests/test_settings_dialog.py`)
- Configurable spectral-index threshold in the settings dialog, replacing the previously fixed 0.1 value
- `DEFAULT_SPECTRAL_THRESHOLD` constant in `src/spectral_detector.py`, shared between the detector's own default and the GUI settings default
- `SPECTRAL_THRESHOLD_MIN` / `SPECTRAL_THRESHOLD_MAX` range constants in `src/gui/app_settings.py`
- Persistent, range-validated `spectral_threshold` setting, with a safe fallback to the default for missing, out-of-range, or wrong-type values
- Automated tests for spectral-threshold persistence and range validation (`tests/test_app_settings.py`)
- Automated tests for spectral-threshold pass-through in the GUI worker (`tests/test_worker.py`)
- Automated GUI tests for the settings dialog's threshold control (`tests/test_settings_dialog.py`)
- `index_values` field on `WaterDetectionResult`, exposing the raw NDWI/MNDWI raster that was previously computed and discarded after masking
- `colorize_spectral_index()` in `src/visualization.py`: false-colour rendering of a spectral index raster using a diverging colormap (blue = water-like, red/brown = land-like, grey = no data)
- `before_index.png` / `after_index.png` batch products for spectral-mode runs, showing the false-colour NDWI/MNDWI raster
- Two additional panels in `comparison.png` for spectral-mode runs, showing the before/after spectral-index rasters alongside the existing four panels
- Fifth "Spectral Index" preview tab in the desktop GUI, populated only for spectral-mode runs
- `spectral_index` path on `PairEntry` (`src/gui/navigator.py`), wired through to the new preview tab
- Automated tests for `colorize_spectral_index()` (`tests/test_visualization.py`, new)
- Automated tests confirming `index_values` is populated for NDWI/MNDWI and left `None` for HSV (`tests/test_spectral_detector.py`)
- Automated integration tests confirming spectral-index PNGs are produced only for spectral-mode batch runs, never for HSV (`tests/test_spectral_batch_integration.py`)
- Automated GUI tests for the fifth preview tab, including graceful fallback when no spectral-index file exists (`tests/test_image_view.py`, new)
- `export_spectral_index_geotiff()` in `src/geotiff_export.py`: georeferenced single-band float32 GeoTIFF export of the raw NDWI/MNDWI raster, carrying the source CRS and affine transform
- `before_index.tif` / `after_index.tif` batch products for spectral-mode runs on GeoTIFF pairs, ready to open directly in QGIS or ArcGIS Pro
- NaN written as a real NoData value on the exported index GeoTIFF, unlike the flood-mask export's deliberate choice not to define one -- a missing index value is a genuinely different case from a valid two-class flood mask
- Automated tests for the georeferenced index export, mirroring the existing flood-mask export tests (`tests/test_geotiff_export.py`)
- Automated integration tests confirming index GeoTIFFs are produced only for spectral-mode runs on GeoTIFF pairs, never for HSV or for plain image pairs (`tests/test_spectral_batch_integration.py`)
- `src/sentinel2_band_stacker.py`: combines individual single-band Sentinel-2 raster files -- the shape real Level-2A `.SAFE` products ship in -- into one aligned, stacked raster compatible with the existing `GeoTiffRasterData`/`SpectralWaterDetector` pipeline, requiring no changes to either
- Automatic resolution checking against `SENTINEL2_BANDS` metadata, resampling any band coarser than the finest requested band (e.g. 20 m B11) onto that band's exact pixel grid
- Bilinear resampling (configurable) for pixel values; always nearest-neighbour for validity masks, so mask boundaries stay binary instead of blurring into meaningless fractional values
- `Sentinel2BandStackError` exception for domain-level failures (missing files, unreadable files, bands in mismatched coordinate reference systems)
- Automated tests covering same-resolution and mixed-resolution stacking, bilinear-vs-nearest resampling behaviour, resampled validity-mask propagation, and all error paths (`tests/test_sentinel2_band_stacker.py`, new)
- `src/sentinel2_import.py`: writes the aligned, stacked raster from `stack_sentinel2_bands()` back out as a single combined, georeferenced multi-band GeoTIFF, with each band's Sentinel-2 code embedded as its band description
- The combined file is a completely ordinary GeoTIFF from the rest of the application's point of view -- it can be dropped straight into `data/before`/`data/after` and processed by the unmodified `GeoTiffRasterLoader`, `SpectralWaterDetector` and `BatchProcessor`, with no further code changes required anywhere
- Automated tests confirming the combined file's structure (band count, order, CRS, resampled grid) and, critically, a full round trip through the existing unmodified loader and spectral detector (`tests/test_sentinel2_import.py`, new)
- `src/gui/sentinel2_import_dialog.py`: new **File → Import Sentinel-2 Bands...** dialog wrapping `combine_sentinel2_bands_to_geotiff()` -- select individual band files or a whole folder, review detected bands and resolutions in a table, choose Before/After and an output name, and combine with one click
- Best-effort Sentinel-2 band-code detection from filenames (case-insensitive, e.g. `T33UUP_20230615T101031_B03_10m.jp2` → `B03`), with explicit warnings for unrecognised files when hand-picked, and silent skipping of irrelevant files (metadata, thumbnails) during a folder scan
- Combine failures (mismatched CRS, missing files) are shown inline in the dialog rather than crashing the application
- Automated tests for band-code detection, adding/removing files, folder scanning, and both the success and failure paths of combining (`tests/test_sentinel2_import_dialog.py`, new)

### Verified

- The complete Sentinel-2 workflow (band import, resampling, spectral detection, false-colour visualization, georeferenced index export) confirmed end-to-end against real Copernicus Data Space Ecosystem Sentinel-2 L2A data, not just synthetic test fixtures: two full-resolution acquisitions (10980 x 10980 px each) of the same tile, imported via the new GUI dialog and run through a complete batch analysis without any code changes
- Along the way, confirmed the import dialog's band-code detection and per-band resampling work correctly against real ESA filenames and native JPEG2000 (`.jp2`) band files, not only the GeoTIFF fixtures used in automated tests

### Fixed

- Preview images (Before/After/Overlay/New Flood Mask/Spectral Index) silently failing to display -- falling back to their placeholder with no error anywhere in the log -- for full-resolution real-world tiles. Root cause: Qt's default 256 MB decoded-image allocation limit, a safeguard against maliciously crafted "decompression bomb" images, rejecting this application's own legitimate, locally-generated batch output (a single-band preview PNG of a 10980 x 10980 px Sentinel-2 tile decodes to roughly 345 MB as RGB). `gui_main.py` now disables the limit at startup, since every image FloodVision ever loads is its own trusted output, never untrusted input. Found via the real-Copernicus-data verification above -- our synthetic test fixtures were always small enough to stay under the limit, so this had no automated test coverage before now
- Automated tests reproducing the failure and its fix by temporarily lowering/raising the allocation limit against a smaller fixture, rather than committing a genuinely huge test image (`tests/test_image_view.py`)

### Improved

- Expanded the complete regression test suite to 314 passing tests

---

### [0.9.2] - 2026-07-19

### Added

* Sentinel-2 NDWI band resolution for Green (B03) and NIR (B08) based on the actual raster band order
* Validation and clear error reporting when required NDWI bands are missing
* Valid-data mask support in NDWI calculations
* Automated tests for Sentinel-2 NDWI band resolution
* Automated regression tests for NDWI valid-data mask handling
* Automated regression test for preservation of raster validity masks in spectral water detection

### Improved

* Refactored GeoTIFF raster loading in the batch processor into a reusable raw-raster loading method
* Improved separation between raw raster loading and RGB image conversion
* Improved NDWI processing by excluding invalid and NoData pixels directly during spectral-index calculation
* Improved consistency of validity-mask propagation through the spectral water-detection pipeline
* Improved reliability of NoData-aware Sentinel-2 water detection
* Expanded the complete regression test suite to 182 passing tests

### Fixed

* Fixed `SpectralWaterDetector` not forwarding the raster validity mask to NDWI calculation
* Fixed `SpectralWaterDetector` not preserving the validity mask in `WaterDetectionResult`
* Removed unreachable duplicate result-return code in spectral water detection
* Removed the unused `SpectralDetectorAdapter` placeholder after confirming that productive spectral detection is routed directly through `GeoTiffRasterData`
* Synchronized `develop-v0.9.1` with all changes from `develop-v0.9.0`

---

### [0.9.0] - 2026-07-14

### Added

- Optional RGB band selection for multi-band GeoTIFF rasters
- Zero-based raster band indexing
- Preservation of requested source-band order during RGB conversion
- Validation of selected band count
- Validation of integer and non-negative band indices
- Validation of out-of-range band indices
- User-configurable multispectral RGB band selection via `config.yaml`
- `MULTISPECTRAL_RGB_BANDS` configuration constant
- Productive multispectral GeoTIFF processing in the batch workflow
- Automatic loading of multi-band GeoTIFF raster data
- Dedicated GeoTIFF raster loading and RGB conversion in the batch pipeline
- GeoTIFF band-description loading via Rasterio
- Preservation of GeoTIFF band descriptions in raster data
- Support for partially missing GeoTIFF band descriptions
- Sentinel-2 spectral band metadata foundation
- Immutable `Sentinel2Band` metadata model
- Complete Sentinel-2 band metadata catalog
- Metadata definitions for B02, B03, B04, B05, B06, B07, B08, B8A, B09, B10, B11, and B12
- Native spatial-resolution metadata for supported Sentinel-2 bands
- Case-insensitive Sentinel-2 band lookup
- Whitespace normalization for Sentinel-2 band codes
- Validation and error handling for unknown Sentinel-2 bands
- Sentinel-2 band-code to zero-based raster-index conversion
- Preservation of requested Sentinel-2 band order
- Sentinel-2 band-index resolution from the actual raster band order
- Automatic Sentinel-2 RGB selection from GeoTIFF band descriptions
- Automatic resolution of B04, B03, and B02 for Sentinel-2 RGB processing
- Validation of required Sentinel-2 RGB bands
- Clear error reporting when required Sentinel-2 bands are missing
- Sentinel-2 band resolution despite unrelated missing band descriptions
- NDWI spectral-index calculation
- MNDWI spectral-index calculation foundation
- Pure NumPy-based spectral-index processing
- Spectral band extraction from Sentinel-2-like raster data
- Spectral water detection using Sentinel-2 Green and NIR bands
- NDWI threshold-based water-mask generation
- Spectral water-coverage calculation
- Compatible `WaterDetectionResult` output for the existing processing pipeline
- Optional validity mask in `WaterDetectionResult`
- Spectral detector adapter for the batch-processing architecture
- Strategy-compatible spectral detection alongside RGB-based detection
- Productive routing of `SpectralWaterDetector` through the backend batch workflow
- Complete synthetic Sentinel-2 Before/After batch workflow
- End-to-end NDWI-based flood-change detection
- Georeferenced export of spectral flood masks
- NoData-aware spectral water detection
- NoData-aware Before/After flood-change detection
- Shared validity-mask handling for paired raster observations
- Intersection of Before and After validity masks for statistical evaluation
- Safe handling of rasters without valid pixels
- Automated multispectral band-selection tests
- Automated multispectral configuration tests
- Automated four-band GeoTIFF integration tests
- Automated GeoTIFF band-description tests
- Automated Sentinel-2 metadata tests
- Automated Sentinel-2 band-resolution tests
- Automated NDWI and MNDWI tests
- Automated spectral band-extraction tests
- Automated spectral water-detection tests
- Automated spectral detector integration tests
- Automated Sentinel-2 Before/After batch integration test
- Automated georeferenced spectral-export validation
- Automated invalid-pixel exclusion tests
- Automated fully masked raster-comparison tests
- Complete regression test suite with 179 passing tests

### Improved

- Extended multispectral support from isolated raster conversion to productive batch processing
- Preserved the existing PNG and JPEG processing workflows
- Preserved the existing three-band GeoTIFF processing workflow
- Preserved the existing HSV-based water-detection workflow
- Improved separation between standard image loading and GeoTIFF raster loading
- Improved maintainability through reusable Sentinel-2 metadata components
- Improved maintainability through reusable spectral-processing components
- Improved architecture flexibility through interchangeable detection strategies
- Improved Sentinel-2 band handling through raster-description-based resolution
- Improved support for partially documented multispectral rasters
- Routed spectral water detection through the productive backend workflow
- Ensured `SpectralWaterDetector` receives `GeoTiffRasterData` instead of RGB Pillow images
- Excluded invalid and NoData pixels from spectral water classification
- Excluded invalid and NoData pixels from spectral water-coverage statistics
- Added validity-mask shape validation
- Excluded invalid pixels from generated spectral water masks
- Excluded invalid pixels from Before water-coverage calculations
- Excluded invalid pixels from After water-coverage calculations
- Excluded invalid pixels from new-water percentage calculations
- Excluded invalid pixels from net flood-increase calculations
- Removed newly flooded classifications from invalid raster areas
- Manually verified the existing PNG/JPEG desktop workflow
- Confirmed successful generation of masks, overlays, comparison images, and CSV reports
- Confirmed that unmatched image files continue to be skipped safely

### Fixed

- Fixed unreachable spectral-detection code in the batch processor
- Fixed spectral detection being bypassed during productive pair processing
- Fixed `SpectralWaterDetector` receiving Pillow images instead of raster data
- Fixed NoData pixels being included in spectral coverage denominators
- Fixed NoData pixels being included in Before/After flood-statistics denominators
- Fixed invalid raster pixels being able to influence newly flooded percentages
- Fixed fully invalid raster comparisons to return safe zero-valued statistics

### Known Limitations

- The desktop GUI currently instantiates the HSV-based detector
- Sentinel-2 NDWI detection is currently available through the backend and batch-processing architecture
- The desktop GUI does not yet provide a detector selection between HSV and Sentinel-2 spectral detection
- Productive MNDWI selection is not yet available
- Automatic Sentinel-2 satellite-product import is not yet available
- Real Sentinel-2 Level-2A product ingestion has not yet been implemented

### Planned

The following items are planned for later releases and are not part of v0.9.0:

- GUI selection between HSV and Sentinel-2 spectral detection
- Productive selection between NDWI and MNDWI
- Processing of real Sentinel-2 Level-2A products
- Sentinel-2 imagery import workflow
- Spectral flood visualizations
- NDWI and MNDWI result layers
- Multi-index flood classification
- GIS-ready spectral-analysis outputs
- Multi-temporal flood monitoring
- Landsat imagery support
- Support for additional satellite imagery sources
- Additional spectral indices
- Performance improvements for large raster datasets
- Extended GIS export capabilities
- Future AI-assisted semantic-segmentation experiments

---
## [0.8.0] - 2026-07-09

### Added

- Rasterio dependency
- Initial GeoTIFF support
- GeoTIFF metadata loader
- GeoTIFF file validation
- CRS and EPSG extraction
- Raster bounds extraction
- Pixel resolution extraction
- Raster band and data type information
- NoData value extraction
- Affine transform metadata extraction
- Robust error handling for invalid and corrupted raster files
- Initial automated test infrastructure using pytest
- Separate development dependencies via `requirements-dev.txt`
- GeoTIFF pair compatibility validation
- CRS compatibility checks
- Raster dimension compatibility checks
- Pixel resolution compatibility checks
- Raster bounds compatibility checks
- Affine transform compatibility checks
- Structured compatibility results and mismatch reporting
- GeoTIFF compatibility validation integrated into batch processing
- Automatic spatial compatibility checks before GeoTIFF pair processing
- Safe rejection of incompatible GeoTIFF pairs
- Safe rejection of mixed image and GeoTIFF pairs
- Batch processing continuation after GeoTIFF compatibility failures
- GeoTIFF raster data loader
- Raster pixel data loading using Rasterio
- Band-first NumPy array representation
- Single-band and multi-band raster support
- NoData-aware raster loading
- Valid-data mask generation
- Productive GeoTIFF raster workflow integration
- Automatic routing between legacy image and GeoTIFF processing paths
- GeoTIFF raster loading integrated into batch processing
- GeoTIFF image adapter integrated into the processing pipeline
- Compatible three-band GeoTIFF processing through the existing water detection pipeline
- GeoTIFF Information Panel in the desktop GUI
- Display of CRS and EPSG information
- Display of raster dimensions and band count
- Display of pixel resolution
- Display of NoData values
- Display of raster bounds
- Automatic GeoTIFF metadata display when browsing processed results
- Neutral information state for non-georeferenced images
- GUI tests using pytest-qt
- Synthetic GeoTIFF test data generator for reproducible end-to-end testing
- Manual GeoTIFF end-to-end workflow validation on Windows
- Georeferenced GeoTIFF export for detected flood masks
- Single-band uint8 GeoTIFF output using 0/255 flood classification values
- Preservation of CRS, affine transform, raster dimensions, and spatial bounds in exported flood results
- Automatic GeoTIFF flood mask export during productive batch processing
- Dedicated GeoTIFF export error handling
- Automated tests for georeferenced GeoTIFF export
- 95 automated tests in the complete test suite

### Improved

- Extended FloodVision with the foundation for GIS raster workflows
- Improved project reliability through automated testing
- Improved reliability of spatial raster comparison
- Added tolerance-based comparison for floating-point geospatial values
- Improved batch processing reliability for geospatial raster workflows
- Improved error reporting for incompatible GeoTIFF pairs
- Preserved existing PNG and JPG processing behavior
- Extended GeoTIFF support from metadata analysis to actual raster data loading
- Improved handling of NoData pixels in geospatial raster workflows
- Improved test coverage for GeoTIFF processing
- Extended GeoTIFF support from isolated backend components to productive batch processing
- Preserved the existing PNG and JPEG image workflow while adding a dedicated GeoTIFF processing path
- Improved handling of unsupported GeoTIFF band configurations
- Improved integration test coverage for geospatial raster processing
- Extended the desktop GUI with visible geospatial metadata
- Improved integration between the GeoTIFF backend and PySide6 user interface
- Improved result navigation with automatic metadata updates
- Added automated test coverage for GeoTIFF GUI components
- Added pytest-qt to the development dependencies
- Improved cross-platform portability of GUI directory settings
- Added automatic fallback to project-relative default directories when stored paths do not exist on the current system
- Preserved valid user-selected custom directories across application restarts
- Added automated test coverage for cross-platform GUI settings behavior
- Extended the GeoTIFF workflow from raster processing to GIS-ready result export
- Improved interoperability with GIS software through georeferenced flood mask outputs
- Preserved the existing PNG and JPEG visualization workflow while adding GeoTIFF result export
- Improved GeoTIFF batch processing with reusable source metadata and no redundant metadata read

### Fixed

- Fixed GeoTIFF Information Panel crash caused by an outdated metadata attribute name
- Updated GeoTIFF Information Panel tests to use the current `pixel_size` metadata field

---

## [0.7.1] - 2026-07-07

### Added

- Drag & Drop support for folder selection
- Reusable folder selection component

### Improved

- Improved image navigation
- Improved macOS image panning
- Improved GUI usability
- Improved folder selection workflow
- Improved image viewing experience

### Changed

- Refactored GUI components for better maintainability

---

## [0.7.0] - 2026-07-06

### Added

- Professional desktop GUI
- Image navigation
- Zoom controls
- Fit Image
- Actual Size (100%)
- Statistics panel
- Live log console
- Screenshot documentation

### Improved

- Better project structure
- Improved user interface
- Enhanced logging
- Better usability

### Fixed

- Improved error handling
- More stable batch processing

---

## [0.6.1] - 2026-07-05

### Added

- Summary dialog
- Navigation panel
- Log console
- Statistics improvements

### Improved

- GUI usability
- Settings handling

---

## [0.6.0] - 2026-07-04

### Added

- First desktop GUI using PySide6
- Progress bar
- Image preview
- Settings dialog

---

## [0.5.0] - 2026-07-03

### Added

- Batch processing
- Automatic image pairing
- CSV report generation
- Overlay visualization

---

## [0.4.0]

### Added

- Flood change detection

---

## [0.3.0]

### Added

- Water detection

---

## [0.2.0]

### Added

- Image loading

---

## [0.1.0]

### Added

- Initial project structure