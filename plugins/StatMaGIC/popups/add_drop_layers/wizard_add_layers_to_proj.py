from PyQt5.QtWidgets import QDialogButtonBox, QComboBox, QLabel, QVBoxLayout, QDialog

from qgis.PyQt.QtCore import pyqtSignal





class AddLayerToProject(QDialog):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        # super(AddRasterLayer, self).__init__(parent)
        super(AddLayerToProject, self).__init__()

        # preserve a pointer to the dockwidget to access its attributes
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # self.comboBox = QComboBox(self)
        # self.comboBox.addItems(["Google Terrain", "Google Satellite", "OSM Standard"])
        # self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        label1 = QLabel("You need to have a layer loaded to capture an extent")
        # label2 = QLabel("You may choose to add a basemap from the options below (Internet Required) \n"
        #          "or press cancel and choose your own. THIS ISN'T HOOKED UP YET")


        layout.addWidget(label1)
        # layout.addWidget(label2)
        # layout.addWidget(self.comboBox)
        layout.addWidget(self.buttonBox)

        self.signals_connection()
        self.setLayout(layout)

    def signals_connection(self):
        self.buttonBox.accepted.connect(self.cancel)
        # self.buttonBox.accepted.connect(self.add_layer_to_project)
        # self.buttonBox.rejected.connect(self.cancel)

    def add_layer_to_project(self):
        # Todo: Put in hooks to basemaps and add to project
        self.close()

    def cancel(self):
        self.close()
