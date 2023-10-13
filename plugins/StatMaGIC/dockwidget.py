from qgis.PyQt import QtGui, QtWidgets, QtCore
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

        # create tab container
        self.tabWidget = QtWidgets.QTabWidget(self.dockWidgetContents)
        self.tabWidget.setGeometry(QRect(10, 60, 391, 511))

        # create tabs
        mineral_tab = self.addTab("Mineral Assessment")
        geochemistry_tab = self.addTab("Geo Chemistry")
        geology_tab = self.addTab("Geology")

        # who
        self.nameInput = self.addTextInput(mineral_tab, "Investigator Name")

        # what
        self.mineralBox = self.addComboBox(mineral_tab, "Mineral of Interest:", ["Aluminum", "Copper", "Silicon"])
        self.studyAreaBox = self.addComboBox(mineral_tab, "Define Study Area:", ["Draw Rectangle", "Inherit from Layer", "Canvas Extent"])
        # select resolution
        self.xSpinBox, self.ySpinBox = self.addDoubleSpinBox(mineral_tab, "Resolution:", 1280, 720)
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

        self.setAllObjectNames()
        pass

    def getTab(self, item) -> QtWidgets.QWidget:
        if isinstance(item, int):
            return self.tabWidget.widget(item)
        else:
            return self.tabWidget.findChild(QtWidgets.QWidget, item)

    def addTab(self, tabName):
        # create tab
        newTab = QtWidgets.QWidget()
        newTab.setObjectName(tabName)

        # set layout such that each subcomponent is arranged vertically
        tabLayout = QtWidgets.QVBoxLayout()
        tabLayout.setSpacing(0)
        tabLayout.setAlignment(QtCore.Qt.AlignTop)
        newTab.setLayout(tabLayout)

        # add tab to reference objects and return
        self.tabWidget.addTab(newTab, "")
        self.tabWidget.setTabText(self.tabWidget.indexOf(newTab), tabName)
        return newTab

    def addLabel(self, layout, text):
        label = QtWidgets.QLabel()
        label.setText(text)
        label.setMinimumWidth(label.fontMetrics().width(label.text()))
        layout.addWidget(label)

    def addToParentLayout(self, layout, parent):
        widget = QtWidgets.QWidget(parent)
        widget.setLayout(layout)
        parent.layout().addWidget(widget)

    def addDoubleSpinBox(self, parent, name, x, y, maxResX=1920, maxResY=1080):
        layout = QtWidgets.QHBoxLayout()

        self.addLabel(layout, name)

        xSpinBox = QtWidgets.QSpinBox()
        ySpinBox = QtWidgets.QSpinBox()
        xSpinBox.setMaximum(maxResX)
        ySpinBox.setMaximum(maxResY)
        xSpinBox.setValue(x)
        ySpinBox.setValue(y)

        layout.addWidget(xSpinBox)
        layout.addWidget(ySpinBox)

        self.addToParentLayout(layout, parent)

        return xSpinBox, ySpinBox

    def addTextInput(self, parent, text):
        layout = QtWidgets.QHBoxLayout()

        self.addLabel(layout, text)

        # TODO: make the QLineEdit object expand width to fill parent
        inputBox = QtWidgets.QLineEdit()
        layout.addWidget(inputBox)

        self.addToParentLayout(layout, parent)

        return inputBox

    def addComboBox(self, parent, text, items, default=None):
        layout = QtWidgets.QHBoxLayout()

        self.addLabel(layout, text)

        # TODO: make the QComboBox object expand width to fill parent
        comboBox = QtWidgets.QComboBox()
        comboBox.addItems(items)
        # TODO: figure out how to set default selection
        layout.addWidget(comboBox)

        self.addToParentLayout(layout, parent)

        return comboBox

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
                   f"{self.studyAreaBox.currentText()} at resolution "
                   f"{self.xSpinBox.value()} x {self.ySpinBox.value()}.")
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