from qgis.PyQt.QtWidgets import QDialog, QWidget, QVBoxLayout, QLineEdit, QTextEdit, QGraphicsTextItem
from qgis.PyQt.QtWidgets import QListWidget, QListWidgetItem, QMenu, QAction, QMessageBox
from qgis.gui import QgsMapLayerComboBox, QgsRasterBandComboBox
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor, QIntValidator
from PyQt5.QtWidgets import QDialogButtonBox, QGridLayout, QComboBox, QFormLayout, QVBoxLayout, QLabel, QPushButton, QMainWindow
import pyqtgraph as pg
from pyqtgraph.parametertree import interact, Parameter, ParameterTree
from statmagic_backend.dev.match_stack_raster_tools import drop_selected_layers_from_raster
from qgis.core import QgsRasterLayer, QgsProject, QgsVectorLayer, QgsProject, QgsMapLayerProxyModel
from qgis.core import QgsGeometry, QgsPoint, QgsCoordinateTransform
from pathlib import Path
import rasterio as rio
from rasterio.windows import Window
import numpy as np
import geopandas as gpd


class RasterHistQtPlot(QDialog):

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        super(RasterHistQtPlot, self).__init__(parent)
        QDialog.setWindowTitle(self, "Raster Histogram")

        # Create plot area
        self.plot_widget = pg.PlotWidget()
        self.pltItem: pg.PlotItem = self.plot_widget.plotItem
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.pltItem.addItem(self.vLine, ignoreBounds=True)
        self.pltItem.addItem(self.hLine, ignoreBounds=True)
        #self.plot_widget.sigSceneMouseMoved(self.mouseMoved)
        #self.plot_widget.mouseMoveEvent(self.mouseMoved)
        #self.plot_widget.mouseMoveEvent(self.mouseMoved)
        #self.plot_widget.sigSceneMouseMoved(self.mouseMoved)

        #### Create histogram parameter input panel
        # Choose raster layer
        raster_label = QLabel('Raster Layer')
        self.raster_selection_box = QgsMapLayerComboBox(self)
        self.raster_selection_box.setShowCrs(True)
        self.raster_selection_box.setFilters(QgsMapLayerProxyModel.RasterLayer)

        # Choose band
        band_label = QLabel("Band")
        self.raster_band_input = QgsRasterBandComboBox(self)
        self.raster_band_input.setLayer(self.raster_selection_box.currentLayer())
        self.raster_selection_box.layerChanged.connect(self.raster_band_input.setLayer)

        # Choose vector layer defining AOI with first feature
        aoi_label = QLabel('AOI')
        self.aoi_selection_box = QgsMapLayerComboBox(self)
        self.aoi_selection_box.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.aoi_selection_box.setShowCrs(True)
        self.aoi_selection_box.setFixedWidth(300)
        self.highlightFeature()
        self.aoi_selection_box.layerChanged.connect(self.highlightFeature)

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

        # Text box to display statistics
        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)

        # Create for input panel
        self.layer_select_layout = QFormLayout()
        self.layer_select_layout.addRow(raster_label, self.raster_selection_box)
        self.layer_select_layout.addRow(band_label, self.raster_band_input)
        self.layer_select_layout.addRow(aoi_label, self.aoi_selection_box)
        self.layer_select_layout.addRow(bins_label, self.num_bins_input)
        self.layer_select_layout.addWidget(self.run_hist_btn)
        self.layer_select_layout.addWidget(self.text_box)
        ####

        # Populate dialog layout
        self.layout = QGridLayout(self)
        self.layout.addWidget(self.plot_widget, 0, 0)
        self.layout.addLayout(self.layer_select_layout, 0, 1)
        self.setLayout(self.layout)

    def mouseMoved(self, evt):
        print("Mouse moved")
        print(evt)

    def highlightFeature(self):
        aoi: QgsVectorLayer = self.aoi_selection_box.currentLayer()
        l = self.iface.setActiveLayer(aoi)
        self.iface.mainWindow().findChild(QAction, 'mActionDeselectAll').trigger()
        aoi.selectByIds([0])

    def plot_raster_histogram(self):
        # The correct way to compute a histogram should be with the QGIS histogram provider, but the function
        # histogramVector is broken in QGIS 3.34
        # https://github.com/qgis/QGIS/issues/29700
        # So we do a silly thing - get the source of the selected layer, read it with rasterio, and compute our histogram that way

        # Check that the user has selected a valid raster layer
        if self.raster_selection_box.currentLayer() is None:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid raster layer for the histogram")
            msgBox.exec()
            return
        if self.aoi_selection_box.currentLayer() is None:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid vector / polygon layer to provide an AOI for the histogram")
            msgBox.exec()
            return
        if self.raster_band_input.currentBand() is None:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid raster band for the histogram")
            msgBox.exec()
            return
        if self.num_bins_input.text() == '':
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid number of bins for the histogram")
            msgBox.exec()
            return

        print(f'Creating histogram of layer {self.raster_selection_box.currentLayer()}, band {self.raster_band_input.currentBand()}, within AOI {self.aoi_selection_box.currentLayer()}, #bins = {self.num_bins_input.text()}')

        # Grab the user specified parameters from the panel widgets
        raster: QgsRasterLayer = self.raster_selection_box.currentLayer()
        band = self.raster_band_input.currentBand()
        aoi: QgsVectorLayer = self.aoi_selection_box.currentLayer()

        # Assume the bounding box of the first feature of the AOI layer is the AOI
        extents_feature = aoi.getFeature(0)
        extents_rect = extents_feature.geometry().boundingBox()

        print(f'Raster (height,  width) = ({raster.height()}, {raster.width()}), # bands = {raster.bandCount()}')
        print(f'Reading raster from {raster.source()}')

        # Open the raster layer with rasterio since the built-in QGIS histogram function is broken
        raster_path = Path(raster.source())
        try:
            with rio.open(raster_path) as ds:
                # Get the coordinates of the AOI feature in the same CRS as the raster
                print("Constructing coordinate transform")
                min_corner = QgsPoint(extents_rect.xMinimum(), extents_rect.yMinimum())
                max_corner = QgsPoint(extents_rect.xMaximum(), extents_rect.yMaximum())
                raster_crs = raster.crs()
                aoi_crs = aoi.crs()
                tr = QgsCoordinateTransform(aoi_crs, raster_crs, QgsProject.instance())

                print("Applying transform")
                min_corner.transform(tr)
                max_corner.transform(tr)
                min_row, min_col = ds.index(min_corner.x(), min_corner.y())
                max_row, max_col = ds.index(max_corner.x(), max_corner.y())
                print(min_row, min_col, max_row, max_col, max_col-min_col, max_row-min_row)

                # Read the raster band data from within the AOI
                print(f'Creating Window({min(min_col, max_col)},{min(min_row, max_row)},{abs(max_col-min_col)},{abs(max_row-min_row)})')
                win = Window(min(min_col, max_col), min(min_row, max_row), abs(max_col-min_col), abs(max_row-min_row))
                print("Reading band within window")
                band_data = ds.read(band, window=win)

                print("Computing histogram")
                hist, bin_edges = np.histogram(band_data,
                                               range=(np.nanmin(band_data), np.nanmax(band_data)),
                                               bins=int(self.num_bins_input.text()), density=False)

                print("Plotting histogram")
                bar_chart = pg.BarGraphItem(x0=bin_edges[:-1], x1=bin_edges[1:], height=hist, pen='w', brush=(0, 0, 255, 150))
                self.pltItem.clear()
                self.pltItem.addItem(bar_chart)
                self.pltItem.setTitle(raster.name())
                self.pltItem.setLabel(axis='left', text='Pixel Counts')
                self.pltItem.setLabel(axis='bottom', text="Band "+str(self.raster_band_input.currentBand()))

                print("Display statistics")
                self.text_box.setText(f'NumPixels = {band_data.size}\nNumNaN = {np.count_nonzero(np.isnan(band_data))}\nMin = {np.nanmin(band_data)}\nMax = {np.nanmax(band_data)}\nMean = {np.nanmean(band_data)}\nMedian = {np.nanmedian(band_data)}\nVar = {np.nanvar(band_data)}')
        except:
            msgBox = QMessageBox()
            msgBox.setText("You must a locally available raster layer for the histogram")
            msgBox.exec()
            return
