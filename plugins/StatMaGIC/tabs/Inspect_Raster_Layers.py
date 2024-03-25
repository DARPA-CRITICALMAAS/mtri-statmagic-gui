from PyQt5 import QtWidgets
from qgis.gui import QgsRasterBandComboBox, QgsRasterHistogramWidget
from qgis.core import QgsMapLayerProxyModel

from .TabBase import TabBase
from ..gui_helpers import *
from ..popups.dropRasterLayer import RasterBandSelectionDialog
from ..popups.plotRasterHistogram import RasterHistQtPlot
from ..popups.plotRasterScatterPlot import RasterScatQtPlot
from ..popups.pcaClusterAnalysis import PCAClusterQtPlot
from ..popups.grab_polygon import PolygonMapTool
from ..popups.grab_rectangle import RectangleMapTool
from ..popups.ClusterMappingDialog import KmeansClusteringMenu
from ..popups.choose_raster_dialog import SelectRasterLayer


class InspectLayersTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Inspect DataCube Layers")

        self.parent = parent
        self.iface = self.parent.iface

        self.drop_layer = None

        self.drop_layers_button = addButton(self, "Drop Layers Menu", self.popup_drop_layer_dialogue)
        self.simple_plot_button = addButton(self, "Raster Histogram", self.popup_make_hist_plot)
        self.scatter_plot_button = addButton(self, "Raster Scatter Plot", self.popup_make_scatter_plot)
        self.pca_cluster_button = addButton(self, "PCA and Cluster Analysis", self.popup_pca_cluster_analysis)
        self.spatial_kmeans_button = addButton(self, "Spatial K-Means Mapping", self.popup_spatial_kmeans_analysis)



    def popup_drop_layer_dialogue(self):
        raster_path_popup = SelectRasterLayer(self.parent)
        raster_path_popup.exec_()
        raster = raster_path_popup.chosen_raster

        popup = RasterBandSelectionDialog(self.parent, raster_layer=raster)
        popup.exec_()

    def popup_make_hist_plot(self):
        popup = RasterHistQtPlot(self.parent)
        self.hist_window = popup.show()

    def popup_pca_cluster_analysis(self):
        popup = PCAClusterQtPlot(self.parent)
        self.pca_window = popup.show()

    def popup_spatial_kmeans_analysis(self):
        popup = KmeansClusteringMenu(self.parent)
        self.spatial_kmeans_window = popup.show()

    def popup_make_scatter_plot(self):
        # Todo: make a popup to select which raster layer will have bands dropped
        # Probably a simple dialog with a MapLayerComboBox
        # The raster_layer should be a QgsRasterLayer
        popup = RasterScatQtPlot(self.parent)
        self.scatter_window = popup.show()

    # def drawPolygon(self):
    #     self.c = self.parent.canvas
    #     self.t = PolygonMapTool(self.c)
    #     self.c.setMapTool(self.t)
    #
    # def drawRectangle(self):
    #     print('launching Rectangle Tool')
    #     self.c = self.parent.canvas
    #     self.t = RectangleMapTool(self.c)
    #     self.c.setMapTool(self.t)
    #
    # def print_rect(self):
    #     print('Rectangle is:', self.t.rectangle())
    #
    #

