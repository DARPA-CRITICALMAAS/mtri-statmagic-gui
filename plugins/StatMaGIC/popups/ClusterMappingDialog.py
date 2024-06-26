
from PyQt5.QtWidgets import  QDialog, QVBoxLayout, QPushButton, QLabel, QCheckBox, \
    QComboBox, QSpinBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QMessageBox
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsProject, QgsMapLayerProxyModel, QgsRasterLayer, QgsLayerTreeLayer

from shapely.geometry import box
from shapely.wkt import loads
import geopandas as gpd
from osgeo import gdal
import rasterio as rio
from rasterio.windows import Window, from_bounds
from rasterio.mask import mask
from rasterio import RasterioIOError
from pathlib import Path


from ..popups.grab_polygon import PolygonMapTool
from ..popups.grab_rectangle import RectangleMapTool
from statmagic_backend.extract.raster import getCanvasRasterDict, getFullRasterDict, getFullRasterDict_rio, getSubsetRasterDict_rio
from statmagic_backend.maths.scaling import standardScale_and_PCA
from statmagic_backend.maths.clustering import kmeans_fit_predict
from ..fileops import rasterio_write_raster_from_array
from ..layerops import qgis_poly_to_gdf, shape_data_array_to_raster_array, shape_raster_array_to_data_array

import logging
logger = logging.getLogger("statmagic_gui")


# Todo: Implement a similar flow to the other sample_from_... using self.raster_array and self.raster_dict to
# pass to run_kmeans using sample_from_polygon as example.
# Todo: add in self.layer_name from prep_kmeans that can be used as layer name in the QGIS Layer Tree

