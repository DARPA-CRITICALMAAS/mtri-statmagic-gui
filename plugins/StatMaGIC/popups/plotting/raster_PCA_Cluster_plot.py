from qgis.PyQt.QtWidgets import QDialog, QLineEdit, QTextEdit
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.gui import QgsMapLayerComboBox, QgsRasterBandComboBox
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QGridLayout, QFormLayout, QLabel, QPushButton, QComboBox, QSpinBox, QVBoxLayout, QHBoxLayout
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
from osgeo import gdal
from statmagic_backend.extract.raster import getCanvasRasterDict, getFullRasterDict, getFullRasterDict_rio, getSubsetRasterDict_rio
from statmagic_backend.maths.scaling import standardScale_and_PCA

from ..grab_polygon import PolygonMapTool
from ..grab_rectangle import RectangleMapTool
from StatMaGIC.layerops import qgis_poly_to_gdf, shape_data_array_to_raster_array, shape_raster_array_to_data_array

import logging
logger = logging.getLogger("statmagic_gui")


class RasterPCAQtPlot(QDialog):

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        super(RasterPCAQtPlot, self).__init__(parent)
        QDialog.setWindowTitle(self, "Raster PCA BiPlot")

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

        aoi_label = QLabel('Data Extent Selection')
        self.aoi_selection_box = QComboBox(self)
        self.aoi_selection_box.setFixedWidth(300)
        self.aoi_selection_box.addItems(['Canvas', 'Full Raster', 'Drawn Rectangle', 'Drawn Polygon'])

        # Buttons to draw area
        self.drawRectButton = QPushButton()
        self.drawRectButton.setText('Draw Rectangle')
        self.drawRectButton.clicked.connect(self.drawRect)
        self.drawPolyButton = QPushButton()
        self.drawPolyButton.setText('Draw Polygon')
        self.drawPolyButton.clicked.connect(self.drawPoly)

        # Button to run PCA
        self.run_PCA_btn = QPushButton()
        self.run_PCA_btn.setText('Run PCA')
        self.run_PCA_btn.clicked.connect(self.prepPCA)

        # Button to create PCA plot
        self.run_plot_btn = QPushButton()
        self.run_plot_btn.setText('Create Plot')
        self.run_plot_btn.clicked.connect(self.plot_raster_scatter)

        # Choose band
        band_label = QLabel("PCA X-Axis")
        self.raster_band_input = QgsRasterBandComboBox(self)
        self.raster_band_input.setLayer(self.raster_selection_box.currentLayer())
        self.raster_selection_box.layerChanged.connect(self.raster_band_input.setLayer)

        # Choose band
        band2_label = QLabel("PCA Y-Axis")
        self.raster_band2_input = QgsRasterBandComboBox(self)
        self.raster_band2_input.setLayer(self.raster_selection_box.currentLayer())
        self.raster_selection_box.layerChanged.connect(self.raster_band2_input.setLayer)

        # Text box to display statistics
        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)

        self.cluster_box = QPushButton()
        self.cluster_box.setText("Optional Cluster into Groups")
        self.cluster_box.clicked.connect(self.popup_cluster_menu)
        self.cluster_box.setEnabled(False)


        # Main NonPlot Layout
        self.mainLayout = QVBoxLayout()

        # Create for input panel
        self.layer_select_layout = QFormLayout()
        self.layer_select_layout.addRow(raster_label, self.raster_selection_box)
        self.layer_select_layout.addRow(aoi_label, self.aoi_selection_box)

        self.samplingLayout = QHBoxLayout()
        self.samplingLayout.addWidget(self.drawRectButton)
        self.samplingLayout.addWidget(self.drawPolyButton)

        self.runPCA_layout = QVBoxLayout()
        self.runPCA_layout.addWidget(self.run_PCA_btn)

        self.band_select_layout = QFormLayout()
        self.band_select_layout.addRow(band_label, self.raster_band_input)
        self.band_select_layout.addRow(band2_label, self.raster_band2_input)
        self.band_select_layout.addRow(QLabel('Assign Cluster Labels'), self.cluster_box)

        self.mainLayout.addLayout(self.layer_select_layout)
        self.mainLayout.addLayout(self.samplingLayout)
        self.mainLayout.addLayout(self.runPCA_layout)
        self.mainLayout.addLayout(self.band_select_layout)

        self.mainLayout.addWidget(self.run_plot_btn)
        self.mainLayout.addWidget(self.text_box)

        # Populate dialog layout
        self.layout = QGridLayout(self)
        self.layout.addWidget(self.plot_widget, 0, 0)
        self.layout.addLayout(self.mainLayout, 0, 1)
        self.setLayout(self.layout)

    def drawRect(self):
        self.c = self.parent.canvas
        self.RectTool = RectangleMapTool(self.c)
        self.c.setMapTool(self.RectTool)

    def drawPoly(self):
        self.c = self.parent.canvas
        self.PolyTool = PolygonMapTool(self.c)
        self.c.setMapTool(self.PolyTool)

    def prepPCA(self):
        self.passPCA_check()
        if self.aoi_selection_box.currentIndex() == 3:
            logger.debug('sampling from drawn Polygon')
            self.sample_from_polygon()

        if self.aoi_selection_box.currentIndex() == 2:
            logger.debug('sampling from Rectangle')
            self.sample_from_rectangle()

        if self.aoi_selection_box.currentIndex() == 1:
            logger.debug('sampling from full raster')
            self.sample_full_raster()

        if self.aoi_selection_box.currentIndex() == 0:
            logger.debug('sampling from canvas extent')
            self.sample_from_canvas()

    def sample_from_polygon(self):
        # Get the selected raster layer
        raster = self.raster_selection_box.currentLayer()
        raster_path = raster.source()
        self.full_dict = getFullRasterDict_rio(rio.open(raster_path))
        # Get the epsg crs of the raster layer
        raster_crs = raster.crs().authid()
        # Get the epsg crs of the polygon from the active canvas
        poly_crs = self.parent.canvas.mapSettings().destinationCrs().authid()
        # Get the polygon from the mapTool
        poly = self.PolyTool.geometry()
        logger.debug(poly)
        # Convert the polygon to a GeoDataFrame
        poly_gdf = qgis_poly_to_gdf(poly, poly_crs, raster_crs)

        try:
            with rio.open(raster_path) as ds:
                geom = [poly_gdf.geometry[0]]
                rdarr, aff = mask(ds, shapes=geom, crop=True)
                self.raster_dict = getSubsetRasterDict_rio(self.full_dict, rdarr, aff)
                self.raster_array = rdarr

        except (RasterioIOError, IOError):
            msgBox = QMessageBox()
            msgBox.setText("You must use a locally available raster layer for the histogram.")
            msgBox.exec()
            return

        self.run_pca()

    def sample_from_rectangle(self):
        # Get the selected raster layer
        raster = self.raster_selection_box.currentLayer()
        raster_path = raster.source()
        self.full_dict = getFullRasterDict_rio(rio.open(raster_path))
        # Get the epsg crs of the raster layer
        raster_crs = raster.crs().authid()
        # Get the polygon from the mapTool
        bb = self.RectTool.rectangle()
        crs_epsg = self.parent.canvas.mapSettings().destinationCrs().authid()
        bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
        poly_gdf = gpd.GeoDataFrame(geometry=[box(*bbc)], crs=crs_epsg)
        poly_gdf.to_crs(raster_crs, inplace=True)

        try:
            with rio.open(raster_path) as ds:
                geom = [poly_gdf.geometry[0]]
                rdarr, aff = mask(ds, shapes=geom, crop=True)
                self.raster_dict = getSubsetRasterDict_rio(self.full_dict, rdarr, aff)
                self.raster_array = rdarr

        except (RasterioIOError, IOError):
            msgBox = QMessageBox()
            msgBox.setText("You must use a locally available raster layer")
            msgBox.exec()
            return

        self.run_pca()
        pass

    def sample_full_raster(self):
        raster = self.raster_selection_box.currentLayer()
        raster_path = raster.source()
        self.raster_dict = getFullRasterDict_rio(rio.open(raster_path))
        self.raster_array = rio.open(raster_path).read()
        self.run_pca()

    def sample_from_canvas(self):
        r_ds = gdal.Open(self.raster_selection_box.currentLayer().source())
        self.full_dict = getFullRasterDict(r_ds)
        self.raster_dict = getCanvasRasterDict(self.full_dict, self.parent.canvas.extent())
        self.raster_array = r_ds.ReadAsArray(self.raster_dict['Xoffset'], self.raster_dict['Yoffset'],
                                        self.raster_dict['sizeX'], self.raster_dict['sizeY'])
        self.run_pca()

    def passPCA_check(self):
        # Check that the user has selected a valid raster layer
        if self.raster_selection_box.currentLayer() is None:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid raster layer for the plot")
            msgBox.exec()
            return

        if Path(self.raster_selection_box.currentLayer().source()).exists() is False:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid raster layer for the plot")
            msgBox.exec()
            return

        if self.aoi_selection_box.currentIndex() == 2:
            try:
                r = self.RectTool.rectangle()
            except AttributeError:
                msgBox = QMessageBox()
                msgBox.setText("You must first draw a rectangle to provide an AOI of which to sample data")
                msgBox.exec()
                return

        if self.aoi_selection_box.currentIndex() == 3:
            try:
                r = self.PolyTool.geometry()
            except AttributeError:
                msgBox = QMessageBox()
                msgBox.setText("You must first draw a polygon to provide an AOI of which to sample data")
                msgBox.exec()
            return

    def passPlot_check(self):
        if self.raster_band_input.currentBand() is None:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid raster band for the histogram")
            msgBox.exec()
            return

        if self.raster_band2_input.currentBand() is None:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid raster band for the histogram")
            msgBox.exec()
            return


    def parse_raster_pcaPlot(self):

        # Grab the user specified parameters from the panel widgets
        raster: QgsRasterLayer = self.raster_selection_box.currentLayer()
        band1 = self.raster_band_input.currentBand()
        band2 = self.raster_band2_input.currentBand()
        raster_path = Path(raster.source())

        if self.aoi_selection_box.currentIndex() == 4:
            logger.debug('drawing from Polygon')
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
                    dat = rdarr[band1, :, :]

            except (RasterioIOError, IOError):
                msgBox = QMessageBox()
                msgBox.setText("You must use a locally available raster layer for the histogram.")
                msgBox.exec()
                return

        if self.aoi_selection_box.currentIndex() == 3:
            logger.debug('drawing from Rectangle')
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
                    datX = rdarr[band1, :, :]
                    datY = rdarr[band2, :, :]

            except (RasterioIOError, IOError):
                msgBox = QMessageBox()
                msgBox.setText("You must use a locally available raster layer for the histogram.")
                msgBox.exec()
                return

        if self.aoi_selection_box.currentIndex() == 2:
            logger.debug('drawing from vector geometry')
            if self.vector_selection_box.currentLayer() is None:
                msgBox = QMessageBox()
                msgBox.setText("You must select a valid vector / polygon layer to provide an AOI for the histogram")
                msgBox.exec()
                return

            aoi: QgsVectorLayer = self.vector_selection_box.currentLayer()

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
                    logger.debug("Constructing coordinate transform")
                    min_corner = QgsPoint(extents_rect.xMinimum(), extents_rect.yMinimum())
                    max_corner = QgsPoint(extents_rect.xMaximum(), extents_rect.yMaximum())
                    raster_crs = raster.crs()
                    aoi_crs = aoi.crs()
                    tr = QgsCoordinateTransform(aoi_crs, raster_crs, QgsProject.instance())

                    logger.debug("Applying transform")
                    min_corner.transform(tr)
                    max_corner.transform(tr)
                    min_row, min_col = ds.index(min_corner.x(), min_corner.y())
                    max_row, max_col = ds.index(max_corner.x(), max_corner.y())
                    logger.debug(min_row, min_col, max_row, max_col, max_col - min_col, max_row - min_row)

                    # Read the raster band data from within the AOI
                    logger.debug(f'Creating Window('
                          f'{min(min_col, max_col)},{min(min_row, max_row)},'
                          f'{abs(max_col - min_col)},{abs(max_row - min_row)}'
                          f')')
                    win = Window(min(min_col, max_col), min(min_row, max_row),
                                 abs(max_col - min_col), abs(max_row - min_row))
                    logger.debug("Reading band within window")
                    dat = ds.read(band1, window=win)

            except (RasterioIOError, IOError):
                msgBox = QMessageBox()
                msgBox.setText("You must use a locally available raster layer for the histogram.")
                msgBox.exec()
                return

        if self.aoi_selection_box.currentIndex() == 1:
            logger.debug("Extracting values from full raster")
            try:
                with rio.open(raster_path) as ds:
                    dat = ds.read(band1)

            except (RasterioIOError, IOError):
                msgBox = QMessageBox()
                msgBox.setText("You must use a locally available raster layer for the histogram.")
                msgBox.exec()
                return

        if self.aoi_selection_box.currentIndex() == 0:

            bb = self.parent.canvas.extent()
            bb.asWktCoordinates()
            raster_crs = raster.crs().authid()
            bb.asWktCoordinates()
            crs_epsg = self.parent.canvas.mapSettings().destinationCrs().authid()
            bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
            bounding_gdf = gpd.GeoDataFrame(geometry=[box(*bbc)], crs=crs_epsg)
            bounding_gdf.to_crs(raster_crs, inplace=True)
            bounds = bounding_gdf.bounds

            logger.debug("Extracting values from canvas")
            try:
                with rio.open(raster_path) as ds:

                    min_row, min_col = ds.index(bounds.minx, bounds.miny)
                    max_row, max_col = ds.index(bounds.maxx, bounds.maxy)
                    win = Window(min(min_col[0], max_col[0]), min(min_row[0], max_row[0]),
                                 abs(max_col[0] - min_col[0]), abs(max_row[0] - min_row[0]))
                    logger.debug("Reading band within window")
                    dat = ds.read(band1, window=win)


            except (RasterioIOError, IOError):
                msgBox = QMessageBox()
                msgBox.setText("You must use a locally available raster layer for the histogram.")
                msgBox.exec()
                return

        # Deal with nodata values
        nodata = rio.open(raster_path).nodata
        self.plot_raster_scatter(datX, datY, nodata, raster.name())

    def run_pca(self):
        data_array, msk = shape_raster_array_to_data_array(self.raster_array, self.raster_dict, return_mask=True)
        # Todo: Turn this into a pandas df ready to plot pass to plotting functions
        # Todo: Print out some info from the PCA into the text edit box
        self.pca_data, self.pca = standardScale_and_PCA(data_array, 0.975)

        print(self.pca_data)
        print(self.pca.n_components_)


    def plot_raster_scatter(self, dataX, dataY, nodata, Name):
        dataX = np.ravel(dataX)
        dataY = np.ravel(dataY)
        datX = np.delete(dataX, np.where(dataX == nodata))
        datY = np.delete(dataY, np.where(dataY == nodata))

        # logger.debug("Computing histogram")
        # hist, bin_edges = np.histogram(band_data,
        #                                range=(np.nanmin(band_data), np.nanmax(band_data)),
        #                                bins=int(self.num_bins_input.text()), density=False)

        logger.debug("Plotting histogram")
        scatter_plot = pg.ScatterPlotItem(
                size=10,
                pen=pg.mkPen(None),
                brush=pg.mkBrush(255, 255, 255, 20),
                # hoverable=True,
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

        logger.debug("Display statistics")
        # Todo: add some correlatoin stats or somthing like that
        # self.text_box.setText(f'NumPixels = {band_data.size}\n'
        #                       f'NumNaN = {np.count_nonzero(np.isnan(band_data))}\n'
        #                       f'NumNodata = {dat1d.size - band_data.size}\n'
        #                       f'Min = {np.nanmin(band_data)}\n'
        #                       f'Max = {np.nanmax(band_data)}\n'
        #                       f'Mean = {np.nanmean(band_data)}\n'
        #                       f'Median = {np.nanmedian(band_data)}\n'
        #                       f'Var = {np.nanvar(band_data)}')

    def popup_cluster_menu(self):
        pass
