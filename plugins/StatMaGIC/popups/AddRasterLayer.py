
from PyQt5.QtWidgets import QDialogButtonBox
from qgis.PyQt import QtGui, QtWidgets
from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox, QgsFileWidget
from ..layerops import rasterBandDescAslist

import logging
logger = logging.getLogger("statmagic_gui")


class AddRasterLayer(QtWidgets.QDialog):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        # super(AddRasterLayer, self).__init__(parent)
        super(AddRasterLayer, self).__init__()

        # preserve a pointer to the dockwidget to access its attributes
        self.parent = parent
        self.initUI()

        self.currentfile = None
        self.description = None

    def initUI(self):
        layout = QtWidgets.QVBoxLayout()

        self.comboBox = QgsMapLayerComboBox(self)
        self.descriptionBox = QtWidgets.QLineEdit(self)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        label1 = QtWidgets.QLabel('Choose layer:')
        label4 = QtWidgets.QLabel('Add text for band name:')
        label6 = QtWidgets.QLabel('Confirm Selection:')

        layout.addWidget(label1)
        layout.addWidget(self.comboBox)
        layout.addWidget(label4)
        layout.addWidget(self.descriptionBox)
        layout.addWidget(label6)
        layout.addWidget(self.buttonBox)

        self.comboBox.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.comboBox.setAllowEmptyLayer(True)
        self.comboBox.setCurrentIndex(0)
        self.signals_connection()
        self.setLayout(layout)

    def signals_connection(self):
        self.buttonBox.accepted.connect(self.returnLayerInfo)
        self.buttonBox.rejected.connect(self.cancel)

    def returnLayerInfo(self):
        self.currentfile = self.comboBox.currentLayer().source()
        self.description = self.descriptionBox.text()
        self.accept()

    def cancel(self):
        self.reject()
