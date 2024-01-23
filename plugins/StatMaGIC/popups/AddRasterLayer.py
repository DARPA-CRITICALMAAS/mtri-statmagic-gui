import os

from PyQt5.QtWidgets import QDialogButtonBox
from qgis.PyQt import QtGui, QtWidgets
from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox, QgsFileWidget


class AddRasterLayer(QtWidgets.QDialog):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        # super(AddRasterLayer, self).__init__(parent)
        super(AddRasterLayer, self).__init__()

        # preserve a pointer to the dockwidget to access its attributes
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout()

        self.returnList = []

        self.comboBox = QgsMapLayerComboBox(self)
        self.fileInput = QgsFileWidget(self)
        self.descriptionBox = QtWidgets.QLineEdit(self)
        self.samplingBox = QtWidgets.QComboBox(self)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.samplingBox.addItems(['nearest', 'bilinear', 'cubic', 'cubic_spline', 'lanczos', 'average', 'mode', 'gauss'])

        label1 = QtWidgets.QLabel('Get from loaded layer:')
        label2 = QtWidgets.QLabel('Get from file path:')
        label3 = QtWidgets.QLabel('Select resampling method:')
        label4 = QtWidgets.QLabel('Add text description for band name:')
        label5 = QtWidgets.QLabel('Confirm Selection:')

        layout.addWidget(label1)
        layout.addWidget(self.comboBox)
        layout.addWidget(label2)
        layout.addWidget(self.fileInput)
        layout.addWidget(label3)
        layout.addWidget(self.samplingBox)
        layout.addWidget(label4)
        layout.addWidget(self.descriptionBox)
        layout.addWidget(label5)
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
        currentfile = self.comboBox.currentLayer()
        filepath = self.fileInput.filePath()
        method = self.samplingBox.currentText()
        description = self.descriptionBox.text()

        if currentfile:
            file_source = currentfile.source()
        elif filepath:
            file_source = filepath
        else:
            print('No selection made')

        self.parent.pathlist.append(file_source)
        self.parent.methodlist.append(method)
        self.parent.desclist.append(description)

        self.parent.refreshList(file_source)
        self.close()

    def cancel(self):
        self.close()
