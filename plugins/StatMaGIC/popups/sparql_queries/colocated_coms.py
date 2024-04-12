from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QPushButton, QLabel, QLineEdit, QMessageBox, QTextEdit, QComboBox, QTableView, QCheckBox, QVBoxLayout, QHBoxLayout, QFrame, QFormLayout, QSpacerItem, QGridLayout
from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5.QtGui import QPalette, QColor, QIntValidator

from qgis.core import QgsVectorLayer, QgsProject, QgsRasterLayer, QgsMapLayerProxyModel, QgsPoint, QgsCoordinateTransform
from statmagic_backend.sparql import sparql_utils

import logging
logger = logging.getLogger("statmagic_gui")


class ColocatedCommoditiesQueryBuilder(QDialog):

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        super(ColocatedCommoditiesQueryBuilder, self).__init__(parent)
        QDialog.setWindowTitle(self, "Colocated Commodities Query Builder")

        self.ore_label = QLabel("Primary Commodity")
        self.ore_selection = QComboBox()
        try:
            self.ore_selection.addItems(sparql_utils.get_commodity_list())
        except:
            self.ore_selection.addItems(sparql_utils.get_default_commodity_list())

        self.submit_btn = QPushButton("Construct Query")
        self.submit_btn.clicked.connect(self.submitclose)

        self.query = ""

        # Populate dialog layout
        self.layout = QGridLayout(self)
        self.layout.addWidget(self.ore_label, 0, 0)
        self.layout.addWidget(self.ore_selection, 0, 1)
        self.layout.addWidget(self.submit_btn, 2, 0)
        self.setLayout(self.layout)

    def submitclose(self):
        self.query = sparql_utils.get_query_colocated_commodities(str(self.ore_selection.currentText()))
        print(self.query)

        self.accept()


