# 🌊 FloodVision

**Professional Flood Detection & Flood Change Detection using Python, OpenCV and Computer Vision**

FloodVision is a computer vision project that detects water surfaces in aerial or satellite imagery and compares images captured at different times to identify newly flooded areas.

The project is being developed step by step as a professional portfolio application and will eventually support GIS data, satellite imagery, AI-based segmentation, and interactive visualization.

---

# Features

## Current Features (Version 0.5)

- Water detection using HSV color segmentation
- Flood change detection (Before / After comparison)
- Batch processing of multiple image pairs
- Automatic CSV report generation
- Overlay visualization
- Automatic mask generation
- Robust error handling
- Detailed logging
- Modular object-oriented architecture

---

# Technologies

- Python 3.12
- OpenCV
- NumPy
- Pillow
- Matplotlib

---

# Installation

```bash
git clone https://github.com/robpi82/FloodVision.git
cd FloodVision

python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt
```

---

# Run

```bash
python main.py
```

---

# Folder Structure

```text
FloodVision/
│
├── data/
│   ├── before/
│   ├── after/
│   └── output/
│
├── src/
│   ├── batch_processor.py
│   ├── change_detection.py
│   ├── image_loader.py
│   ├── mask_generator.py
│   ├── report_generator.py
│   ├── visualization.py
│   ├── water_detection.py
│   ├── config.py
│   ├── exceptions.py
│   └── utils.py
│
├── logs/
├── main.py
├── requirements.txt
└── README.md
```

---

# Example Workflow

1. Place "before" images inside:

```text
data/before/
```

2. Place matching "after" images inside:

```text
data/after/
```

3. Run:

```bash
python main.py
```

4. FloodVision automatically:

- detects water in each image
- compares before and after images
- calculates newly flooded areas
- creates masks
- creates overlays
- exports comparison images
- generates a CSV report

Results are stored in:

```text
data/output/
```

---

# Current Version

## Version 0.5

### Implemented

- Water detection
- Flood change detection
- Batch processing
- Automatic report generation
- CSV export
- Overlay visualization
- Image pairing
- Automatic mask generation
- Robust error handling
- Logging
- Modular architecture

### Planned (Roadmap)

### Version 0.6
- Modern desktop GUI (PySide6)
- Drag & Drop support
- Progress bar
- Image preview
- Settings dialog

### Version 0.7
- GeoTIFF support
- Sentinel-2 satellite imagery
- Landsat support
- Raster processing

### Version 0.8
- AI flood segmentation using U-Net
- Deep learning inference
- Model evaluation

### Version 0.9
- Interactive map visualization
- GIS export
- Shapefile export
- GeoJSON export

### Version 1.0
- Professional desktop application
- Advanced reporting
- PDF export
- Excel export
- Complete documentation
- Unit tests
- Portfolio-ready release

---

# Author

**Robert Piotrowicz**

GitHub:

https://github.com/robpi82

---

# License

Educational and portfolio project.