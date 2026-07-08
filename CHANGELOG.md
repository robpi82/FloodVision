# Changelog

All notable changes to this project will be documented in this file.

---

## [0.8.0] - Unreleased

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
- 13 automated tests for the GeoTIFF metadata loader
- Separate development dependencies via `requirements-dev.txt`
- GeoTIFF pair compatibility validation
- CRS compatibility checks
- Raster dimension compatibility checks
- Pixel resolution compatibility checks
- Raster bounds compatibility checks
- Affine transform compatibility checks
- Structured compatibility results and mismatch reporting
- 22 automated tests for GeoTIFF pair compatibility
- 35 automated tests in the complete test suite
- GeoTIFF compatibility validation integrated into batch processing
- Automatic spatial compatibility checks before GeoTIFF pair processing
- Safe rejection of incompatible GeoTIFF pairs
- Safe rejection of mixed image and GeoTIFF pairs
- Batch processing continuation after GeoTIFF compatibility failures
- 5 automated tests for GeoTIFF batch integration
- 40 automated tests in the complete test suite
- 
### Improved

- Extended FloodVision with the foundation for GIS raster workflows
- Improved project reliability through automated testing
- Improved reliability of spatial raster comparison
- Added tolerance-based comparison for floating-point geospatial values
- Improved batch processing reliability for geospatial raster workflows
- Improved error reporting for incompatible GeoTIFF pairs
- Preserved existing PNG and JPG processing behavior
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