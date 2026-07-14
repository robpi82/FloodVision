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
- Productive multispectral GeoTIFF processing in the batch workflow
- Automatic loading of multi-band GeoTIFF raster data for water detection
- Integration of configured RGB band selection into productive flood processing
- Dedicated GeoTIFF raster loading and RGB conversion in the batch pipeline
- Automated integration test for four-band GeoTIFF processing with selected RGB bands
- GeoTIFF band description loading via Rasterio
- Preservation of GeoTIFF band descriptions in raster data
- Automated tests for GeoTIFF band description loading
- Sentinel-2 spectral band metadata foundation
- Immutable `Sentinel2Band` metadata model
- Complete Sentinel-2 band metadata catalog
- Sentinel-2 metadata definitions for B02, B03, B04, B05, B06, B07, B08, B8A, B09, B10, B11, and B12
- Native spatial resolution metadata for supported Sentinel-2 bands
- Case-insensitive Sentinel-2 band lookup
- Whitespace normalization for Sentinel-2 band codes
- Validation and error handling for unknown Sentinel-2 bands
- Parameterized automated tests for Sentinel-2 band metadata
- Sentinel-2 band code to zero-based raster index conversion
- Preservation of requested Sentinel-2 band order during raster index conversion
- Automated tests for Sentinel-2 band index conversion
- Sentinel-2 band index resolution from actual raster band order
- Automated tests for raster-aware Sentinel-2 band index resolution
- Automatic Sentinel-2 RGB band selection from GeoTIFF band descriptions
- Integration of actual raster band order into productive GeoTIFF processing
- Automatic resolution of B04, B03, and B02 for Sentinel-2 RGB processing
- Automated integration testing for Sentinel-2 band-description-based RGB selection
- Validation of required Sentinel-2 RGB bands in raster band descriptions
- Clear error reporting for missing required Sentinel-2 RGB bands
- Support for partially missing GeoTIFF band descriptions
- Sentinel-2 band index resolution despite unrelated missing band descriptions
- Automated tests for partial Sentinel-2 band description handling
- Productive support for partially missing Sentinel-2 band descriptions
- Automated integration testing for partial Sentinel-2 band descriptions in batch processing
- NDWI spectral index calculation foundation
- MNDWI spectral index calculation foundation
- Pure NumPy-based spectral index implementation independent from image processing
- Spectral water detection foundation using Sentinel-2 Green and NIR bands
- NDWI threshold-based water mask generation
- Spectral water coverage calculation
- Compatible `WaterDetectionResult` output for integration with existing FloodVision pipeline
- Spectral detector adapter for integration into existing batch processing architecture
- Strategy-compatible spectral detection architecture alongside RGB-based detection
- Automated tests for spectral water detection
- Automated integration tests for spectral processing workflow
- Added a complete synthetic Sentinel-2 Before/After batch integration test
- Added end-to-end validation of NDWI-based flood change detection
- Added validation of georeferenced spectral flood mask export
- Increased the complete regression test suite to 175 passing tests
- 175 automated tests in the complete test suite
- Added NoData-aware Before/After flood change detection
- Added shared validity-mask handling for paired raster observations
- Added automated tests for invalid-pixel exclusion and fully masked raster comparisons
- Increased the complete regression test suite to 179 passing tests


### Improved

- Extended multispectral support from isolated raster conversion to productive batch processing
- Preserved existing PNG and JPEG processing workflows
- Preserved existing three-band GeoTIFF processing workflows
- Improved separation between standard image loading and GeoTIFF raster loading
- Improved test coverage for multispectral GeoTIFF processing
- Added a reusable Sentinel-2 metadata foundation for future satellite imagery workflows
- Completed the Sentinel-2 band metadata catalog for future satellite imagery processing
- Replaced redundant individual Sentinel-2 band metadata tests with parameterized test coverage
- Improved maintainability and scalability of Sentinel-2 metadata tests
- Prepared the project architecture for future Sentinel-2 and NDWI processing
- Extended FloodVision from RGB-based water detection towards physical spectral analysis
- Improved architecture flexibility through interchangeable detection strategies
- Prepared the processing pipeline for future satellite-based flood monitoring workflows
- Improved scalability for Sentinel-2 multispectral analysis
- Improved flood detection architecture through separation of spectral analysis and image-based detection
- Improved maintainability by introducing reusable spectral processing components
- Prepared FloodVision for future multispectral classification workflows
- Excluded invalid and NoData raster pixels from spectral water classification
- Excluded invalid raster pixels from spectral water coverage calculations
- Added shape validation for spectral validity masks
- Added safe handling for rasters without any valid pixels
- Added automated tests for invalid, masked, and fully NoData raster areas
- Routed spectral water detection through the productive batch-processing workflow
- Ensured `SpectralWaterDetector` receives GeoTIFF raster data instead of RGB Pillow images
- Preserved the existing PNG, JPEG, and HSV-based detection workflow
- Excluded invalid and NoData pixels from water coverage, new-water percentage, and net flood increase calculations
- Extended `WaterDetectionResult` with an optional validity mask
- Combined Before and After validity masks before flood-change analysis

### Planned

- Complete integration of spectral water detection into the production batch workflow
- Automatic Sentinel-2 NDWI and MNDWI based flood detection
- Spectral index based flood classification independent from RGB appearance
- Sentinel-2 GeoTIFF workflow using native spectral bands (B03, B08, B11)
- Automatic water mask generation from multispectral raster data
- Comparison of RGB-based and spectral-based water detection methods
- Improved flood detection accuracy using multispectral information
- Sentinel-2 satellite data import workflow
- Support for additional satellite imagery sources
- GIS visualization improvements for spectral flood products
- Export of spectral flood detection results as GIS-compatible products
- Temporal analysis of flood development using multiple satellite acquisitions
- Integration of additional spectral indices for environmental monitoring
- Future AI-based semantic segmentation experiments for flood detection

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