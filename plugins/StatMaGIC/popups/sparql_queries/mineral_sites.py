from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QPushButton, QLabel, QLineEdit, QMessageBox, QTextEdit, QComboBox, QTableView, QCheckBox, QVBoxLayout, QHBoxLayout, QFrame, QFormLayout, QSpacerItem, QGridLayout
from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5.QtGui import QPalette, QColor, QIntValidator

from qgis.core import QgsVectorLayer, QgsProject, QgsRasterLayer, QgsMapLayerProxyModel, QgsPoint, QgsCoordinateTransform
from qgis.gui import QgsMapLayerComboBox
from statmagic_backend.sparql import sparql_utils

import logging
logger = logging.getLogger("statmagic_gui")


class MineralSitesQueryBuilder(QDialog):

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        super(MineralSitesQueryBuilder, self).__init__(parent)
        QDialog.setWindowTitle(self, "Mineral Sites Query Builder")

        self.ore_label = QLabel("Commodity")
        self.ore_selection = QComboBox()
        try:
            self.ore_selection.addItems(sparql_utils.get_commodity_list())
        except:
            self.ore_selection.addItems(sparql_utils.get_default_commodity_list())

        self.aoi_label = QLabel("AOI")
        self.aoi_selection_box = QgsMapLayerComboBox(self)
        self.aoi_selection_box.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.aoi_selection_box.setShowCrs(True)
        self.aoi_selection_box.setFixedWidth(300)
        self.aoi_selection_box.setAllowEmptyLayer(True)
        self.aoi_selection_box.setCurrentIndex(0)

        self.submit_btn = QPushButton("Construct Query")
        self.submit_btn.clicked.connect(self.submitclose)

        self.query = None
        self.aoi_layer = None

        # Populate dialog layout
        self.layout = QGridLayout(self)
        self.layout.addWidget(self.ore_label, 0, 0)
        self.layout.addWidget(self.ore_selection, 0, 1)
        self.layout.addWidget(self.aoi_label, 1, 0)
        self.layout.addWidget(self.aoi_selection_box, 1, 1)
        self.layout.addWidget(self.submit_btn, 2, 0)
        self.setLayout(self.layout)

    def submitclose(self):
        self.query = sparql_utils.get_mineral_sites(str(self.ore_selection.currentText()))
        self.aoi_layer = self.aoi_selection_box.currentLayer()
        print(self.aoi_layer)
        print(self.query)

        self.accept()


