# Changelog

All notable changes to this project will be documented in this file.

---

## [0.9.0] - Unreleased

### Added

- Optional RGB band selection for multi-band GeoTIFF rasters
- Zero-based raster band indexing
- Preservation of requested band order during RGB conversion
- Validation of selected band count
- Validation of out-of-range band indices
- Automated tests for GeoTIFF raster band selection
- User-configurable multispectral RGB band selection via `config.yaml`
- Validation of multispectral RGB band configuration
- Validation of band count, integer types, and non-negative band indices
- `MULTISPECTRAL_RGB_BANDS` configuration constant
- Automated tests for multispectral band configuration
- 111 automated tests in the complete test suite

### Planned

- Sentinel-2 imagery support
- Multispectral GeoTIFF raster loading
- Sentinel-2 band metadata handling
- Support for non-RGB raster workflows
- Preservation of existing RGB and GeoTIFF processing workflows
- Automated tests for multispectral raster processing

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