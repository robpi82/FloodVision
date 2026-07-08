from pathlib import Path
from types import SimpleNamespace

from src.gui.geotiff_info_panel import GeoTiffInfoPanel


class FakeLoader:
    def __init__(self, is_geotiff=True):
        self.result = is_geotiff

    def is_geotiff(self, path):
        return self.result

    def read_metadata(self, path):
        return SimpleNamespace(
            crs="EPSG:32632", epsg=32632, width=2048, height=1024,
            band_count=3, resolution=(10.0, 10.0), nodata=0.0,
            bounds=(500000.0, 5100000.0, 520480.0, 5110240.0),
        )


def test_initial_state(qtbot):
    panel = GeoTiffInfoPanel(FakeLoader())
    qtbot.addWidget(panel)
    assert panel._status.text() == "No GeoTIFF selected."


def test_non_geotiff_shows_neutral_message(qtbot):
    panel = GeoTiffInfoPanel(FakeLoader(False))
    qtbot.addWidget(panel)
    panel.show_file(Path("image.png"))
    assert "not a georeferenced GeoTIFF" in panel._status.text()


def test_geotiff_metadata_is_displayed(qtbot):
    panel = GeoTiffInfoPanel(FakeLoader())
    qtbot.addWidget(panel)
    panel.show_file(Path("flood.tif"))
    assert panel._status.text() == "flood.tif"
    assert panel._values["EPSG"].text() == "32632"
    assert panel._values["Size"].text() == "2048 × 1024 px"
    assert panel._values["Bands"].text() == "3"
    assert panel._values["Resolution"].text() == "10 × 10"
    assert panel._values["NoData"].text() == "0.0"


def test_clear_resets_values(qtbot):
    panel = GeoTiffInfoPanel(FakeLoader())
    qtbot.addWidget(panel)
    panel.show_file(Path("flood.tif"))
    panel.clear()
    assert panel._status.text() == "No GeoTIFF selected."
    assert all(label.text() == "—" for label in panel._values.values())
