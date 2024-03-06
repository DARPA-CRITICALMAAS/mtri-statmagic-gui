
from PyQt5.QtWidgets import  QDialog, QVBoxLayout, QPushButton, QLabel, QCheckBox, \
    QComboBox, QSpinBox, QDoubleSpinBox, QFormLayout, QHBoxLayout
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsProject, QgsMapLayerProxyModel

from shapely.geometry import box
from shapely.wkt import loads
import geopandas as gpd


from ..popups.grab_polygon import PolygonMapTool
from ..popups.grab_rectangle import RectangleMapTool

class KmeansClusteringMenu(QDialog):

    def __init__(self, parent=None):
        super(KmeansClusteringMenu, self).__init__(parent)
        QDialog.setWindowTitle(self, "K-Means Mapping")

        # preserve a pointer to the dockwidget to access its attributes
        self.parent = parent
        self.iface = self.parent.iface
        self.initUI()

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
        # These were the original options
        # data_items = ["Full Data", "Within Mask", "Within Polygons"]

        # Number of Clusters | ComboBox
        self.numClusters_selection_spin = QSpinBox(self)
        self.numClusters_selection_spin.setRange(2, 50)
        self.numClusters_selection_spin.setValue(2)
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

        # Exclusivity Threshold | FloatSpinBox
        self.archExcl_selection_spin = QDoubleSpinBox(self)
        self.archExcl_selection_spin.setRange(0.0, 1.0)
        self.archExcl_selection_spin.setValue(0.95)
        self.archExcl_selection_spin.setSingleStep(0.05)

        # Fuzzines | FloatSpinBox
        self.archFuzz_selection_spin = QDoubleSpinBox(self)
        self.archFuzz_selection_spin.setRange(1.0, 5.0)
        self.archFuzz_selection_spin.setValue(2.0)
        self.archFuzz_selection_spin.setSingleStep(0.25)

        self.run_Kmeans_Button = QPushButton(self)
        self.run_Kmeans_Button.setText('Run Kmeans')
        self.run_Kmeans_Button.clicked.connect(self.run_Kmeans)
        self.run_Kmeans_Button.setToolTip('Computes the Kmeans Clustering on the selected data')

        self.map_clusters_Button = QPushButton(self)
        self.map_clusters_Button.setText('Map Clusters')
        self.map_clusters_Button.clicked.connect(self.map_kmeans_clusters)
        self.map_clusters_Button.setToolTip('Spatializes the kmeans clusters and adds them to the map')

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
        self.button_layout.addWidget(self.map_clusters_Button)

        # Layout for sampling buttons
        self.sampling_button_layout = QHBoxLayout()
        self.sampling_button_layout.addWidget(self.drawRectButton)
        self.sampling_button_layout.addWidget(self.drawPolyButton)

        # Inputs Panel
        self.input_layout = QFormLayout()
        self.input_layout.addRow(raster_label, self.raster_selection_box)
        self.input_layout.addRow(aoi_label, self.aoi_selection_box)
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
    def run_Kmeans(self):
        pass

    def map_kmeans_clusters(self):
        pass


    #
    # def capture_canvas_extent(self):
    #     self.crs_epsg = QgsProject.instance().crs().authid()
    #     bb = self.parent.parent.canvas.extent()
    #     bb.asWktCoordinates()
    #     bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
    #     shapelyBox = box(*bbc)
    #     self.extent_gdf = gpd.GeoDataFrame(geometry=[shapelyBox], crs=self.crs_epsg)
    #     self.DeterminedExtentText.setText('Bounds Pulled From Canvas Extent')
    #
    # def get_extent_from_LayerComboBox(self):
    #     selectedLayer = self.selectfromLayerBox.currentLayer()
    #     self.crs_epsg = selectedLayer.crs().authid()
    #     bb = selectedLayer.extent()
    #     bb.asWktCoordinates()
    #     bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
    #     shapelyBox = box(*bbc)
    #
    #     if self.useSelectedFeatureCheck.isChecked():
    #         sel = selectedLayer.selectedFeatures()[0]
    #         shapely_poly = loads(sel.geometry().asWkt())
    #         self.extent_gdf = gpd.GeoDataFrame(geometry=[shapely_poly], crs=self.crs_epsg)
    #         self.DeterminedExtentText.setText('Bounds And Geometry Pulled From Selected Features')
    #     else:
    #         self.extent_gdf = gpd.GeoDataFrame(geometry=[shapelyBox], crs=self.crs_epsg)
    #         self.DeterminedExtentText.setText('Bounds Pulled From Selected Layer Extent')
    #
    # def returnExtent(self):
    #     self.parent.extent_gdf = self.extent_gdf
    #     self.parent.src_crs = self.crs_epsg
    #     self.close()
    #
    # def draw_on_canvas(self):
    #     bb = self.parent.canvas.extent()
    #     bb.asWktCoordinates()
    #     bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
    #
    #
    # def cancel(self):
    #     self.close()
