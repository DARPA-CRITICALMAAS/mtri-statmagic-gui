from PyQt5 import QtWidgets
from qgis.gui import QgsRasterBandComboBox, QgsRasterHistogramWidget
from qgis.core import QgsMapLayerProxyModel

from .TabBase import TabBase
from ..gui_helpers import *
from ..popups.dropRasterLayer import RasterBandSelectionDialog
from ..popups.plotRasterHistogram import RasterHistQtPlot
# from ..popups.plotRasterScatterPlot import RasterScatQtPlot
# from ..popups.pcaClusterAnalysis import PCAClusterQtPlot
from ..popups.ClusterMappingDialog import KmeansClusteringMenu
from ..popups.choose_raster_dialog import SelectRasterLayer
from ..popups.plotting.raster_PCA_Cluster_plot import RasterPCAQtPlot
from ..popups.plotting.default_plotter import RasterScatQtPlot

import logging
logger = logging.getLogger("statmagic_gui")


class InspectDataCubeLayersTab(TabBase):
    def __init__(self, parent, tabWidget, isEnabled=True):
        super().__init__(parent, tabWidget, "Inspect DataCube Layers", isEnabled)

        self.parent = parent
        self.iface = self.parent.iface

        self.drop_layer = None

        self.drop_layers_button = addButton(self, "Drop Layers Menu", self.popup_drop_layer_dialogue)
        self.simple_plot_button = addButton(self, "Raster Histogram", self.popup_make_hist_plot)
        self.scatter_plot_button = addButton(self, "Template Plot - Raster Bands ScatterPlot", self.popup_make_scatter_plot)
        self.raster_pca_button = addButton(self, "Raster PCA Plot", self.popup_make_rasterPCA_plot)
        # self.pca_cluster_button = addButton(self, "PCA and Cluster Analysis", self.popup_pca_cluster_analysis)
        self.spatial_kmeans_button = addButton(self, "Spatial K-Means Mapping", self.popup_spatial_kmeans_analysis)

        self.scatter_plot_button.setEnabled(True)
        self.raster_pca_button.setEnabled(False)
        # self.pca_cluster_button.setEnabled(False)

    def popup_drop_layer_dialogue(self):
        raster_path_popup = SelectRasterLayer(self.parent)
        if raster_path_popup.exec_():
            raster = raster_path_popup.chosen_raster

            popup = RasterBandSelectionDialog(self.parent, raster_layer=raster)
            popup.exec_()

    def popup_make_hist_plot(self):
        popup = RasterHistQtPlot(self.parent)
        self.hist_window = popup.show()

    # def popup_pca_cluster_analysis(self):
    #     popup = PCAClusterQtPlot(self.parent)
    #     self.pca_window = popup.show()

    def popup_spatial_kmeans_analysis(self):
        popup = KmeansClusteringMenu(self.parent)
        self.spatial_kmeans_window = popup.show()

    def popup_make_scatter_plot(self):
        # Todo: make a popup to select which raster layer will have bands dropped
        # Probably a simple dialog with a MapLayerComboBox
        # The raster_layer should be a QgsRasterLayer
        popup = RasterScatQtPlot(self.parent)
        self.scatter_window = popup.show()

    def popup_make_rasterPCA_plot(self):
        popup = RasterPCAQtPlot(self.parent)
        self.raster_pca_window = popup.show()

