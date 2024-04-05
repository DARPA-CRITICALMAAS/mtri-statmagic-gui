# -*- coding: utf-8 -*-
import logging
gui_logger = logging.getLogger("statmagic_gui")
backend_logger = logging.getLogger("statmagic_backend")

from PyQt5.QtWidgets import QScrollArea, QAbstractScrollArea, QMessageBox
from qgis.PyQt.QtCore import pyqtSignal, QRect

from .gui_helpers import *
from .tabs.AWS import AWSTab
# from .tabs.Beak import BeakTab
# from .tabs.SRI import SRITab
from .tabs.Geochemistry import GeochemistryTab
from .tabs.InitiateCMA import InitiateCMATab
from .tabs.Predictions import PredictionsTab
from .tabs.TrainingPoints import TrainingPointsTab
from .tabs.Inspect_Raster_Layers import InspectLayersTab
from .tabs.Rasterization import RasterizationTab
from .tabs.AddLayers import AddLayersTab

from .tabs.TA2 import TA2Tab
from .tabs.Sciencebase import SciencebaseTab
from .tabs.CollapsiblePractice import CollapsibleTab


class StatMaGICDockWidget(QtWidgets.QDockWidget):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(StatMaGICDockWidget, self).__init__(parent)
        self.iface = parent.iface
        self.canvas = self.iface.mapCanvas()
        self.setObjectName("StatMaGICDockWidget")
        # self.resize(200, 300)
        self.dockWidgetContents = QtWidgets.QWidget(self)
        self.dockWidgetLayout = QtWidgets.QVBoxLayout()
        self.dockWidgetContents.setLayout(self.dockWidgetLayout)

        self.CMA_WorkflowLog = {}

        # buttonFrame, buttonLayout = addFrame(self.dockWidgetContents, "HBox", "NoFrame", "Plain", 3)
        buttonWidget = addWidgetFromLayout(QtWidgets.QHBoxLayout(), self.dockWidgetContents)

        self.viewLogsButtonGUI = addButton(buttonWidget, "View GUI Logs", self.viewLogsGUI)
        self.viewLogsButtonBackend = addButton(buttonWidget, "View Backend Logs", self.viewLogsBackend)

        addToParentLayout(buttonWidget)

        self.createTabs()

        self.setWidget(self.dockWidgetContents)

        # Variables that need access from multiple tabs
        self.meta_data = {}
        self.point_samples = None
        self.oneClassSVM = None

    def createTabs(self):
        # create containing widget to allow scroll bars to appear on resize
        self.scrollArea = QScrollArea(self.dockWidgetContents)
        self.scrollArea.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.scrollArea.setContentsMargins(0,0,0,0)
        self.scrollArea.setFrameStyle(QScrollArea.NoFrame)
        # self.scrollArea.setLayout(QtWidgets.QVBoxLayout)

        # create tab container
        self.tabWidget = QtWidgets.QTabWidget(self.dockWidgetContents)

        # populate tabs
        self.initiateCMA_tab = InitiateCMATab(self, self.tabWidget)
        self.addLayers_tab          = AddLayersTab(self, self.tabWidget)
        self.InspectLayersTab       = InspectLayersTab(self, self.tabWidget)
        self.rasterize_tab          = RasterizationTab(self, self.tabWidget)
        self.geochemistry_tab       = GeochemistryTab(self, self.tabWidget)
        self.trainingPoints_tab     = TrainingPointsTab(self, self.tabWidget)
        self.predictions_tab        = PredictionsTab(self, self.tabWidget)
        # self.sri_tab                = SRITab(self, self.tabWidget)
        # self.beak_tab               = BeakTab(self, self.tabWidget)
        self.ta2_tab                = TA2Tab(self, self.tabWidget)
        self.aws_tab                = AWSTab(self, self.tabWidget)
        self.sciencebase_tab        = SciencebaseTab(self, self.tabWidget)
        self.collapsible_tab = CollapsibleTab(self, self.tabWidget)

        # add tabs to parent
        # addToParentLayout(self.tabWidget)
        self.scrollArea.setWidget(self.tabWidget)
        addToParentLayout(self.scrollArea)

    def viewLogsGUI(self):
        logPopup = QMessageBox()
        logPopup.setText(gui_logger.handlers[0].stream.__str__())
        logPopup.exec()
        pass

    def viewLogsBackend(self):
        logPopup = QMessageBox()
        logPopup.setText(backend_logger.handlers[0].stream.__str__())
        logPopup.exec()
        pass

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()
