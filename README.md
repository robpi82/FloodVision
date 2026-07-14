<p align="center">
  <img src="docs/screenshots/floodvision_banner.png" alt="FloodVision Banner" width="100%">
</p>

# 🌊 FloodVision

![Stable Version](https://img.shields.io/badge/stable-v0.8.0-red)
![Development Version](https://img.shields.io/badge/development-v0.9.0-yellow)
![Python](https://img.shields.io/badge/python-3.12-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.11-green)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-pink)
![Tests](https://img.shields.io/badge/tests-174%20passed-brightgreen)
![License](https://img.shields.io/badge/license-MIT-success)
![Status](https://img.shields.io/badge/status-active-brightgreen)

Professional desktop application for flood detection using computer vision, image processing, and geospatial raster analysis.

FloodVision compares two images of the same location ("Before" and "After") and automatically detects newly flooded areas.

The current stable release provides a complete GeoTIFF and GIS raster processing workflow. Development in v0.9.0 extends FloodVision with multispectral raster processing, Sentinel-2 support, spectral indices, and NoData-aware spectral water detection.

---

## Features

### Image Processing

* Automatic water detection
* Flood change detection
* Before / After image comparison
* Overlay visualization
* New flood mask generation
* Batch processing
* Automatic image pairing
* Robust error handling

### Desktop GUI

* Modern PySide6 desktop application
* Dark theme
* Before / After / Overlay / New Flood Mask preview
* Drag & Drop folder support
* Folder path input
* Folder browser integration
* Previous / Next image navigation
* Zoom In
* Zoom Out
* Fit Image
* Actual Size (100%)
* Improved image navigation
* Progress bar
* Live log console
* Statistics panel
* GeoTIFF Information Panel
* Automatic GeoTIFF metadata display
* Progress tracking
* Batch processing summary

### GeoTIFF & GIS Support

Available since FloodVision v0.8.0:

* Rasterio integration
* GeoTIFF file detection and validation
* GeoTIFF metadata extraction
* Coordinate Reference System (CRS) extraction
* EPSG code extraction
* Raster bounds extraction
* Pixel resolution extraction
* Raster dimensions and band information
* Raster data type information
* NoData value extraction
* Affine transform metadata extraction
* GeoTIFF pair compatibility validation
* CRS compatibility checks
* Raster dimension compatibility checks
* Pixel resolution compatibility checks
* Raster bounds compatibility checks
* Affine transform compatibility checks
* Structured compatibility results and mismatch reporting
* Tolerance-based comparison of geospatial values
* GeoTIFF compatibility validation integrated into batch processing
* Automatic spatial compatibility checks before GeoTIFF pair processing
* Safe rejection of incompatible GeoTIFF pairs
* Safe rejection of mixed image and GeoTIFF pairs
* Batch processing continuation after compatibility failures
* GeoTIFF raster data loading
* Raster pixel data extraction as NumPy arrays
* Band-first raster data representation
* Single-band and multi-band raster support
* NoData-aware raster loading
* Valid-data mask generation
* GeoTIFF raster loading error handling
* GeoTIFF image adapter
* Conversion of three-band GeoTIFF raster data to RGB images
* Band-first NumPy array to Pillow RGB image conversion
* Automatic scaling of numeric raster data to uint8
* NoData-aware RGB image conversion
* Invalid raster pixels masked as black
* Validation of supported raster band configurations
* Productive GeoTIFF raster workflow integration
* Automatic routing between legacy images and GeoTIFF raster processing
* GeoTIFF raster loading integrated into batch processing
* GeoTIFF RGB image adaptation integrated into batch processing
* Compatible three-band GeoTIFFs processed through the existing water detection pipeline
* Legacy PNG and JPEG processing workflow preserved
* Georeferenced GeoTIFF export for detected flood masks
* Single-band uint8 GeoTIFF output using 0/255 flood classification values
* Preservation of CRS, affine transform, raster dimensions, and spatial bounds
* Automatic GeoTIFF flood mask export during batch processing
* GIS-ready flood detection results for use in QGIS and ArcGIS Pro

### Multispectral Raster Support

Currently under development for FloodVision v0.9.0:

* Multispectral GeoTIFF support
* Configurable raster band selection
* Selection of arbitrary source bands for RGB image generation
* Validation of multispectral band configurations
* Preservation of existing three-band RGB workflows
* Sentinel-2 spectral band metadata foundation
* Immutable Sentinel-2 band metadata model
* Metadata definitions for B02, B03, B04, B05, B06, B07, B08, B8A, B09, B10, B11, and B12
* Native spatial resolution metadata for supported Sentinel-2 bands
* Normalized and validated Sentinel-2 band lookup
* Sentinel-2 band code to zero-based raster index conversion
* Preservation of requested Sentinel-2 band order during raster index conversion
* GeoTIFF band description loading via Rasterio
* Preservation of GeoTIFF band descriptions in raster data
* Automatic Sentinel-2 RGB band selection from GeoTIFF band descriptions
* Validation of required Sentinel-2 RGB bands in raster band descriptions
* Support for partially missing GeoTIFF band descriptions
* Sentinel-2 RGB band resolution despite unrelated missing band descriptions
* Productive batch processing support for partially missing Sentinel-2 band descriptions
* Clear error reporting when required Sentinel-2 RGB bands are missing
* Resolution of B04, B03, and B02 from the actual raster band order
* Integration of Sentinel-2 band descriptions into productive GeoTIFF processing
* Complete Sentinel-2 band metadata catalog
* NDWI spectral index calculation
* MNDWI spectral index calculation foundation
* NumPy-based spectral index processing independent from image processing
* Spectral water detection using Sentinel-2 Green and NIR bands
* NDWI threshold-based water mask generation
* Spectral water coverage calculation
* Compatible `WaterDetectionResult` integration
* Spectral detector adapter for batch processing integration
* Strategy-compatible spectral detection architecture alongside RGB-based detection
* Automated spectral water detection tests
* Automated spectral batch integration tests
* NoData-aware spectral water detection
* Exclusion of invalid raster pixels from spectral water masks
* Exclusion of invalid raster pixels from water coverage statistics
* Validation of spectral validity-mask dimensions
* Safe handling of rasters without valid pixels

### GeoTIFF Information Panel

FloodVision provides visible geospatial metadata directly in the desktop application.

When browsing a processed GeoTIFF result, the GeoTIFF Information Panel automatically displays:

* Coordinate Reference System (CRS)
* EPSG code
* Raster width and height
* Number of raster bands
* Pixel resolution
* NoData value
* Raster bounds

For standard images without geospatial metadata, the panel displays a neutral information state.

The panel is implemented as a dedicated PySide6 dock widget and automatically updates when navigating between processed image pairs.

### Reporting

* CSV report generation
* Comparison images
* Water coverage statistics
* Flood increase calculation
* Batch summary
* Automatic output folder generation

### Automated Testing

* pytest test infrastructure
* pytest-qt GUI testing infrastructure
* Synthetic GeoTIFF test data
* GeoTIFF metadata loader tests
* GeoTIFF compatibility validation tests
* GeoTIFF batch integration tests
* GeoTIFF raster loader tests
* GeoTIFF image adapter tests
* Productive GeoTIFF pipeline integration tests
* GeoTIFF-to-RGB processing path tests
* GeoTIFF Information Panel tests
* GUI initial state tests
* GUI metadata display tests
* GUI non-GeoTIFF state tests
* GUI panel reset tests
* Raster pixel data tests
* Multi-band raster tests
* RGB conversion tests
* Raster data scaling tests
* NoData handling tests
* NoData masking tests
* Unsupported band configuration tests
* Unsupported GeoTIFF band configuration tests
* Non-finite raster value tests
* Error handling tests
* CRS and EPSG tests
* Floating-point tolerance tests
* Cross-platform GUI settings tests
* Automatic fallback tests for invalid machine-specific directory paths
* Georeferenced GeoTIFF export tests
* GeoTIFF CRS preservation tests
* GeoTIFF affine transform preservation tests
* GeoTIFF raster dimension preservation tests
* GeoTIFF 0/255 flood mask value tests
* GeoTIFF export integration tests
* Multispectral band selection tests
* Four-band GeoTIFF integration tests
* Sentinel-2 band metadata tests
* Parameterized Sentinel-2 band metadata tests
* Sentinel-2 band index conversion tests
* Raster-aware Sentinel-2 band index resolution tests
* GeoTIFF band description loading tests
* Partial Sentinel-2 band description handling tests
* Batch integration tests for partially missing Sentinel-2 band descriptions
* Sentinel-2 band-description-based RGB selection integration tests
* Missing Sentinel-2 RGB band validation tests
* NDWI calculation tests
* MNDWI calculation tests
* Spectral band extraction tests
* Spectral water detection tests
* Spectral detector integration tests
* Spectral batch processing integration tests
* Valid-mask shape validation tests
* Invalid-pixel exclusion tests
* Fully masked raster handling tests
* Complete regression test suite with 175 passing tests
* End-to-end Sentinel-2 Before/After batch integration test
* Productive spectral detector routing test
* Georeferenced spectral flood mask export validation

---

## Technologies

* Python 3.12
* PySide6
* OpenCV
* NumPy
* Pillow
* Matplotlib
* PyYAML
* Rasterio
* pytest
* pytest-qt
* Ruff

---

## Installation

```bash
git clone git@github.com:robpi82/FloodVision.git
cd FloodVision

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Development Dependencies

To install the development and testing dependencies:

```bash
pip install -r requirements-dev.txt
```

The development dependencies include:

* pytest
* pytest-qt
* Ruff

---

## Run

### Desktop GUI

```bash
python gui_main.py
```

### Command Line

```bash
python main.py
```

---

## Tests

Run the complete automated test suite:

```bash
python -m pytest -v
```

Current development status:

```text
174 passed, 5 warnings
```

---

## Folder Structure

```text
FloodVision
│
├── assets/
│
├── data/
│   ├── before/
│   ├── after/
│   ├── output/
│   ├── processed/
│   └── raw/
│
├── docs/
│   └── screenshots/
│
├── src/
│   ├── gui/
│   │   ├── app_settings.py
│   │   ├── folder_field.py
│   │   ├── geotiff_info_panel.py
│   │   ├── image_view.py
│   │   ├── log_console.py
│   │   ├── log_handler.py
│   │   ├── main_window.py
│   │   ├── navigator.py
│   │   ├── settings_dialog.py
│   │   ├── statistics_panel.py
│   │   ├── summary_dialog.py
│   │   ├── theme.py
│   │   └── worker.py
│   │
│   ├── batch_processor.py
│   ├── change_detection.py
│   ├── config.py
│   ├── exceptions.py
│   ├── geotiff_compatibility.py
│   ├── geotiff_export.py
│   ├── geotiff_image_adapter.py
│   ├── geotiff_loader.py
│   ├── geotiff_raster_loader.py
│   ├── image_loader.py
│   ├── mask_generator.py
│   ├── report_generator.py
│   ├── sentinel2_band_resolver.py
│   ├── sentinel2_bands.py
│   ├── spectral_band_extractor.py
│   ├── spectral_detector.py
│   ├── spectral_detector_adapter.py
│   ├── spectral_indices.py
│   ├── spectral_water_detection.py
│   ├── stretch.py
│   ├── utils.py
│   ├── visualization.py
│   └── water_detection.py
│
├── tests/
│   ├── conftest.py
│   ├── test_app_settings.py
│   ├── test_batch_geotiff_integration.py
│   ├── test_geotiff_compatibility.py
│   ├── test_geotiff_export.py
│   ├── test_geotiff_image_adapter.py
│   ├── test_geotiff_info_panel.py
│   ├── test_geotiff_loader.py
│   ├── test_geotiff_raster_loader.py
│   ├── test_multispectral_config.py
│   ├── test_sentinel2_band_resolver.py
│   ├── test_sentinel2_bands.py
│   ├── test_spectral_band_extractor.py
│   ├── test_spectral_batch_integration.py
│   ├── test_spectral_detector.py
│   ├── test_spectral_indices.py
│   ├── test_spectral_water_detection.py
│   └── test_stretch.py
│
├── gui_main.py
├── main.py
├── config.yaml
├── requirements.txt
├── requirements-dev.txt
├── CHANGELOG.md
├── LICENSE
└── README.md
```

---

## Screenshots

### Desktop Application

![FloodVision Main Window](docs/screenshots/main_window_dark.png)

### Flood Detection Analysis

![FloodVision Comparison](docs/screenshots/comparison.png)

### Flood Overlay Visualization

![FloodVision Overlay](docs/screenshots/overlay.png)

---

## Stable Release

### Version 0.8.0

The current stable release includes:

* Complete GeoTIFF support foundation
* Rasterio integration
* GeoTIFF metadata extraction
* Coordinate Reference System (CRS) and EPSG extraction
* Raster bounds and pixel resolution extraction
* GeoTIFF pair compatibility validation
* Automatic spatial compatibility checks
* GeoTIFF raster data loading
* Single-band and multi-band raster support
* NoData-aware raster processing
* GeoTIFF image adapter
* Three-band raster to RGB image conversion
* Productive GeoTIFF processing pipeline
* GeoTIFF Information Panel
* Automatic geospatial metadata display
* Georeferenced GeoTIFF flood mask export
* Preservation of CRS, affine transform, raster dimensions, and spatial bounds
* GIS-ready flood detection results
* Automated GeoTIFF testing
* Real-world GeoTIFF validation tooling
* Existing PNG and JPEG workflows preserved

---

## Current Development

### Version 0.9.0

**Sentinel-2 & Multispectral Raster Foundation**

Currently implemented on the development branch:

* Multispectral GeoTIFF band selection
* Configurable source band selection
* User-configurable multispectral RGB band selection via `config.yaml`
* Validation of multispectral RGB band configurations
* Validation of band count, integer types, and non-negative band indices
* Productive multispectral GeoTIFF processing in the batch workflow
* Automatic multi-band GeoTIFF raster loading for water detection
* Preservation of existing PNG, JPEG, and three-band GeoTIFF workflows
* Sentinel-2 spectral band metadata foundation
* Immutable Sentinel-2 band metadata model
* Complete Sentinel-2 band metadata catalog
* Metadata definitions for B02, B03, B04, B05, B06, B07, B08, B8A, B09, B10, B11, and B12
* Automatic Sentinel-2 RGB band selection from GeoTIFF band descriptions
* Validation of required Sentinel-2 RGB bands
* Support for partially missing Sentinel-2 band descriptions
* NDWI spectral index calculation
* MNDWI spectral index calculation foundation
* Spectral water detection using Sentinel-2 Green and NIR bands
* NDWI threshold-based flood mask generation
* NoData-aware spectral water detection
* Invalid-pixel exclusion from masks and coverage calculations
* Spectral detection adapter integrated into the processing architecture
* Automated spectral processing tests
* 175 automated tests currently passing
* Productive Sentinel-2 Before/After batch workflow
* Automatic routing of Sentinel-2 GeoTIFFs to the spectral detector
* End-to-end spectral flood change detection
* Georeferenced export of spectral flood masks

Remaining development for v0.9.0:

* Complete Sentinel-2 Before/After integration testing
* Verify that PNG/JPEG and HSV detection remain unchanged
* Manual desktop application test
* Final README and CHANGELOG review
* Release v0.9.0

---

## Roadmap

### Version 0.8.0

**GeoTIFF & GIS Raster Foundation — Released**

Completed development:

* GeoTIFF support foundation
* Rasterio integration
* Coordinate Reference System metadata
* Geospatial metadata extraction
* GeoTIFF pair compatibility validation
* Batch processing integration for GeoTIFF compatibility validation
* GeoTIFF raster data loading
* GeoTIFF image adapter
* Productive GeoTIFF processing pipeline integration
* GeoTIFF Information Panel
* Automated GeoTIFF GUI tests
* Georeferenced GeoTIFF flood mask export
* Preservation of CRS, affine transform, raster dimensions, and spatial bounds
* GIS-ready single-band flood classification output
* Automated GeoTIFF export tests
* Manual end-to-end testing with synthetic GeoTIFF datasets
* Real-world GeoTIFF validation tooling
* Full regression testing

### Version 0.9.0

**Sentinel-2 & Multispectral Raster Foundation — In Development**

Completed:

* Multispectral GeoTIFF processing foundation
* Sentinel-2 band metadata system
* Automatic band resolution from raster descriptions
* NDWI and MNDWI spectral index foundation
* Spectral water detection foundation
* NoData-aware spectral water classification
* Invalid-pixel exclusion from spectral masks and coverage statistics
* Integration architecture for spectral flood detection
* Automated regression and integration testing
* 175 automated tests
* Complete synthetic Sentinel-2 Before/After integration test
* Productive spectral detection routing in batch processing
* Georeferenced spectral flood mask export validation

Remaining development:

* Complete Sentinel-2 Before/After integration test
* Verify legacy RGB and HSV workflows
* Manual desktop application test
* Final documentation review
* Complete Sentinel-2 Before/After integration test
* Release v0.9.0

### Version 0.10.0

**Operational Sentinel-2 Flood Analysis**

Planned development:

* Productive selection between NDWI and MNDWI
* Processing of real Sentinel-2 Level-2A products
* Sentinel-2 imagery import workflow
* Spectral flood visualizations
* NDWI and MNDWI result layers
* Multi-index flood classification
* GIS-ready spectral analysis outputs
* Multi-temporal flood monitoring

### Version 0.11.0

**Advanced Raster Processing**

Planned development:

* Landsat imagery support
* Additional spectral indices
* Support for additional satellite imagery sources
* Performance improvements for large raster datasets
* Extended GIS export capabilities
* Advanced raster processing workflows

### Version 1.0.0

**AI-Assisted Flood Segmentation**

Planned development:

* AI-based flood segmentation
* Semantic segmentation models
* U-Net integration
* PyTorch support
* Model training and evaluation
* Combination of classical, spectral, and AI-based detection approaches

---

## Author

Robert Piotrowicz

GitHub Profile:

https://github.com/robpi82

---

## License

MIT License

Educational and portfolio project.
