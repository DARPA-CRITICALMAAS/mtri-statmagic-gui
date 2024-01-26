from PyQt5.QtWidgets import QDialogButtonBox,  QLineEdit, QDialog, QVBoxLayout, QPushButton, QLabel, QCheckBox
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapLayerComboBox, QgsFileWidget, QgsExtentGroupBox


class ChooseExtent(QDialog):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        # super(AddRasterLayer, self).__init__(parent)
        super(ChooseExtent, self).__init__()

        # preserve a pointer to the dockwidget to access its attributes
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.selectedExtent = []

        self.drawButton = QPushButton(self)
        self.drawButton.setText('Draw On Canvas')
        self.drawButton.clicked.connect(self.draw_on_canvas)
        self.drawButton.setToolTip('Click points on the canvas to create a polygon to define bounds')

        self.selectfromLayerBox = QgsMapLayerComboBox(self)
        self.selectfromLayerBox.setToolTip('Uses the rectangular extent of layer to define bounds')

        label1 = QLabel('Use Selected Feature')
        self.useSelectedFeatureCheck = QCheckBox(self)
        self.useSelectedFeatureCheck.setToolTip('Will only consider the selected feature for determining extent')

        label2 = QLabel('Select From File')
        self.fileInput = QgsFileWidget(self)

        self.extentBox = QgsExtentGroupBox(self)

        self.DeterminedExtentText = QLineEdit(self)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)


        layout.addWidget(self.drawButton)
        layout.addWidget(self.selectfromLayerBox)
        layout.addWidget(label1)
        layout.addWidget(self.useSelectedFeatureCheck)
        layout.addWidget(label2)
        layout.addWidget(self.fileInput)
        layout.addWidget(self.extentBox)
        layout.addWidget(self.DeterminedExtentText)
        layout.addWidget(self.buttonBox)

        self.signals_connection()
        self.setLayout(layout)

    def signals_connection(self):
        self.buttonBox.accepted.connect(self.returnExtent)
        self.buttonBox.rejected.connect(self.cancel)

    def returnExtent(self):
        currentfile = self.selectfromLayerBox.currentLayer()
        # Todo: Think about what to transfer back to parent. A Geometry, gdf, list of coords, ??
        self.close()
    def draw_on_canvas(self):
        return

    def cancel(self):
        self.close()
