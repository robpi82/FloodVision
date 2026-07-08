"""GeoTIFF metadata display panel for the FloodVision GUI."""

from pathlib import Path

from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from src.geotiff_loader import GeoTiffLoader


class GeoTiffInfoPanel(QWidget):
    """Display spatial metadata for the currently selected GeoTIFF."""

    def __init__(self, loader: GeoTiffLoader | None = None, parent=None) -> None:
        super().__init__(parent)
        self._loader = loader or GeoTiffLoader()
        self._status = QLabel()
        self._status.setWordWrap(True)
        self._values = {name: QLabel("—") for name in (
            "CRS", "EPSG", "Size", "Bands", "Resolution", "NoData", "Bounds"
        )}
        for label in self._values.values():
            label.setWordWrap(True)
            label.setTextInteractionFlags(label.textInteractionFlags())

        form = QFormLayout()
        for name, label in self._values.items():
            form.addRow(f"{name}:", label)

        layout = QVBoxLayout(self)
        layout.addWidget(self._status)
        layout.addLayout(form)
        layout.addStretch(1)
        self.clear()

    def clear(self) -> None:
        """Reset the panel to its idle state."""
        self._status.setText("No GeoTIFF selected.")
        for label in self._values.values():
            label.setText("—")

    def show_file(self, path: Path) -> None:
        """Load and display metadata when *path* is a GeoTIFF."""
        path = Path(path)
        if not self._loader.is_geotiff(path):
            self.clear()
            self._status.setText("Current image is not a georeferenced GeoTIFF.")
            return

        metadata = self._loader.read_metadata(path)
        self._status.setText(path.name)
        self._values["CRS"].setText(str(metadata.crs) if metadata.crs else "None")
        self._values["EPSG"].setText(str(metadata.epsg) if metadata.epsg else "None")
        self._values["Size"].setText(f"{metadata.width} × {metadata.height} px")
        self._values["Bands"].setText(str(metadata.band_count))
        self._values["Resolution"].setText(
            f"{metadata.resolution[0]:g} × {metadata.resolution[1]:g}"
        )
        self._values["NoData"].setText(
            str(metadata.nodata) if metadata.nodata is not None else "None"
        )
        self._values["Bounds"].setText(
            ", ".join(f"{value:g}" for value in metadata.bounds)
        )
