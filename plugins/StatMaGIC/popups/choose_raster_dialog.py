from PyQt5.QtWidgets import QDialogButtonBox
from qgis.PyQt import QtGui, QtWidgets
from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsMapLayerProxyModel, QgsRasterLayer
from qgis.gui import QgsMapLayerComboBox, QgsFileWidget
from ..layerops import rasterBandDescAslist

import logging
logger = logging.getLogger("statmagic_gui")


class SelectRasterLayer(QtWidgets.QDialog):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(SelectRasterLayer, self).__init__()

        # preserve a pointer to the dockwidget to access its attributes
        self.parent = parent
        self.chosen_raster = None
        self.initUI()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout()

        self.comboBox = QgsMapLayerComboBox(self)
        self.fileInput = QgsFileWidget(self)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        label1 = QtWidgets.QLabel('Choose From Current Map Layers:')
        label2 = QtWidgets.QLabel('Choose From File Path:')

        layout.addWidget(label1)
        layout.addWidget(self.comboBox)
        layout.addWidget(label2)
        layout.addWidget(self.fileInput)
        layout.addWidget(self.buttonBox)

        self.comboBox.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.comboBox.allowEmptyLayer()
        self.comboBox.setCurrentIndex(-1)
        self.signals_connection()
        self.setLayout(layout)

    def signals_connection(self):
        self.buttonBox.accepted.connect(self.return_raster)
        self.buttonBox.rejected.connect(self.cancel)

    def return_raster(self):

        currentfile = self.comboBox.currentLayer()
        filepath = self.fileInput.filePath()

        if currentfile:
            self.chosen_raster = currentfile
        elif filepath:
            self.chosen_raster = QgsRasterLayer(filepath)
        else:
            logger.debug('No selection made')



        # self.parent.drop_layer = self.chosen_raster
        self.closingPlugin.emit()
        self.accept()

    def cancel(self):
        self.closingPlugin.emit()
        self.reject()