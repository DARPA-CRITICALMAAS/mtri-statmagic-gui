from qgis.PyQt.QtWidgets import QDialog, QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMenu, QAction
from qgis.gui import QgsMapLayerComboBox, QgsRasterBandComboBox
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor, QIntValidator
from PyQt5.QtWidgets import QDialogButtonBox, QGridLayout, QComboBox, QFormLayout, QVBoxLayout, QLabel, QPushButton, QMainWindow
import pyqtgraph as pg
from pyqtgraph.parametertree import interact, Parameter, ParameterTree
from statmagic_backend.dev.match_stack_raster_tools import drop_selected_layers_from_raster
from qgis.core import QgsRasterLayer, QgsProject, QgsVectorLayer, QgsProject, QgsMapLayerProxyModel
from pathlib import Path
import rasterio as rio
import numpy as np


class RasterHistQtPlot(QDialog):

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        super(RasterHistQtPlot, self).__init__(parent)
        QDialog.setWindowTitle(self, "Raster Histogram")

        # Create plot area
        self.plot_widget = pg.PlotWidget()
        self.pltItem: pg.PlotItem = self.plot_widget.plotItem

        #### Create histogram parameter input panel
        # Choose raster layer
        raster_label = QLabel('Raster Layer')
        self.raster_selection_box = QgsMapLayerComboBox(self)
        self.raster_selection_box.setFilters(QgsMapLayerProxyModel.RasterLayer)

        # Choose band
        band_label = QLabel("Band")
        self.raster_band_input = QgsRasterBandComboBox(self)
        self.raster_band_input.setLayer(self.raster_selection_box.currentLayer())
        self.raster_selection_box.layerChanged.connect(self.raster_band_input.setLayer)

        # Choose vector layer defining AOI with first feature
        aoi_label = QLabel('AOI')
        self.aoi_selection_box = QgsMapLayerComboBox(self)
        self.aoi_selection_box.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.aoi_selection_box.setFixedWidth(300)

        # Select number of bins in the histogram
        bins_label = QLabel("# Bins")
        self.num_bins_input = QLineEdit(self)
        validator = QIntValidator()
        validator.setRange(2, 50)
        self.num_bins_input.setValidator(validator)
        self.num_bins_input.setText("10")

        # Button to create histogram
        self.run_hist_btn = QPushButton()
        self.run_hist_btn.setText('Plot Histogram')
        self.run_hist_btn.clicked.connect(self.plot_raster_histogram)

        # Create for input panel
        self.layer_select_layout = QFormLayout()
        self.layer_select_layout.addRow(raster_label, self.raster_selection_box)
        self.layer_select_layout.addRow(band_label, self.raster_band_input)
        self.layer_select_layout.addRow(aoi_label, self.aoi_selection_box)
        self.layer_select_layout.addRow(bins_label, self.num_bins_input)
        self.layer_select_layout.addWidget(self.run_hist_btn)
        ####

        # Populate dialog layout
        self.layout = QGridLayout(self)
        self.layout.addWidget(self.plot_widget, 0, 0)
        self.layout.addLayout(self.layer_select_layout, 0, 1)
        self.setLayout(self.layout)

    def plot_raster_histogram(self):
        # The correct way to compute a histogram should be with the QGIS histogram provider, but the function
        # histogramVector is broken in QGIS 3.34
        # https://github.com/qgis/QGIS/issues/29700
        # So we do a silly thing - get the source of the selected layer, read it with rasterio, and compute our histogram that way

        print(f'Creating histogram of layer {self.raster_selection_box.currentLayer()}, band {self.raster_band_input.currentBand()}, within AOI {self.aoi_selection_box.currentLayer()}')

        raster: QgsRasterLayer = self.raster_selection_box.currentLayer()
        aoi: QgsVectorLayer = self.aoi_selection_box.currentLayer()
        band = self.raster_band_input.currentBand()
        extents_feature = aoi.getFeature(0)
        extents_rect = extents_feature.geometry().boundingBox()
        provider = raster.dataProvider()

        print(f'Raster (height,  width) = ({raster.height()}, {raster.width()}), # bands = {raster.bandCount()}')

        block = provider.block(bandNo=band, boundingBox=raster.extent(), width=raster.width(), height=raster.height())
        print(f'Reading raster from {raster.source()}')
        raster_path = Path(raster.source())

        with rio.open(raster_path) as ds:
            print("Reading band")
            band_data = ds.read(band)
            print("Computing histogram")
            hist, bin_edges = np.histogram(band_data,
                                           range=(np.nanmin(band_data), np.nanmax(band_data)),
                                           bins=int(self.num_bins_input.text()), density=True)

            print("Making barchart")
            bar_chart = pg.BarGraphItem(x0=bin_edges[:-1], x1=bin_edges[1:], height=hist, pen='w', brush=(0, 0, 255, 150))
            print("Clearing pltItem")
            self.pltItem.clear()
            print("Adding to pltItem")
            self.pltItem.addItem(bar_chart)
            print("Title:", raster.name())
            self.pltItem.setTitle(raster.name())
            self.pltItem.setLabel(axis='bottom', text='Pixel Counts')
            self.pltItem.setLabel(axis='left', text="Band "+str(self.raster_band_input.currentBand()))

