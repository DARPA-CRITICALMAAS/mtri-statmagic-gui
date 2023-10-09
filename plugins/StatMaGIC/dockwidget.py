from qgis.PyQt import QtGui, QtWidgets
from qgis.PyQt.QtCore import pyqtSignal, QRect

from pathlib import Path


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
        self.tabWidget = QtWidgets.QTabWidget(self.dockWidgetContents)
        self.tabWidget.setGeometry(QRect(10, 60, 391, 511))
        self.tabWidget.setObjectName("tabWidget")
        self.unsupervised_tab = QtWidgets.QWidget()
        self.unsupervised_tab.setObjectName("unsupervised_tab")
        self.tabWidget.addTab(self.unsupervised_tab, "")
        self.supervised_tab = QtWidgets.QWidget()
        self.supervised_tab.setObjectName("supervised_tab")
        self.tabWidget.addTab(self.supervised_tab, "")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.unsupervised_tab), "Unsupervised")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.supervised_tab), "Supervised")
        self.setWidget(self.dockWidgetContents)
        pass

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()