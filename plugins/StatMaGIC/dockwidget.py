from qgis.PyQt import QtGui, QtWidgets
from qgis.PyQt.QtCore import pyqtSignal, QRect

from pathlib import Path
from osgeo import gdal


class StatMaGICDockWidget(QtWidgets.QDockWidget):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(StatMaGICDockWidget, self).__init__(parent)
        self.setObjectName("StatMaGICDockWidget")
        self.dockWidgetContents = QtWidgets.QWidget(self)
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.gridLayout = QtWidgets.QGridLayout(self.dockWidgetContents)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(self.dockWidgetContents)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        # create tab container
        self.tabWidget = QtWidgets.QTabWidget(self.dockWidgetContents)
        self.tabWidget.setGeometry(QRect(10, 60, 391, 511))
        self.tabWidget.setObjectName("tabWidget")

        self.addTab("Unsupervised")
        self.addTab("Supervised")

        self.setWidget(self.dockWidgetContents)
        pass

    def addTab(self, tabName):
        newTab = QtWidgets.QWidget()
        newTab.setObjectName(tabName)
        self.tabWidget.addTab(newTab, "")
        self.tabWidget.setTabText(self.tabWidget.indexOf(newTab), tabName)
        setattr(self, tabName, newTab)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()