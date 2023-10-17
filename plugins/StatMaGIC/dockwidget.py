from qgis.PyQt import QtGui, QtWidgets, QtCore
from qgis.PyQt.QtCore import pyqtSignal, QRect

from pathlib import Path
from osgeo import gdal

from .utils import getSelectionAsArray, gdalSave
from .gui import *


class StatMaGICDockWidget(QtWidgets.QDockWidget):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(StatMaGICDockWidget, self).__init__(parent)
        self.iface = parent.iface
        self.canvas = self.iface.mapCanvas()
        self.setObjectName("StatMaGICDockWidget")
        self.dockWidgetContents = QtWidgets.QWidget(self)

        # create tab container
        self.tabWidget = QtWidgets.QTabWidget(self.dockWidgetContents)
        self.tabWidget.setGeometry(QRect(10, 60, 391, 511))

        # create tabs
        mineral_tab = addTab(self.tabWidget, "Mineral Assessment")
        geochemistry_tab = addTab(self.tabWidget, "Geo Chemistry")
        geology_tab = addTab(self.tabWidget, "Geology")

        # who
        self.nameInput = addTextInput(mineral_tab, "Investigator Name")

        # what
        self.mineralBox = addComboBox(mineral_tab, "Mineral of Interest", ["Aluminum", "Copper", "Silicon"])
        self.studyAreaBox = addComboBox(mineral_tab, "Define Study Area", ["Draw Rectangle", "Inherit from Layer", "Canvas Extent"])
        # select resolution
        self.pixelSizeBox = addSpinBox(mineral_tab, "Pixel Size", 10., 5000.)
        self.addBufferBox = addSpinBox(mineral_tab, "Buffer", 0., 10000.)
        #   data storage calculator
        # outputs : json, template raster, data pointer list (empty)

        self.mineralRunButton = QtWidgets.QPushButton(mineral_tab)
        self.mineralRunButton.setText("Run Mineral\nAssessment")
        self.mineralRunButton.setGeometry(QRect(300, 400, 80, 33))
        self.mineralRunButton.clicked.connect(self.display)

        # geochemistry
        #   soil
        #   mineral
        #   rock
        # geology

        self.PrintBox = QtWidgets.QLineEdit(self.dockWidgetContents)
        self.PrintBox.setGeometry(QRect(10, 578, 231, 41))
        self.PrintBox.setFrame(True)

        self.setWidget(self.dockWidgetContents)

        # self.setAllObjectNames()
        pass

    def getTab(self, item) -> QtWidgets.QWidget:
        if isinstance(item, int):
            return self.tabWidget.widget(item)
        else:
            return self.tabWidget.findChild(QtWidgets.QWidget, item)

    def setAllObjectNames(self):
        for objName in dir(self):
            if not objName.startswith("__"):
                try:
                    subObject = self.__getattr__(objName)
                    if subObject.objectName() == "":
                        subObject.setObjectName(objName)
                except AttributeError:
                    continue

    def display(self):
        message = (f"{self.nameInput.displayText()} wants to assess "
                   f"{self.mineralBox.currentText()} in the area defined by "
                   f"{self.studyAreaBox.currentText()} at pixel size "
                   f"{self.pixelSizeBox.value()} with buffer "
                   f"{self.addBufferBox.value()}.")
        self.iface.messageBar().pushMessage(message)

    def greyscale(self):
        selectedLayer = self.iface.layerTreeView().selectedLayers()[0]
        extent = self.canvas.extent()
        data, geot, r_proj = getSelectionAsArray(selectedLayer, extent)

        mean = ((data[0, :, :] + data[1, :, :] + data[2, :, :]) / 3).astype("uint8")

        savedFilename = gdalSave("grey", mean, gdal.GDT_Byte, geot, r_proj)
        message = f"greyscale output saved to {savedFilename}"
        self.iface.messageBar().pushMessage(message)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()