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
from ..popups.grab_polygon import PolygonMapTool
from ..popups.grab_rectangle import RectangleMapTool


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
        self.aoi_selection_box.setAllowEmptyLayer(True)
        self.aoi_selection_box.setCurrentIndex(0)


        non_aoi_label = QLabel('Non AOI Options')
        self.non_aoi_selection_box = QComboBox(self)
        self.non_aoi_selection_box.setFixedWidth(300)
        self.non_aoi_selection_box.addItems(['Canvas', 'Full Raster', 'Use Vectory Layer Geometry',
                                             'Rectangle', 'Polygon'])

        # Select number of bins in the histogram
        bins_label = QLabel("# Bins")
        # self.num_bins_input = QLineEdit(self)
        # validator = QIntValidator()
        # validator.setRange(2, 50)
        # self.num_bins_input.setValidator(validator)
        # self.num_bins_input.setText("10")
        # Changed this to a spinBox
        self.num_bins_input = QSpinBox()
        self.num_bins_input.setValue(10)
        self.num_bins_input.setRange(10, 100)
        self.num_bins_input.setSingleStep(5)

        # Buttons to draw area
        self.drawRectButton = QPushButton()
        self.drawRectButton.setText('Draw Rectangle')
        self.drawRectButton.clicked.connect(self.drawRect)
        self.drawPolyButton = QPushButton()
        self.drawPolyButton.setText('Draw Polygon')
        self.drawPolyButton.clicked.connect(self.drawPoly)

        # Button to create histogram
        self.run_hist_btn = QPushButton()
        self.run_hist_btn.setText('Plot Histogram')
        self.run_hist_btn.clicked.connect(self.parse_raster_histogram)

        # Text box to display statistics
        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)

        # Create for input panel
        self.layer_select_layout = QFormLayout()
        self.layer_select_layout.addRow(raster_label, self.raster_selection_box)
        self.layer_select_layout.addRow(band_label, self.raster_band_input)
        self.layer_select_layout.addRow(non_aoi_label, self.non_aoi_selection_box)
        self.layer_select_layout.addRow(aoi_label, self.aoi_selection_box)
        self.layer_select_layout.addRow(bins_label, self.num_bins_input)
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

    def mouseMoved(self, evt):
        print("Mouse moved")
        print(evt)

    def highlightFeature(self):
        aoi: QgsVectorLayer = self.aoi_selection_box.currentLayer()
        l = self.iface.setActiveLayer(aoi)
        self.iface.mainWindow().findChild(QAction, 'mActionDeselectAll').trigger()
        aoi.selectByIds([0])

    def drawRect(self):
        self.c = self.parent.canvas
        self.RectTool = RectangleMapTool(self.c)
        self.c.setMapTool(self.RectTool)

    def drawPoly(self):
        self.c = self.parent.canvas
        self.PolyTool = PolygonMapTool(self.c)
        self.c.setMapTool(self.PolyTool)


    def parse_raster_histogram(self):
        # The correct way to compute a histogram should be with the QGIS
        # histogram provider, but the function histogramVector is broken in QGIS 3.34
        # https://github.com/qgis/QGIS/issues/29700
        # So we do a silly thing - get the source of the selected layer,
        # read it with rasterio, and compute our histogram that way

        # Check that the user has selected a valid raster layer
        if self.raster_selection_box.currentLayer() is None:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid raster layer for the histogram")
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

        # Grab the user specified parameters from the panel widgets
        raster: QgsRasterLayer = self.raster_selection_box.currentLayer()
        band = self.raster_band_input.currentBand()
        raster_path = Path(raster.source())

        print(f'Creating histogram of layer {self.raster_selection_box.currentLayer()},'
              f' band {self.raster_band_input.currentBand()},'
              f' within AOI {self.aoi_selection_box.currentLayer()},'
              f' #bins = {self.num_bins_input.text()}')

        if self.non_aoi_selection_box.currentIndex() == 4:
            print('drawing from Polygon')
            if self.PolyTool.geometry() is None:
                msgBox = QMessageBox()
                msgBox.setText("You must first draw a polygon to provide an AOI for the histogram")
                msgBox.exec()
                return

            poly = self.PolyTool.geometry()
            raster_crs = raster.crs().authid()
            crs_epsg = self.parent.canvas.mapSettings().destinationCrs().authid()
            # This could also make use of the __geo_interface__ referenced in the comments here
            # https://gis.stackexchange.com/questions/353452/convert-qgis-geometry-into-shapely-geometry-to-use-orient-method-defined-in-shap
            wkt = poly.asWkt()
            shapely_geom = loads(wkt)
            bounding_gdf = gpd.GeoDataFrame(geometry=[list(shapely_geom.geoms)[0]], crs=crs_epsg)
            bounding_gdf.to_crs(raster_crs, inplace=True)

            try:
                with rio.open(raster_path) as ds:
                    geom = [bounding_gdf.geometry[0]]
                    rdarr = mask(ds, shapes=geom, crop=True)[0]
                    dat = rdarr[band, :, :]

            except (RasterioIOError, IOError):
                msgBox = QMessageBox()
                msgBox.setText("You must use a locally available raster layer for the histogram.")
                msgBox.exec()
                return

        if self.non_aoi_selection_box.currentIndex() == 3:
            print('drawing from Rectangle')
            if self.RectTool.rectangle() is None:
                msgBox = QMessageBox()
                msgBox.setText("You must first draw a rectangle to provide an AOI for the histogram")
                msgBox.exec()
                return

            bb = self.RectTool.rectangle()
            raster_crs = raster.crs().authid()
            crs_epsg = self.parent.canvas.mapSettings().destinationCrs().authid()
            bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
            bounding_gdf = gpd.GeoDataFrame(geometry=[box(*bbc)], crs=crs_epsg)
            bounding_gdf.to_crs(raster_crs, inplace=True)

            try:
                with rio.open(raster_path) as ds:
                    geom = [bounding_gdf.geometry[0]]
                    rdarr = mask(ds, shapes=geom, crop=True)[0]
                    dat = rdarr[band, :, :]

            except (RasterioIOError, IOError):
                msgBox = QMessageBox()
                msgBox.setText("You must use a locally available raster layer for the histogram.")
                msgBox.exec()
                return

        if self.non_aoi_selection_box.currentIndex() == 2:
            print('drawing from vector geometry')
            if self.aoi_selection_box.currentLayer() is None:
                msgBox = QMessageBox()
                msgBox.setText("You must select a valid vector / polygon layer to provide an AOI for the histogram")
                msgBox.exec()
                return

            aoi: QgsVectorLayer = self.aoi_selection_box.currentLayer()

            # Assume the bounding box of the first feature of the AOI layer is the AOI
            # I'm going to make this so it grabs the selected Features
            extents_feature = aoi.selectedFeatures()[0]
            if extents_feature is None:
                msgBox = QMessageBox()
                msgBox.setText("You must select a feature from the vector layer")
                msgBox.exec()
                return
            # extents_feature = aoi.getFeature(1)
            extents_rect = extents_feature.geometry().boundingBox()

            # Open the raster layer with rasterio since the built-in QGIS histogram function is broken
            try:
                with rio.open(raster_path) as ds:
                    # Get the coordinates of the AOI feature in the same CRS as the raster
                    # Todo: This method will have to be adjusted to account for irregular geometries to drop values outside the polygons
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
                    print(min_row, min_col, max_row, max_col, max_col - min_col, max_row - min_row)

                    # Read the raster band data from within the AOI
                    print(f'Creating Window('
                          f'{min(min_col, max_col)},{min(min_row, max_row)},'
                          f'{abs(max_col - min_col)},{abs(max_row - min_row)}'
                          f')')
                    win = Window(min(min_col, max_col), min(min_row, max_row),
                                 abs(max_col - min_col), abs(max_row - min_row))
                    print("Reading band within window")
                    dat = ds.read(band, window=win)

            except (RasterioIOError, IOError):
                msgBox = QMessageBox()
                msgBox.setText("You must use a locally available raster layer for the histogram.")
                msgBox.exec()
                return

        if self.non_aoi_selection_box.currentIndex() == 1:
            print("Extracting values from full raster")
            try:
                with rio.open(raster_path) as ds:
                    dat = ds.read(band)

            except (RasterioIOError, IOError):
                msgBox = QMessageBox()
                msgBox.setText("You must use a locally available raster layer for the histogram.")
                msgBox.exec()
                return

        if self.non_aoi_selection_box.currentIndex() == 0:

            bb = self.parent.canvas.extent()
            bb.asWktCoordinates()
            raster_crs = raster.crs().authid()
            bb.asWktCoordinates()
            crs_epsg = self.parent.canvas.mapSettings().destinationCrs().authid()
            bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
            bounding_gdf = gpd.GeoDataFrame(geometry=[box(*bbc)], crs=crs_epsg)
            bounding_gdf.to_crs(raster_crs, inplace=True)
            bounds = bounding_gdf.bounds

            print("Extracting values from canvas")
            try:
                with rio.open(raster_path) as ds:

                    min_row, min_col = ds.index(bounds.minx, bounds.miny)
                    max_row, max_col = ds.index(bounds.maxx, bounds.maxy)
                    win = Window(min(min_col[0], max_col[0]), min(min_row[0], max_row[0]),
                                 abs(max_col[0] - min_col[0]), abs(max_row[0] - min_row[0]))
                    print("Reading band within window")
                    dat = ds.read(band, window=win)


            except (RasterioIOError, IOError):
                msgBox = QMessageBox()
                msgBox.setText("You must use a locally available raster layer for the histogram.")
                msgBox.exec()
                return

        # Deal with nodata values
        nodata = rio.open(raster_path).nodata
        self.plot_raster_histogram(dat, nodata, raster.name())


    def plot_raster_histogram(self, data, nodata, Name):
        dat1d = np.ravel(data)
        band_data = np.delete(dat1d, np.where(dat1d == nodata))

        print("Computing histogram")
        hist, bin_edges = np.histogram(band_data,
                                       range=(np.nanmin(band_data), np.nanmax(band_data)),
                                       bins=int(self.num_bins_input.text()), density=False)

        print("Plotting histogram")
        bar_chart = pg.BarGraphItem(x0=bin_edges[:-1], x1=bin_edges[1:], height=hist, pen='w', brush=(0, 0, 255, 150))
        self.pltItem.clear()
        self.pltItem.addItem(bar_chart)
        self.pltItem.setTitle(Name)
        self.pltItem.setLabel(axis='left', text='Pixel Counts')
        self.pltItem.setLabel(axis='bottom', text=f"Band {str(self.raster_band_input.currentBand())}")

        print("Display statistics")
        self.text_box.setText(f'NumPixels = {band_data.size}\n'
                              f'NumNaN = {np.count_nonzero(np.isnan(band_data))}\n'
                              f'NumNodata = {dat1d.size - band_data.size}\n'
                              f'Min = {np.nanmin(band_data)}\n'
                              f'Max = {np.nanmax(band_data)}\n'
                              f'Mean = {np.nanmean(band_data)}\n'
                              f'Median = {np.nanmedian(band_data)}\n'
                              f'Var = {np.nanvar(band_data)}')