class KmeansClusteringMenu(QDialog):

    def __init__(self, parent=None):
        super(KmeansClusteringMenu, self).__init__(parent)
        QDialog.setWindowTitle(self, "K-Means Mapping")

        # preserve a pointer to the dockwidget to access its attributes
        self.parent = parent
        self.iface = self.parent.iface
        self.initUI()
        self.updateEnabled()

    def initUI(self):
        # Choose raster layer
        raster_label = QLabel('Raster Layer')
        self.raster_selection_box = QgsMapLayerComboBox(self)
        self.raster_selection_box.setShowCrs(True)
        self.raster_selection_box.setFilters(QgsMapLayerProxyModel.RasterLayer)

        # Data Selection Extent  |  ComboBox
        aoi_label = QLabel('Select Extent')
        self.aoi_selection_box = QComboBox(self)
        self.aoi_selection_box.setFixedWidth(300)
        self.aoi_selection_box.addItems(['Canvas', 'Full Raster', 'Use Vectory Layer Geometry',
                                             'Rectangle', 'Polygon'])
        self.aoi_selection_box.setCurrentIndex(4)

        vector_label = QLabel('Vector Layer')
        self.vector_selection_box = QgsMapLayerComboBox(self)
        self.vector_selection_box.setShowCrs(True)
        self.vector_selection_box.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.vector_selection_box.allowEmptyLayer()


        # These were the original options
        # data_items = ["Full Data", "Within Mask", "Within Polygons"]

        # Number of Clusters | ComboBox
        self.numClusters_selection_spin = QSpinBox(self)
        self.numClusters_selection_spin.setRange(2, 50)
        self.numClusters_selection_spin.setValue(8)
        self.numClusters_selection_spin.setSingleStep(1)

        # PCA Var Exp | FloatSpinBox
        self.pcaVarExp_selection_spin = QDoubleSpinBox(self)
        self.pcaVarExp_selection_spin.setRange(0.0, 1.0)
        self.pcaVarExp_selection_spin.setValue(0.95)
        self.pcaVarExp_selection_spin.setSingleStep(0.025)

        # Archetype Checkbox | CheckBox
        self.archTypecheck = QCheckBox(self)

        # Do PCA Checkbox | CheckBox
        self.doPCAcheck = QCheckBox(self)
        self.doPCAcheck.setChecked(True)

        # Exclusivity Threshold | FloatSpinBox
        self.archExcl_selection_spin = QDoubleSpinBox(self)
        self.archExcl_selection_spin.setRange(0.0, 1.0)
        self.archExcl_selection_spin.setValue(0.95)
        self.archExcl_selection_spin.setSingleStep(0.05)
        # self.archExcl_selection_spin.setEnabled(False)

        # Fuzzines | FloatSpinBox
        self.archFuzz_selection_spin = QDoubleSpinBox(self)
        self.archFuzz_selection_spin.setRange(1.0, 5.0)
        self.archFuzz_selection_spin.setValue(2.0)
        self.archFuzz_selection_spin.setSingleStep(0.25)
        # self.archFuzz_selection_spin.setEnabled(False)

        self.run_Kmeans_Button = QPushButton(self)
        self.run_Kmeans_Button.setText('Run Kmeans')
        self.run_Kmeans_Button.clicked.connect(self.prep_Kmeans)
        self.run_Kmeans_Button.setToolTip('Computes the Kmeans Clustering on the selected data')

        # self.map_clusters_Button = QPushButton(self)
        # self.map_clusters_Button.setText('Map Clusters')
        # self.map_clusters_Button.clicked.connect(self.map_kmeans_clusters)
        # self.map_clusters_Button.setToolTip('Spatializes the kmeans clusters and adds them to the map')

        self.map_clusters_check = QCheckBox(self)
        self.map_clusters_check.setChecked(True)
        self.map_clusters_check.setText('Map Clusters')
        self.map_clusters_check.setToolTip('Creates a rasterized output of the kmeans and adds to the map')

        # Buttons to draw area
        self.drawRectButton = QPushButton()
        self.drawRectButton.setText('Draw Rectangle')
        self.drawRectButton.clicked.connect(self.drawRect)
        self.drawPolyButton = QPushButton()
        self.drawPolyButton.setText('Draw Polygon')
        self.drawPolyButton.clicked.connect(self.drawPoly)

        # Layout for buttons
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.run_Kmeans_Button)
        # self.button_layout.addWidget(self.map_clusters_Button)
        self.button_layout.addWidget(self.map_clusters_check)

        # Layout for sampling buttons
        self.sampling_button_layout = QHBoxLayout()
        self.sampling_button_layout.addWidget(self.drawRectButton)
        self.sampling_button_layout.addWidget(self.drawPolyButton)

        # Inputs Panel
        self.input_layout = QFormLayout()
        self.input_layout.addRow(raster_label, self.raster_selection_box)
        self.input_layout.addRow(aoi_label, self.aoi_selection_box)
        self.input_layout.addRow(vector_label, self.vector_selection_box)
        self.input_layout.addRow('Choolse Number of Clusters', self.numClusters_selection_spin)
        self.input_layout.addRow('Standardize and PCA', self.doPCAcheck)
        self.input_layout.addRow('PCA Var Exp', self.pcaVarExp_selection_spin)
        self.input_layout.addRow('Return Archetypes', self.archTypecheck)
        self.input_layout.addRow('Archetype Exclusivity', self.archExcl_selection_spin)
        self.input_layout.addRow('Archetype Fuzziness', self.archFuzz_selection_spin)
        self.input_layout.addRow('Drawing Sampling', self.sampling_button_layout)

        # Populate dialog layout
        self.layout = QVBoxLayout(self)
        self.layout.addLayout(self.input_layout)
        self.layout.addLayout(self.button_layout)
        self.setLayout(self.layout)

    def drawRect(self):
        self.c = self.parent.canvas
        self.RectTool = RectangleMapTool(self.c)
        self.c.setMapTool(self.RectTool)

    def drawPoly(self):
        self.c = self.parent.canvas
        self.PolyTool = PolygonMapTool(self.c)
        self.c.setMapTool(self.PolyTool)

    def prep_Kmeans(self):
        self.pass_kmeans_checks()
        if self.aoi_selection_box.currentIndex() == 4:
            logger.debug('sampling from drawn Polygon')
            self.sample_from_polygon()

        if self.aoi_selection_box.currentIndex() == 3:
            logger.debug('sampling from Rectangle')
            self.sample_from_rectangle()

        if self.aoi_selection_box.currentIndex() == 2:
            logger.debug('sampling from vector geometry')
            self.sample_from_vector()

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

        self.run_kmeans()

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

        #
        # poly = self.RectTool.rectangle()
        # # Convert the polygon to a GeoDataFrame
        # poly_gdf = qgis_poly_to_gdf(poly, poly_crs, raster_crs)

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

        self.run_kmeans()
        pass

    def sample_from_vector(self):
        aoi = self.vector_selection_box.currentLayer()
        poly_crs = aoi.crs().authid()
        poly = aoi.selectedFeatures()[0].geometry()
        logger.debug(poly)
        raster = self.raster_selection_box.currentLayer()
        raster_path = raster.source()
        self.full_dict = getFullRasterDict_rio(rio.open(raster_path))
        raster_crs = raster.crs().authid()
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

        self.run_kmeans()

    def sample_full_raster(self):
        raster = self.raster_selection_box.currentLayer()
        raster_path = raster.source()
        self.raster_dict = getFullRasterDict_rio(rio.open(raster_path))
        self.raster_array = rio.open(raster_path).read()
        self.run_kmeans()

    def sample_from_canvas(self):
        r_ds = gdal.Open(self.raster_selection_box.currentLayer().source())
        self.full_dict = getFullRasterDict(r_ds)
        self.raster_dict = getCanvasRasterDict(self.full_dict, self.parent.canvas.extent())
        self.raster_array = r_ds.ReadAsArray(self.raster_dict['Xoffset'], self.raster_dict['Yoffset'],
                                        self.raster_dict['sizeX'], self.raster_dict['sizeY'])
        self.run_kmeans()

    def run_kmeans(self):

        num_clust = self.numClusters_selection_spin.value()
        doPCA = self.doPCAcheck.isChecked()

        data_array, msk = shape_raster_array_to_data_array(self.raster_array, self.raster_dict, return_mask=True)

        if doPCA is True:
            pca_data, pca = standardScale_and_PCA(data_array, 0.95)
            self.km = kmeans_fit_predict(pca_data, num_clust)
        else:
            self.km = kmeans_fit_predict(data_array, num_clust)

        labels = self.km.labels_ + 1

        add_to_map = self.map_clusters_check.isChecked()
        if add_to_map is True:
            raster_array = shape_data_array_to_raster_array(labels, self.raster_dict, mask_array=msk, nodata=0)
            self.raster_dict.update({'NoData': 0})
            output_raster_path = rasterio_write_raster_from_array(raster_array, self.raster_dict)
            logger.debug(output_raster_path)

            groupName = 'KmeansClusterOutputs'
            layerName = ' Kmeans Output'

            root = QgsProject.instance().layerTreeRoot()
            raster_layer = QgsRasterLayer(output_raster_path, layerName)
            QgsProject.instance().addMapLayer(raster_layer, False)
            layer = QgsLayerTreeLayer(raster_layer)

            if root.findGroup(groupName) == None:
                group = root.insertGroup(0, groupName)
            else:
                group = root.findGroup(groupName)
            group.insertChildNode(0, layer)

    def pass_kmeans_checks(self):
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

        if self.aoi_selection_box.currentIndex() == 2:
            logger.debug('drawing from vector geometry')
            if self.vector_selection_box.currentLayer() is None:
                msgBox = QMessageBox()
                msgBox.setText("You must select a valid vector / polygon layer to provide an AOI")
                msgBox.exec()
                return

            aoi = self.vector_selection_box.currentLayer()

            try:
                extents_feature = aoi.selectedFeatures()[0]
            except IndexError:
                msgBox = QMessageBox()
                msgBox.setText("You must select a feature from the vector layer")
                msgBox.exec()
                return

    def updateEnabled(self):
        pass
        # Todo: Figure out the statechanged business
        # enableArchOptions = False
        # enableRectButton = False
        # enablePolyButton = False
        # enableRunKmeans = False
        # enableMapClusters = False
        #
        # if self.archTypecheck.isChecked():
        #     enableArchOptions = True
        # else:
        #     enableArchOptions = False
        #
        # if enableArchOptions is True:
        #     self.archExcl_selection_spin.setEnabled(True)
        #     self.archFuzz_selection_spin.setEnabled(True)
