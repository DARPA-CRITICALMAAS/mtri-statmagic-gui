from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QPushButton, QLabel, QLineEdit, QMessageBox, QTextEdit, QComboBox, QTableView, QCheckBox, QVBoxLayout, QHBoxLayout, QFrame, QFormLayout, QSpacerItem, QGridLayout
from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5.QtGui import QPalette, QColor, QIntValidator

from qgis.core import QgsVectorLayer, QgsProject, QgsRasterLayer, QgsMapLayerProxyModel, QgsPoint, QgsCoordinateTransform
from statmagic_backend.sparql import sparql_utils

import logging
logger = logging.getLogger("statmagic_gui")


class OreGradeCutoffQueryBuilder(QDialog):

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        super(OreGradeCutoffQueryBuilder, self).__init__(parent)
        QDialog.setWindowTitle(self, "Ore / Grade / Cutoff Query Builder")

        self.ore_label = QLabel("Ore")
        self.ore_selection = QComboBox()
        try:
            self.ore_selection.addItems(sparql_utils.get_commodity_list())
        except:
            self.ore_selection.addItems(sparql_utils.get_default_commodity_list())

        self.filter_grade_label = QLabel("Grade Filter Cutoff")
        self.filter_grade_input = QLineEdit()
        validator = QIntValidator()
        validator.setRange(0, 50)
        self.filter_grade_input.setValidator(validator)

        self.submit_btn = QPushButton("Construct Query")
        self.submit_btn.clicked.connect(self.submitclose)

        self.query = ""

        # Populate dialog layout
        self.layout = QGridLayout(self)
        self.layout.addWidget(self.ore_label, 0, 0)
        self.layout.addWidget(self.ore_selection, 0, 1)
        self.layout.addWidget(self.filter_grade_label, 1, 0)
        self.layout.addWidget(self.filter_grade_input, 1, 1)
        self.layout.addWidget(self.submit_btn, 2, 0)
        self.setLayout(self.layout)

    def submitclose(self):
        self.query =    f'SELECT ?o_inv ?comm_name ?ore ?grade ?cutoff_grade ?cat\n' + \
                        f'WHERE \u007b\n' + \
                        f'?s :mineral_inventory ?o_inv .\n' + \
                        f'?o_inv :category ?cat .\n' + \
                        f'?o_inv :commodity [ :name "{self.ore_selection.currentText()}"@en ] .\n' + \
                        f'?o_inv :ore [ :ore_value ?ore ] .\n' + \
                        f'?o_inv :grade [ :grade_value ?grade ] .\n' + \
                        f'?o_inv :cutoff_grade [ :grade_value ?cutoff_grade ] .\n' + \
                        f'FILTER (?grade >= {self.filter_grade_input.text()})\n' + \
                        f'\u007d'

        self.accept()


