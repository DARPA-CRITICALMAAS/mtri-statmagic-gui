from qgis.PyQt.QtWidgets import QDialog, QLineEdit, QTextEdit
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.gui import QgsMapLayerComboBox, QgsRasterBandComboBox
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QGridLayout, QFormLayout, QLabel, QPushButton, QComboBox, QSpinBox
import pyqtgraph as pg
from rasterio import RasterioIOError

from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject, QgsMapLayerProxyModel
from qgis.core import QgsPoint, QgsCoordinateTransform
from pathlib import Path
import rasterio as rio
from rasterio.windows import Window, from_bounds
from rasterio.mask import mask
from shapely import box
from shapely.wkt import loads
import numpy as np
import geopandas as gpd
from ..grab_polygon import PolygonMapTool
from ..grab_rectangle import RectangleMapTool
from ...layerops import qgis_poly_to_gdf

import logging
logger = logging.getLogger("statmagic_gui")


class RasterScatQtPlot(QDialog):

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        super(RasterScatQtPlot, self).__init__(parent)
        QDialog.setWindowTitle(self, "Raster ScatterPlot")

        self.initUI()

        self.raster = None
        self.band1 = None
        self.band2 = None
        self.raster_path = None
        self.nodata = None
        self.aoi_vector = None

        self.updateEnabled()

    def initUI(self):

        # Create plot area
        self.plot_widget = pg.PlotWidget()
        self.pltItem: pg.PlotItem = self.plot_widget.plotItem
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.pltItem.addItem(self.vLine, ignoreBounds=True)
        self.pltItem.addItem(self.hLine, ignoreBounds=True)

        #### Create histogram parameter input panel
        # Choose raster layer
        raster_label = QLabel('Raster Layer')
        self.raster_selection_box = QgsMapLayerComboBox(self)
        self.raster_selection_box.setShowCrs(True)
        self.raster_selection_box.setFilters(QgsMapLayerProxyModel.RasterLayer)

        # Choose band
        band_label = QLabel("Band 1 (X-Axis)")
        self.raster_band_input = QgsRasterBandComboBox(self)
        self.raster_band_input.setLayer(self.raster_selection_box.currentLayer())
        self.raster_selection_box.layerChanged.connect(self.raster_band_input.setLayer)

        # Choose band
        band2_label = QLabel("Band 2 (Y-Axis)")
        self.raster_band2_input = QgsRasterBandComboBox(self)
        self.raster_band2_input.setLayer(self.raster_selection_box.currentLayer())
        self.raster_selection_box.layerChanged.connect(self.raster_band2_input.setLayer)

        # Choose vector layer defining AOI with first feature
        vector_label = QLabel('Vector Layer')
        self.vector_selection_box = QgsMapLayerComboBox(self)
        self.vector_selection_box.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.vector_selection_box.setShowCrs(True)
        self.vector_selection_box.setFixedWidth(300)
        self.vector_selection_box.setAllowEmptyLayer(True)
        self.vector_selection_box.setCurrentIndex(0)

        aoi_label = QLabel('AOI Options')
        self.aoi_selection_box = QComboBox(self)
        self.aoi_selection_box.setFixedWidth(300)
        self.aoi_selection_box.addItems(['Canvas', 'Full Raster', 'Use Vectory Layer Geometry',
                                             'Rectangle', 'Polygon'])

        # Buttons to draw area
        self.drawRectButton = QPushButton()
        self.drawRectButton.setText('Draw Rectangle')
        self.drawRectButton.clicked.connect(self.drawRect)
        self.drawPolyButton = QPushButton()
        self.drawPolyButton.setText('Draw Polygon')
        self.drawPolyButton.clicked.connect(self.drawPoly)

        # Button to create histogram
        self.run_hist_btn = QPushButton()
        self.run_hist_btn.setText('Generate Plot')
        self.run_hist_btn.clicked.connect(self.do_plot)

        # Text box to display statistics
        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)

        # Create for input panel
        self.layer_select_layout = QFormLayout()
        self.layer_select_layout.addRow(raster_label, self.raster_selection_box)
        self.layer_select_layout.addRow(band_label, self.raster_band_input)
        self.layer_select_layout.addRow(band2_label, self.raster_band2_input)
        self.layer_select_layout.addRow(aoi_label, self.aoi_selection_box)
        self.layer_select_layout.addRow(vector_label, self.vector_selection_box)
        self.layer_select_layout.addWidget(self.drawRectButton)
        self.layer_select_layout.addWidget(self.drawPolyButton)
        self.layer_select_layout.addWidget(self.run_hist_btn)
        self.layer_select_layout.addWidget(self.text_box)
        ####

        # Populate dialog layout
        self.layout = QGridLayout(self)
        self.layout.addWidget(self.plot_widget, 0, 0)
        self.layout.addLayout(self.layer_select_layout, 0, 1)
        self.setLayout(self.layout)

    def drawRect(self):
        self.c = self.parent.canvas
        self.RectTool = RectangleMapTool(self.c)
        self.c.setMapTool(self.RectTool)

    def drawPoly(self):
        self.c = self.parent.canvas
        self.PolyTool = PolygonMapTool(self.c)
        self.c.setMapTool(self.PolyTool)

    def pass_valid_Checks(self):
        if self.raster_selection_box.currentLayer() is None:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid raster layer")
            msgBox.exec()
            return

        if Path(self.raster_selection_box.currentLayer().source()).exists() is False:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid raster layer")
            msgBox.exec()
            return

        if self.aoi_selection_box.currentIndex() == 2:
            if self.vector_selection_box.currentLayer() is None:
                msgBox = QMessageBox()
                msgBox.setText("You must select a valid vector / polygon layer to provide an AOI for the histogram")
                msgBox.exec()
                return

            if self.vector_selection_box.currentLayer.selectedFeatures()[0] is None:
                msgBox = QMessageBox()
                msgBox.setText("You must select a feature from the vector layer")
                msgBox.exec()
                return

    def pass_ROI_checks(self):

        if self.aoi_selection_box.currentIndex() == 3:
            try:
                r = self.RectTool.rectangle()
            except AttributeError:
                msgBox = QMessageBox()
                msgBox.setText("You must first draw a rectangle to provide an AOI of which to sample data")
                msgBox.exec()
                return

        if self.aoi_selection_box.currentIndex() == 4:
            try:
                r = self.PolyTool.geometry()
            except AttributeError:
                msgBox = QMessageBox()
                msgBox.setText("You must first draw a polygon to provide an AOI of which to sample data")
                msgBox.exec()
            return

    def do_plot(self):
        self.pass_valid_Checks()
        self.parse_plot_params()
        if self.aoi_selection_box.currentIndex() == 4:
            self.sample_from_polygon()

        if self.aoi_selection_box.currentIndex() == 3:
            self.sample_from_rectangle()

        if self.aoi_selection_box.currentIndex() == 2:
            self.sample_from_vector()

        if self.aoi_selection_box.currentIndex() == 1:
            self.sample_full_raster()

        if self.aoi_selection_box.currentIndex() == 0:
            datX, datY = self.sample_from_canvas()

        self.pass_ROI_checks()

        self.make_plot(datX, datY, self.nodata, self.raster.name())

    def sample_from_canvas(self):
        bb = self.parent.canvas.extent()
        bb.asWktCoordinates()
        raster_crs = self.raster.crs().authid()
        bb.asWktCoordinates()
        crs_epsg = self.parent.canvas.mapSettings().destinationCrs().authid()
        bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
        bounding_gdf = gpd.GeoDataFrame(geometry=[box(*bbc)], crs=crs_epsg)
        bounding_gdf.to_crs(raster_crs, inplace=True)
        bounds = bounding_gdf.bounds

        with rio.open(self.raster_path) as ds:

            min_row, min_col = ds.index(bounds.minx, bounds.miny)
            max_row, max_col = ds.index(bounds.maxx, bounds.maxy)
            win = Window(min(min_col[0], max_col[0]), min(min_row[0], max_row[0]),
                         abs(max_col[0] - min_col[0]), abs(max_row[0] - min_row[0]))

            # have to add 1 to the index since rio read starts at 1
            # if using np indexing don't add 1
            datX = ds.read(self.band1 + 1, window=win)
            datY = ds.read(self.band2 + 1, window=win)

        return datX, datY

    def sample_full_raster(self):
        with rio.open(self.raster_path) as ds:
            datX = ds.read(self.band1 + 1)
            datY = ds.read(self.band2 + 1)

        return datX, datY

    def sample_from_vector(self):

        poly_crs = self.aoi_vector.crs().authid()
        poly = self.aoi_vector.selectedFeatures()[0].geometry()
        raster_crs = self.raster.crs().authid()
        poly_gdf = qgis_poly_to_gdf(poly, poly_crs, raster_crs)
        with rio.open(self.raster_path) as ds:
            geom = [poly_gdf.geometry[0]]
            rdarr, aff = mask(ds, shapes=geom, crop=True)
            datX = rdarr[self.band1, :, :]
            datY = rdarr[self.band2, :, :]

        return datX, datY

    def sample_from_rect(self):
        bb = self.RectTool.rectangle()
        raster_crs = self.raster.crs().authid()
        crs_epsg = self.parent.canvas.mapSettings().destinationCrs().authid()
        bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
        bounding_gdf = gpd.GeoDataFrame(geometry=[box(*bbc)], crs=crs_epsg)
        bounding_gdf.to_crs(raster_crs, inplace=True)

        with rio.open(self.raster_path) as ds:
            geom = [bounding_gdf.geometry[0]]
            rdarr = mask(ds, shapes=geom, crop=True)[0]
            datX = rdarr[self.band1, :, :]
            datY = rdarr[self.band2, :, :]

        return datX, datY

    def sample_from_poly(self):
        poly = self.PolyTool.geometry()
        raster_crs = self.crs().authid()
        crs_epsg = self.parent.canvas.mapSettings().destinationCrs().authid()
        wkt = poly.asWkt()
        shapely_geom = loads(wkt)
        bounding_gdf = gpd.GeoDataFrame(geometry=[list(shapely_geom.geoms)[0]], crs=crs_epsg)
        bounding_gdf.to_crs(raster_crs, inplace=True)

        with rio.open(self.raster_path) as ds:
            geom = [bounding_gdf.geometry[0]]
            rdarr = mask(ds, shapes=geom, crop=True)[0]
            datX = rdarr[self.band1, :, :]
            datY = rdarr[self.band2, :, :]

        return datX, datY

    def parse_plot_params(self):
        # Grab the user specified parameters from the panel widgets
        self.raster = self.raster_selection_box.currentLayer()
        self.band1 = self.raster_band_input.currentIndex()
        self.band2 = self.raster_band2_input.currentIndex()
        self.raster_path = Path(self.raster.source())
        self.nodata = rio.open(self.raster_path).nodata

        if self.aoi_selection_box.currentIndex() == 3:
            self.aoi_vector = self.vector_selection_box.currentLayer()


    def make_plot(self, dataX, dataY, nodata, Name):
        dataX = np.ravel(dataX)
        dataY = np.ravel(dataY)
        xmask = np.where(dataX == nodata, True, False)
        ymask = np.where(dataY == nodata, True, False)

        mask = np.logical_or(xmask, ymask)
        datX = np.delete(dataX, mask)
        datY = np.delete(dataY, mask)

        scatter_plot = pg.ScatterPlotItem(
                size=1,
                # pen=pg.mkPen(None),
                # brush=pg.mkBrush(255, 255, 255, 20),
                hoverable=True,
                # hoverSymbol='s',
                # hoverSize=15,
                # hoverPen=pg.mkPen('r', width=2),
                # hoverBrush=pg.mkBrush('g'),
            )
        self.pltItem.clear()
        scatter_plot.addPoints(x=datX, y=datY, data=np.arange(datX.shape[0]))
        self.pltItem.addItem(scatter_plot)
        self.pltItem.setTitle(Name)
        self.pltItem.setLabel(axis='left', text=f"Band {str(self.raster_band_input.currentBand())}")
        self.pltItem.setLabel(axis='bottom', text=f"Band {str(self.raster_band2_input.currentBand())}")

        # Todo: add some correlatoin stats or somthing like that
        # self.text_box.setText(f'NumPixels = {band_data.size}\n'
        #                       f'NumNaN = {np.count_nonzero(np.isnan(band_data))}\n'
        #                       f'NumNodata = {dat1d.size - band_data.size}\n'
        #                       f'Min = {np.nanmin(band_data)}\n'
        #                       f'Max = {np.nanmax(band_data)}\n'
        #                       f'Mean = {np.nanmean(band_data)}\n'
        #                       f'Median = {np.nanmedian(band_data)}\n'
        #                       f'Var = {np.nanvar(band_data)}')

    def updateEnabled(self):
        # Todo: Figure out making the different elements visible depending on the selection in aoi_selection_box
        # Todo: Make Draw Rect and Draw Polygon just one button "Draw shape on canvas"
        # Todo: Add Help doc explaining draw Rect is click, hold, pull, release and Polygon is left click to create vert
        # and right click to finish object
        pass


