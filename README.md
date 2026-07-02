# 🌊 FloodVision

**Professional Flood Detection & Flood Change Detection using Python,
OpenCV and Computer Vision**

FloodVision is a portfolio project that detects water surfaces in images
and compares satellite or aerial images taken at different times to
identify newly flooded areas.

## Features

-   Water detection using HSV color segmentation
-   Flood change detection (Before / After comparison)
-   Batch processing
-   CSV report generation
-   Overlay visualization
-   Robust error handling
-   Modular architecture

## Technologies

-   Python 3.12
-   OpenCV
-   NumPy
-   Pillow
-   Matplotlib

## Installation

``` bash
git clone git@github.com:robpi82/FloodVision.git
cd FloodVision
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

``` bash
python main.py
```

## Folder Structure

``` text
FloodVision/
├── data/
├── src/
├── main.py
├── requirements.txt
└── README.md
```

## Current Version

Version **0.4**

Implemented: - Water detection - Flood change detection - Batch
processing - CSV reports

Planned: - Machine Learning - GeoTIFF support - Sentinel-2 integration -
Streamlit web interface

## Author

Robert Piotrowicz

GitHub: https://github.com/robpi82

## License

Educational and portfolio project.
