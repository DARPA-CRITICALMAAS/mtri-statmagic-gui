from qgis.PyQt import QtGui, QtWidgets
from qgis.PyQt.QtCore import pyqtSignal, QRect

from pathlib import Path
from osgeo import gdal

from .utils import getSelectionAsArray, gdalSave


class StatMaGICDockWidget(QtWidgets.QDockWidget):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(StatMaGICDockWidget, self).__init__(parent)
        self.iface = parent.iface
        self.canvas = self.iface.mapCanvas()
        self.setObjectName("StatMaGICDockWidget")
        self.dockWidgetContents = QtWidgets.QWidget(self)
        self.gridLayout = QtWidgets.QGridLayout(self.dockWidgetContents)
        self.label = QtWidgets.QLabel(self.dockWidgetContents)
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        # create tab container
        self.tabWidget = QtWidgets.QTabWidget(self.dockWidgetContents)
        self.tabWidget.setGeometry(QRect(10, 60, 391, 511))

        Unsupervised_tab = self.addTab("Unsupervised")
        Supervised_tab = self.addTab("Supervised")

        self.MakeTempLayer = QtWidgets.QPushButton(Unsupervised_tab)
        self.MakeTempLayer.setGeometry(QRect(262, 10, 121, 25))
        self.MakeTempLayer.setText("Make Train Layer")
        self.MakeTempLayer.clicked.connect(self.greyscale)

        self.setWidget(self.dockWidgetContents)

        self.setAllObjectNames()
        pass

    def getTab(self, item) -> QtWidgets.QWidget:
        if isinstance(item, int):
            return self.tabWidget.widget(item)
        else:
            return self.tabWidget.findChild(QtWidgets.QWidget, item)

    def addTab(self, tabName):
        newTab = QtWidgets.QWidget()
        newTab.setObjectName(tabName)
        self.tabWidget.addTab(newTab, "")
        self.tabWidget.setTabText(self.tabWidget.indexOf(newTab), tabName)
        return newTab

    def setAllObjectNames(self):
        for objName in dir(self):
            if not objName.startswith("__"):
                try:
                    subObject = self.__getattr__(objName)
                    if subObject.objectName() == "":
                        subObject.setObjectName(objName)
                except AttributeError:
                    continue

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