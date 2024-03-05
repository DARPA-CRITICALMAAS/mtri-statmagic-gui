from PyQt5 import QtWidgets
from qgis.gui import QgsRasterBandComboBox, QgsRasterHistogramWidget
from qgis.core import QgsMapLayerProxyModel

from .TabBase import TabBase
from ..gui_helpers import *
from ..popups.dropRasterLayer import RasterBandSelectionDialog
from ..popups.plotRasterHistogram import RasterHistQtPlot
from ..popups.pcaClusterAnalysis import PCAClusterQtPlot
from ..popups.grab_polygon import PolygonMapTool
from ..popups.grab_rectangle import RectangleMapTool

# These are the imports for trying to figure out the QgsRubberband for getting temporary polgyons from the canvas
# Goal is to be able to pull stats/results from rasters within a temporary object
from PyQt5.QtCore import QVariant, Qt, QPointF
from PyQt5.QtWidgets import QInputDialog, QLineEdit
from PyQt5.QtGui import QColor, QPolygonF
from qgis.core import QgsVectorLayer, QgsField, QgsPoint, QgsPolygon, QgsFeature, QgsDistanceArea, QgsGeometry, QgsProject
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand



class InspectLayersTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Inspect DataCube Layers")

        self.parent = parent
        self.iface = self.parent.iface

        ##### TOP FRAME - Insepetion options#####
        topFrame, topLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        topFormLayout = QtWidgets.QFormLayout()
        #
        # # Needs to set a raster box. Will need to think about having a copy of the datacube.tif
        # # So that one can be edited and one can be loaded in the QGIS TOC
        self.comboBox = QgsMapLayerComboBox(self)
        self.comboBox.setFilters(QgsMapLayerProxyModel.RasterLayer)
        # self.rasterBandBox = QgsRasterBandComboBox(self)
        # self.comboBox.layerChanged.connect(self.rasterBandBox.setLayer)
        #
        addFormItem(topFormLayout, "Raster / DataCube:", self.comboBox)
        # addFormItem(topFormLayout, "Choose Band: ", self.rasterBandBox)
        #
        addWidgetFromLayoutAndAddToParent(topFormLayout, topFrame)
        addToParentLayout(topFrame)

        self.drop_layers_button = addButton(self, "Drop Layers Menu", self.popup_drop_layer_dialogue)
        self.simple_plot_button = addButton(self, "Raster Histogram", self.popup_make_hist_plot)
        self.pca_cluster_button = addButton(self, "PCA and Cluster Analysis", self.popup_pca_cluster_analysis)

        ##### TOP STUFF #####
        topFrame1, topLayout1 = addFrame(self, "HBox", "NoFrame", "Plain", 3)

        data_items = ["Full Data", "Within Mask", "Within Polygons"]
        self.data_sel_box = addComboBox(topFrame1, "Data Selection", data_items, layout_str="VBox")
        self.NumClustersBox = addSpinBox(topFrame1, "# Clusters", "VBox", dtype=int, value=5, min=2)
        self.pca_var_exp = addSpinBox(topFrame1, "PCA var exp", "VBox", dtype=float,
                                      value=0.95, min=0.25, max=0.99, step=0.025)
        self.pca_var_exp.setDecimals(3)  # TODO: add to helper if this is a common operation


        addToParentLayout(topFrame1)

        topFrame2, topLayout2 = addFrame(self, "HBox", "NoFrame", "Sunken", 3)

        self.PCAbox = addCheckbox(topFrame2, "Standardize and PCA", isChecked=True)
        addEmptyFrame(topLayout2)  # force space between checkbox and addMSbutton
        self.RunKmeansButton = addButton(topFrame2, "Run Kmeans", self.selectKmeansData)

        addToParentLayout(topFrame2)

        addEmptyFrame(self.layout())  # force space between top stuff and map clusters frame

        ##### MAP CLUSTERS FRAME #####
        mapClustersFrame, mapClustersLayout = addFrame(self, "VBox", "Box", "Sunken", 2, margins=10)

        self.ArchetypeCheckBox = addCheckbox(mapClustersFrame, "Return Archetypes")

        subFrame, subLayout = addFrame(mapClustersFrame, "HBox", "NoFrame", "Sunken", 3)
        subLayout.setSpacing(5)

        formLayout = QtWidgets.QFormLayout(subFrame)
        self.ConfValue = addLineEditToForm(formLayout, "Confidence Threshold", value=0.95)
        self.FuzzinessValue = addLineEditToForm(formLayout, "Fuzziness Metric (1-5)", value=2)
        subLayout.addLayout(formLayout)

        self.MapClustersButton = addButton(subFrame, "Map Clusters", self.map_clusters)

        addToParentLayout(subFrame)
        addToParentLayout(mapClustersFrame)

        self.test_rubberPoly_button = addButton(self, "test Poly rubberband", self.drawPolygon)
        self.test_rubberRect_button = addButton(self, "test Rect rubberband", self.drawRectangle)
        self.test_rect_button = addButton(self, "test Rect result", self.print_rect)

    def popup_drop_layer_dialogue(self):
        popup = RasterBandSelectionDialog(self.parent, raster_layer=self.comboBox.currentLayer())
        popup.exec_()

    def popup_make_hist_plot(self):
        popup = RasterHistQtPlot(self.parent)
        self.hist_window = popup.show()

    def popup_pca_cluster_analysis(self):
        popup = PCAClusterQtPlot(self.parent)
        self.pca_window = popup.show()

    def map_clusters(self):
        pass

    def selectKmeansData(self):
        pass
    #
    def drawPolygon(self):
        self.c = self.parent.canvas
        self.t = PolygonMapTool(self.c)
        self.c.setMapTool(self.t)


    def drawRectangle(self):
        print('launching Rectangle Tool')
        self.c = self.parent.canvas
        self.t = RectangleMapTool(self.c)
        self.c.setMapTool(self.t)


    def print_rect(self):
        print('Rectangle is:', self.t.rectangle())



