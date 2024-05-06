# -*- coding: utf-8 -*-
import logging
from urllib.parse import parse_qsl

from qgis._core import QgsProject

gui_logger = logging.getLogger("statmagic_gui")
backend_logger = logging.getLogger("statmagic_backend")

from PyQt5.QtWidgets import QScrollArea, QAbstractScrollArea, QMessageBox
from qgis.PyQt.QtCore import pyqtSignal, QRect

from .gui_helpers import *
from .tabs.AWS import AWSTab
from .tabs.Geochemistry import GeochemistryTab
from .tabs.Predictions import PredictionsTab
from .tabs.TrainingPoints import TrainingPointsTab
from .tabs.InspectDataCubeLayers import InspectDataCubeLayersTab
from .tabs.RasterizationTools import RasterizationToolsTab
from .tabs.AddLayers import AddLayersTab
from .tabs.Home import HomeTab

from .tabs.Sciencebase import SciencebaseTab
from .tabs.Sparql import SparqlTab


class StatMaGICDockWidget(QtWidgets.QDockWidget):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(StatMaGICDockWidget, self).__init__(parent)
        self.iface = parent.iface
        self.canvas = self.iface.mapCanvas()
        self.setObjectName("StatMaGICDockWidget")
        self.dockWidgetContents = QtWidgets.QWidget(self)
        self.dockWidgetLayout = QtWidgets.QVBoxLayout()
        self.dockWidgetContents.setLayout(self.dockWidgetLayout)

        self.CMA_WorkflowLog = {}

        # mainly used to track CRS changes
        self.currentCRS = QgsProject.instance().crs()

        buttonWidget = addWidgetFromLayout(QtWidgets.QHBoxLayout(), self.dockWidgetContents)

        self.viewLogsButtonGUI = addButton(buttonWidget, "View GUI Logs", self.viewLogsGUI)
        self.viewLogsButtonBackend = addButton(buttonWidget, "View Backend Logs", self.viewLogsBackend)

        addToParentLayout(buttonWidget)

        # Connect callback so we can detect when the user adds a layer
        # QgsProject.instance().legendLayersAdded.connect(self.onLayersAdded)
        QgsProject.instance().layersAdded.connect(self.onLayersAdded)
        QgsProject.instance().layersRemoved.connect(self.onLayersRemoved)
        QgsProject.instance().crsChanged.connect(self.onNewCRS)

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
        self.home_tab                   = HomeTab(self, self.tabWidget)
        self.addLayers_tab              = AddLayersTab(self, self.tabWidget)
        self.inspectDataCubeLayers_tab  = InspectDataCubeLayersTab(self, self.tabWidget)
        self.rasterizationTools_tab     = RasterizationToolsTab(self, self.tabWidget)
        self.geochemistry_tab           = GeochemistryTab(self, self.tabWidget, isEnabled=False)
        self.trainingPoints_tab         = TrainingPointsTab(self, self.tabWidget)
        self.predictions_tab            = PredictionsTab(self, self.tabWidget)
        self.aws_tab                    = AWSTab(self, self.tabWidget)
        self.sciencebase_tab            = SciencebaseTab(self, self.tabWidget)
        self.sparql_tab                 = SparqlTab(self, self.tabWidget)

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

    def onLayersAdded(self, layers):
        """ Callback for when the user adds layers to the QGIS project. """
        for layer in layers:
            # derive human-readable layer type from the class name
            layer_type = (type(layer).__name__
                          .replace("Qgs", "")
                          .replace("Layer", " Layer")
                          .lower())

            layer_name = layer.name()
            layer_path = layer.dataProvider().dataSourceUri()

            # if the layer path has "://" in it, it's probably a URL
            if "://" in layer_path:
                # but the string might contain irrelevant URL parameters
                layer_dict = dict(parse_qsl(layer_path))
                if layer_dict:
                    # so we just want the web address part
                    layer_path = layer_dict["url"]

            gui_logger.info(f"User added a {layer_type} '{layer_name}' <{layer_path}>")

    def onLayersRemoved(self, layers):
        """ Callback for when the user removes layers from the QGIS project. """
        gui_logger.info(f"User removed the following layers: {layers}")

    def onNewCRS(self):
        """ Callback for when the Coordinate Reference System has changed. """
        crs = QgsProject.instance().crs()
        oldcrs = f"{self.currentCRS.authid()} '{self.currentCRS.description()}'"
        newcrs = f"{crs.authid()} '{crs.description()}'"
        gui_logger.warning(f"Project CRS changed from {oldcrs} to {newcrs}")
        self.currentCRS = crs

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()
