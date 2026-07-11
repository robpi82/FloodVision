<p align="center">
  <img src="docs/screenshots/floodvision_banner.png" alt="FloodVision Banner" width="100%">
</p>

# 🌊 FloodVision

![Stable Version](https://img.shields.io/badge/stable-v0.8.0-red)
![Development Version](https://img.shields.io/badge/development-v0.9.0-yellow)
![Python](https://img.shields.io/badge/python-3.12-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.11-green)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-pink)
![Tests](https://img.shields.io/badge/tests-124%20passed-brightgreen)
![License](https://img.shields.io/badge/license-MIT-success)
![Status](https://img.shields.io/badge/status-active-brightgreen)

Professional desktop application for flood detection using computer vision, image processing, and geospatial raster analysis.

FloodVision compares two images of the same location ("Before" and "After") and automatically detects newly flooded areas.

The current stable release provides a complete GeoTIFF and GIS raster processing workflow. Development is now focused on multispectral raster processing and Sentinel-2 support.

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
* Metadata definitions for B02, B03, B04, B05, B06, B07, B08, and B8A
* Native spatial resolution metadata for supported Sentinel-2 bands
* Normalized and validated Sentinel-2 band lookup
* Foundation for future Sentinel-2 imagery support
* Foundation for future non-RGB raster processing workflows

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
124 passed, 3 warnings
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
│   ├── geotiff_image_adapter.py
│   ├── geotiff_loader.py
│   ├── geotiff_raster_loader.py
│   ├── image_loader.py
│   ├── mask_generator.py
│   ├── report_generator.py
│   ├── sentinel2_bands.py
│   ├── utils.py
│   ├── visualization.py
│   └── water_detection.py
│
├── tests/
│   ├── conftest.py
│   ├── test_batch_geotiff_integration.py
│   ├── test_geotiff_compatibility.py
│   ├── test_geotiff_image_adapter.py
│   ├── test_geotiff_info_panel.py
│   ├── test_geotiff_loader.py
│   ├── test_geotiff_raster_loader.py
│   └── test_sentinel2_bands.py
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
* Support for selecting arbitrary raster bands for RGB image generation
* User-configurable multispectral RGB band selection via `config.yaml`
* Validation of multispectral RGB band configurations
* Validation of band count, integer types, and non-negative band indices
* Productive multispectral GeoTIFF processing in the batch workflow
* Automatic multi-band GeoTIFF raster loading for water detection
* Integration of configured RGB band selection into productive flood processing
* Preservation of existing PNG, JPEG, and three-band GeoTIFF workflows
* Sentinel-2 spectral band metadata foundation
* Immutable Sentinel-2 band metadata model
* Metadata definitions for B02, B03, B04, B05, B06, B07, B08, and B8A
* Native spatial resolution metadata for supported Sentinel-2 bands
* Normalized and validated Sentinel-2 band lookup
* Automated integration testing for four-band GeoTIFF processing
* Automated tests for Sentinel-2 band metadata
* 124 automated tests currently passing

Planned development:

* Sentinel-2 imagery support
* Extended multispectral GeoTIFF raster loading
* Support for additional Sentinel-2 spectral bands
* Integration of Sentinel-2 band metadata into raster processing workflows
* Support for non-RGB raster workflows
* Additional automated tests for multispectral raster processing

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

Currently implemented on the development branch:

* Multispectral GeoTIFF band selection
* Configurable raster band selection
* User-configurable RGB band selection via `config.yaml`
* Validation of multispectral band configurations
* Validation of band count, integer types, and non-negative band indices
* Productive multispectral GeoTIFF processing in the batch workflow
* Automatic multi-band GeoTIFF raster loading for water detection
* Integration of configured RGB band selection into productive flood processing
* Preservation of existing PNG, JPEG, and three-band GeoTIFF workflows
* Sentinel-2 spectral band metadata foundation
* Immutable Sentinel-2 band metadata model
* Metadata definitions for B02, B03, B04, B05, B06, B07, B08, and B8A
* Native spatial resolution metadata for supported Sentinel-2 bands
* Normalized and validated Sentinel-2 band lookup
* Automated integration testing for four-band GeoTIFF processing
* Automated tests for Sentinel-2 band metadata
* 124 automated tests

Planned development:

* Sentinel-2 imagery support
* Extended multispectral GeoTIFF raster loading
* Support for additional Sentinel-2 spectral bands
* Integration of Sentinel-2 band metadata into raster processing workflows
* Support for non-RGB raster workflows
* Additional automated tests for multispectral raster processing

### Version 0.10.0

**NDWI Water Detection**

Planned development:

* NDWI-based water detection
* Green and Near-Infrared band processing
* Configurable NDWI thresholds
* NDWI raster visualization
* NDWI flood change detection
* Georeferenced NDWI output products

### Version 0.11.0

**Advanced Raster Processing**

Planned development:

* Landsat imagery support
* Extended multispectral workflows
* Advanced raster processing
* Additional GIS export capabilities
* Performance improvements for large raster datasets

### Version 1.0.0

**AI Flood Segmentation**

Planned development:

* AI-based flood segmentation
* Deep Learning models
* U-Net integration
* PyTorch support

---

## Author

Robert Piotrowicz

GitHub Profile:

https://github.com/robpi82

---

## License

MIT License

Educational and portfolio project.
