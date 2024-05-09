from qgis.PyQt.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QMessageBox
from qgis.gui import QgsMapLayerComboBox, QgsRasterBandComboBox
from PyQt5.QtWidgets import QGridLayout, QFormLayout, QLabel, QPushButton, QComboBox
import pyqtgraph as pg


from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject, QgsMapLayerProxyModel

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

'''
Joe and/or Alex - Take a good look through here and change things as needed for better design, signalling, etc.
The goal is to have this be a template for more plotting functions, so that a designer can simply change out the 
make_plot function and the widgets required for input (raster bands, vector layers, etc) and all the data fetching
functions (sample from ____) are good to go to pass data into the plotting function.

Of course I did a lot of this, then saw on stack exchange reference to QStackedWidget, which might be the best 
choice for this dynamic GUI stuff, but I didn't yet explore. 

The other thing I need help with is how to stop the continuation if one of the pass_Checks methods after the
QMessage is closed

Also I imagine that there are more standard ways to pass the data to the plotting function so please feel free to 
improve on that aspect as well.
'''
class NoPlotForYouException(BaseException):
    """ Custom exception to hijack control flow if a plot can't be made. """
    pass

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
        self.roi_vector = None

        self.roi_selection_box.currentIndexChanged.connect(self.updateGui)

    def initUI(self):

        # Create plot area
        self.plot_widget = pg.PlotWidget()
        self.pltItem: pg.PlotItem = self.plot_widget.plotItem
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.pltItem.addItem(self.vLine, ignoreBounds=True)
        self.pltItem.addItem(self.hLine, ignoreBounds=True)

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

        # Options for choosing the data extent 
        roi_label = QLabel('ROI Options')
        self.roi_selection_box = QComboBox(self)
        self.roi_selection_box.addItems(['Canvas', 'Full Raster', 'Use Vectory Layer Geometry', 'Rectangle', 'Polygon'])

        # The Non-plot part of the layout
        # This will hold the static widgets on top and the updatable widgets below
        self.inputsLayout = QVBoxLayout()

        # Use a form to gather the essential inputs that are needed for all extent selection options
        self.layer_select_layout = QFormLayout()
        self.layer_select_layout.addRow(raster_label, self.raster_selection_box)
        self.layer_select_layout.addRow(band_label, self.raster_band_input)
        self.layer_select_layout.addRow(band2_label, self.raster_band2_input)
        self.layer_select_layout.addRow(roi_label, self.roi_selection_box)

        self.inputsLayout.addLayout(self.layer_select_layout)

        # This is the layout that will be created and deleted at each changed action of the roi selection
        self.updatableLayout = QVBoxLayout()
        self.inputsLayout.addLayout(self.updatableLayout)

        # Use Grid Layout to combine the plot side with the inputs+textbox side
        self.layout = QGridLayout(self)
        self.layout.addWidget(self.plot_widget, 0, 0)
        self.layout.addLayout(self.inputsLayout, 0, 1)
        self.setLayout(self.layout)
        self.updateGui()

    def updateGui(self):
        self.removeGui_widgets()
        if self.roi_selection_box.currentIndex() == 0:
            self.initCanvasGui()
        elif self.roi_selection_box.currentIndex() == 1:
            self.initFullGui()
        elif self.roi_selection_box.currentIndex() == 2:
            self.initVectorGui()
        elif self.roi_selection_box.currentIndex() == 3:
            self.initRectGui()
        else:
            self.initPolyGui()

    def removeGui_widgets(self):
        while self.updatableLayout.count():
            child = self.updatableLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def initRectGui(self):
        self.drawRectButton = QPushButton()
        self.drawRectButton.setText('Draw Rectangle')
        self.drawRectButton.clicked.connect(self.drawRect)

        self.run_rect_btn = QPushButton()
        self.run_rect_btn.setText('Generate Plot From \n Rectangle Extent')
        self.run_rect_btn.clicked.connect(self.do_plot)

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)

        self.updatableLayout.addWidget(self.drawRectButton)
        self.updatableLayout.addWidget(self.run_rect_btn)
        self.updatableLayout.addWidget(self.text_box)

    def initPolyGui(self):
        self.drawPolyButton = QPushButton()
        self.drawPolyButton.setText('Draw Polygon')
        self.drawPolyButton.clicked.connect(self.drawPoly)

        self.run_poly_btn = QPushButton()
        self.run_poly_btn.setText('Generate Plot From \n Polygon Extent')
        self.run_poly_btn.clicked.connect(self.do_plot)

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)

        self.updatableLayout.addWidget(self.drawPolyButton)
        self.updatableLayout.addWidget(self.run_poly_btn)
        self.updatableLayout.addWidget(self.text_box)

    def initCanvasGui(self):
        self.run_canvas_btn = QPushButton()
        self.run_canvas_btn.setText('Generate Plot From Canvas Extent')
        self.run_canvas_btn.clicked.connect(self.do_plot)

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)

        self.updatableLayout.addWidget(self.run_canvas_btn)
        self.updatableLayout.addWidget(self.text_box)

    def initFullGui(self):
        self.run_full_btn = QPushButton()
        self.run_full_btn.setText('Generate Plot \n From Full Raster')
        self.run_full_btn.clicked.connect(self.do_plot)

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)

        self.updatableLayout.addWidget(self.run_full_btn)
        self.updatableLayout.addWidget(self.text_box)

    def initVectorGui(self):
        self.vector_selection_box = QgsMapLayerComboBox(self)
        self.vector_selection_box.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.vector_selection_box.setShowCrs(True)
        self.vector_selection_box.setAllowEmptyLayer(True)
        self.vector_selection_box.setPlaceholderText("Choose a Polygon Layer")
        self.vector_selection_box.setCurrentIndex(-1)

        self.run_vec_btn = QPushButton()
        self.run_vec_btn.setText('Generate Plot \n From Selected Feature')
        self.run_vec_btn.clicked.connect(self.do_plot)

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)

        self.updatableLayout.addWidget(self.vector_selection_box)
        self.updatableLayout.addWidget(self.run_vec_btn)
        self.updatableLayout.addWidget(self.text_box)

    def drawRect(self):
        self.c = self.parent.canvas
        # clear any previous rectangle before enabling new rectangle selection
        if hasattr(self, "RectTool") and self.RectTool.isActive():
            self.RectTool.deactivate()
        self.RectTool = RectangleMapTool(self.c)
        self.c.setMapTool(self.RectTool)

    def drawPoly(self):
        self.c = self.parent.canvas
        # clear any previous rectangle before enabling new rectangle selection
        if hasattr(self, "PolyTool") and self.PolyTool.isActive():
            self.PolyTool.deactivate()
        self.PolyTool = PolygonMapTool(self.c)
        self.c.setMapTool(self.PolyTool)

    def pass_valid_Checks(self):
        if self.raster_selection_box.currentLayer() is None:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid raster layer")
            msgBox.exec()
            raise NoPlotForYouException()

        if Path(self.raster_selection_box.currentLayer().source()).exists() is False:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid raster layer")
            msgBox.exec()
            raise NoPlotForYouException()

        if self.roi_selection_box.currentIndex() == 2:
            if self.vector_selection_box.currentLayer() is None:
                msgBox = QMessageBox()
                msgBox.setText("You must select a valid vector / polygon layer to provide an roi")
                msgBox.exec()
                raise NoPlotForYouException()

            cl = self.vector_selection_box.currentLayer()
            if len(cl.selectedFeatures()) < 1:
                msgBox = QMessageBox()
                msgBox.setText("You must select a feature from the vector layer")
                msgBox.exec()
                raise NoPlotForYouException()

    def pass_ROI_checks(self):
        if self.roi_selection_box.currentIndex() == 3:
            try:
                r = self.RectTool.rectangle()
                # if RectTool was never initialized, this throws AttributeError
                # if RectTool has been used, but deactivated, r will be empty
                # since this doesn't throw AttributeError, we have to throw it
                if r is None:
                    # TODO: find a better control flow mechanism than this
                    raise AttributeError()
            except AttributeError:
                msgBox = QMessageBox()
                msgBox.setText("You must first draw a rectangle to provide an roi of which to sample data")
                msgBox.exec()
                raise NoPlotForYouException()

        if self.roi_selection_box.currentIndex() == 4:
            try:
                r = self.PolyTool.geometry()
                if r is None:
                    raise AttributeError()
            except AttributeError:
                msgBox = QMessageBox()
                msgBox.setText("You must first draw a polygon to provide an roi of which to sample data")
                msgBox.exec()
                raise NoPlotForYouException()

    def do_plot(self):
        try:
            self.pass_valid_Checks()
            self.parse_plot_params()
            if self.roi_selection_box.currentIndex() == 4:
                datX, datY = self.sample_from_poly()

            if self.roi_selection_box.currentIndex() == 3:
                datX, datY = self.sample_from_rect()

            if self.roi_selection_box.currentIndex() == 2:
                datX, datY = self.sample_from_vector()

            if self.roi_selection_box.currentIndex() == 1:
                datX, datY = self.sample_full_raster()

            if self.roi_selection_box.currentIndex() == 0:
                datX, datY = self.sample_from_canvas()
        except NoPlotForYouException:
            return

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
        poly_crs = self.roi_vector.crs().authid()
        poly = self.roi_vector.selectedFeatures()[0].geometry()
        raster_crs = self.raster.crs().authid()
        poly_gdf = qgis_poly_to_gdf(poly, poly_crs, raster_crs)
        with rio.open(self.raster_path) as ds:
            geom = [poly_gdf.geometry[0]]
            rdarr, aff = mask(ds, shapes=geom, crop=True)
            datX = rdarr[self.band1, :, :]
            datY = rdarr[self.band2, :, :]

        return datX, datY

    def sample_from_rect(self):
        self.pass_ROI_checks()
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
        self.pass_ROI_checks()
        poly = self.PolyTool.geometry()
        raster_crs = self.raster.crs().authid()
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

        if self.roi_selection_box.currentIndex() == 2:
            self.roi_vector = self.vector_selection_box.currentLayer()

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

    def done(self, a0):
        if hasattr(self, "RectTool"):
            self.RectTool.deactivate()
            self.c.unsetMapTool(self.RectTool)

        if hasattr(self, "PolyTool"):
            self.PolyTool.deactivate()
            self.c.unsetMapTool(self.PolyTool)

        super(RasterScatQtPlot, self).done(a0)
