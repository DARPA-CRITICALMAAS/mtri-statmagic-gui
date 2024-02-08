# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import pyqtSignal, QRect

from .gui_helpers import *
from .tabs.Beak import BeakTab
from .tabs.Geochemistry import GeochemistryTab
from .tabs.InitiateCMA import InitiateCMATab
from .tabs.Predictions import PredictionsTab
from .tabs.TrainingPoints import TrainingPointsTab
from .tabs.Inspect_Raster_Layers import InspectLayersTab
from .tabs.Rasterization import RasterizationTab
from .tabs.AddLayers import AddLayersTab
from .tabs.SRI import SRITab


class StatMaGICDockWidget(QtWidgets.QDockWidget):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(StatMaGICDockWidget, self).__init__(parent)
        self.iface = parent.iface
        self.canvas = self.iface.mapCanvas()
        self.setObjectName("StatMaGICDockWidget")
        self.resize(485, 642)
        self.dockWidgetContents = QtWidgets.QWidget(self)
        self.dockWidgetLayout = QtWidgets.QVBoxLayout()
        self.dockWidgetContents.setLayout(self.dockWidgetLayout)

        self.addGlobalOptions()

        self.createTabs()

        self.setWidget(self.dockWidgetContents)

        # Variables that need access from multiple tabs
        self.meta_data = {}
        self.point_samples = None
        self.oneClassSVM = None

    def addGlobalOptions(self):
        """ Add the stuff that always appears above the tabs. """
        self.topLayout = QtWidgets.QHBoxLayout()
        self.topWidget = addWidgetFromLayout(self.topLayout, self.dockWidgetContents)

        # self.comboBox_raster = addQgsMapLayerComboBox(self.topWidget, "Raster Layer")
        # self.comboBox_vector = addQgsMapLayerComboBox(self.topWidget, "Polygon Layer")
        #
        # self.comboBox_raster.setFilters(QgsMapLayerProxyModel.RasterLayer)
        # self.comboBox_vector.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        #
        # (
        #     self.ClusterWholeExtentBox,
        #     self.UseBandSelectionBox
        # ) = addTwoCheckboxes(self.topWidget, "Whole Raster", "Use Selected Bands Only")

        addToParentLayout(self.topWidget)

    def createTabs(self):
        # create tab container
        self.tabWidget = QtWidgets.QTabWidget(self.dockWidgetContents)
        self.tabWidget.setGeometry(QRect(10, 60, 391, 511))

        # populate tabs
        self.initiateCMA_tab = InitiateCMATab(self, self.tabWidget)
        self.addLayers_tab          = AddLayersTab(self, self.tabWidget)
        self.InspectLayersTab       = InspectLayersTab(self, self.tabWidget)
        self.rasterize_tab          = RasterizationTab(self, self.tabWidget)
        self.geochemistry_tab       = GeochemistryTab(self, self.tabWidget)
        self.trainingPoints_tab     = TrainingPointsTab(self, self.tabWidget)
        self.predictions_tab        = PredictionsTab(self, self.tabWidget)
        self.sri_tab                = SRITab(self, self.tabWidget)
        self.beak_tab               = BeakTab(self, self.tabWidget)

        # add tabs to parent
        addToParentLayout(self.tabWidget)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()
