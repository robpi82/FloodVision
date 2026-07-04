# 🌊 FloodVision

Professional Flood Detection & Flood Change Detection using Python, OpenCV and a modern Desktop GUI.

FloodVision is a portfolio project developed to automatically detect newly flooded areas by comparing before and after aerial or satellite images. The application provides a graphical desktop interface, automatic image processing and detailed analysis reports.

---

# Features

## Flood Detection

- Automatic water detection
- Before / After comparison
- New flood area detection
- Overlay visualization
- Flood mask generation
- Batch processing
- CSV report export
- Automatic statistics
- Robust error handling

## Desktop GUI

- Modern PySide6 interface
- Image preview
- Processing progress
- Statistics panel
- Summary dialog
- Log console
- Folder navigator
- Settings dialog

---

# Technologies

- Python 3.12
- OpenCV
- NumPy
- Pillow
- Matplotlib
- PySide6
- PyYAML

---

# Installation

```bash
git clone git@github.com:robpi82/FloodVision.git
cd FloodVision

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

---

# Run

Console version

```bash
python main.py
```

Desktop GUI

```bash
python gui_main.py
```

---

# Folder Structure

```text
FloodVision/

├── data/
│   ├── before/
│   ├── after/
│   ├── output/
│   └── raw/
│
├── src/
│   ├── gui/
│   ├── water_detection.py
│   ├── change_detection.py
│   ├── image_loader.py
│   ├── mask_generator.py
│   ├── report_generator.py
│   ├── visualization.py
│   ├── batch_processor.py
│   ├── config.py
│   └── exceptions.py
│
├── assets/
├── gui_main.py
├── main.py
├── config.yaml
├── requirements.txt
└── README.md
```

---

# Current Version

## Version 0.6.1

### Implemented

- Water detection
- Flood change detection
- Batch processing
- CSV export
- Overlay visualization
- Automatic mask generation
- Desktop GUI
- Image viewer
- Statistics panel
- Summary dialog
- Log console
- Navigation panel
- Settings dialog

---

# Roadmap

## Version 0.7

- GeoTIFF support
- Sentinel-2 imagery
- Landsat imagery
- Raster processing

## Version 0.8

- AI flood segmentation
- Deep Learning
- Model evaluation

## Version 0.9

- Interactive map
- GeoJSON export
- Shapefile export
- GIS integration

## Version 1.0

- Professional FloodVision release
- Complete documentation
- Example datasets
- Installer for Windows and macOS

---

# Author

Robert Piotrowicz

GitHub:
https://github.com/robpi82

---

# License

Educational and portfolio project.

Developed for learning Python, Computer Vision, GIS and Remote Sensing.