from qgis.PyQt.QtWidgets import QDialog, QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMenu, QAction
from qgis.gui import QgsMapLayerComboBox, QgsRasterBandComboBox
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor
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

        ###
        raster_label = QLabel('Raster Layer')
        self.raster_selection_box = QgsMapLayerComboBox()
        self.raster_selection_box.setFilters(QgsMapLayerProxyModel.RasterLayer)

        band_label = QLabel("Band")
        self.raster_band_input = QgsRasterBandComboBox()
        self.raster_band_input.setLayer(self.raster_selection_box.currentLayer())
        self.raster_selection_box.layerChanged.connect(self.raster_band_input.setLayer)

        aoi_label = QLabel('AOI')
        self.aoi_selection_box = QgsMapLayerComboBox()
        self.aoi_selection_box.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.aoi_selection_box.setFixedWidth(300)

        self.run_hist_btn = QPushButton()
        self.run_hist_btn.setText('Plot Histogram')
        self.run_hist_btn.clicked.connect(self.plot_raster_histogram)

        self.layer_select_layout = QFormLayout()
        self.layer_select_layout.addRow(raster_label, self.raster_selection_box)
        self.layer_select_layout.addRow(band_label, self.raster_band_input)
        self.layer_select_layout.addRow(aoi_label, self.aoi_selection_box)
        self.layer_select_layout.addWidget(self.run_hist_btn)
        ####

        self.layout = QGridLayout()
        self.layout.addWidget(self.plot_widget, 0, 0)
        self.layout.addLayout(self.layer_select_layout, 0, 1)
        self.setLayout(self.layout)

    def plot_raster_histogram(self):
        # The correct way to compute a histogram should be with the QGIS histogram provider, but the function
        # histogramVector is broken in QGIS 3.34
        # https://github.com/qgis/QGIS/issues/29700
        # So we do a silly thing - get the source of the selected layer, read it with rasterio, and compute our histogram that way

        print(self.raster_selection_box.currentLayer())
        print(self.aoi_selection_box.currentLayer())
        print(self.raster_band_input.currentBand())
        #print(self.raster_selection_box.currentLayer().bandName(self.raster_band_input.currentBand()))

        raster: QgsRasterLayer = self.raster_selection_box.currentLayer()
        aoi: QgsVectorLayer = self.aoi_selection_box.currentLayer()
        extents_feature = aoi.getFeature(0)
        extents_rect = extents_feature.geometry().boundingBox()
        provider = raster.dataProvider()

        print(raster.height(), raster.width())
        print(raster.name())
        print(raster.bandCount())
        print(provider.bandStatistics(1))
        print(provider.histogram(bandNo=1, extent=extents_rect))
        #provider.block()
        #provider.initHistogram()
        hist = provider.histogram(1)
        print(hist.minimum, hist.maximum, hist.binCount)
        print(hist)

        block = provider.block(bandNo=1, boundingBox=raster.extent(), width=raster.width(), height=raster.height())
        print(block.width(), block.height(), block.dataType())
        print(raster.source())
        raster_path = Path(raster.source())

        with rio.open(raster_path) as ds:
            print("Reading raster")
            band1 = ds.read(1)
            #band1 = np.random.normal(size=(ds.height, ds.width))
            print("Computing histogram")
            hist, bin_edges = np.histogram(band1, range=(np.nanmin(band1), np.nanmax(band1)), bins=10, density=True)
            print(hist, bin_edges)

            # make interesting distribution of values
            #vals = np.hstack([np.random.normal(size=500), np.random.normal(size=260, loc=4)])
            ## compute standard histogram
            #hist, bin_edges = np.histogram(vals, bins=np.linspace(-3, 8, 40))

            #self.plot_widget.plotItem
            print("Making barchart")
            bar_chart = pg.BarGraphItem(x0=bin_edges[:-1], x1=bin_edges[1:], height=hist, pen='w', brush=(0, 0, 255, 150))
            print("Clearing pltItem")
            self.pltItem.clear()
            print("Adding to pltItem")
            self.pltItem.addItem(bar_chart)
            self.pltItem.setTitle(raster.title())
            self.pltItem.setLabel(axis='bottom', text='Pixel Counts')
            self.pltItem.setLabel(axis='left', text=str(self.raster_band_input.currentBand()))

        #print(hist.histogramVector)


