import rasterio.enums
from qgis.PyQt.QtWidgets import QDialog, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QDialogButtonBox, QComboBox, QSpinBox, QCheckBox
from statmagic_backend.dev.match_stack_raster_tools import *
from qgis.core import QgsRasterLayer, QgsProject
from ..constants import nationdata_raster_dict, resampling_dict

import logging
logger = logging.getLogger("statmagic_gui")

class raster_process_menu(QDialog):

    def __init__(self, parent, raster_layer):
        self.parent = parent
        self.iface = parent.iface
        self.raster_layer = raster_layer
        QDialog.__init__(self)
        self.setGeometry(500, 300, 500, 300)
        QDialog.setWindowTitle(self, "Raster Layer Options")
        # Create an instance of the widget wrapper class
        self.table_widget = table_combo_widget(self)
        num_rows = self.raster_layer.bandCount()
        num_cols = 4
        band_list = []
        for b in range(num_rows):
            band_list.append(self.raster_layer.bandName(b + 1))

        self.table_widget.set_items(band_list, num_rows, num_cols)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.table_widget)


class table_combo_widget(QWidget):

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        QDialog.__init__(self)
        self.layout = QVBoxLayout(self)
        self.tableWidget = QTableWidget()
        # self.tableWidget.setGeometry(QtCore.QRect(220, 100, 411, 392))
        self.layout.addWidget(self.tableWidget)

        # self.tableWidget.show()


    def set_items(self, band_name_list, n_row, n_col):

        # https://stackoverflow.com/questions/39720036/pyqt5-qcombobox-in-qtablewidget
        # See above for how to populate the table
        # also look at gidlac code for setting and accessing values
        self.tableWidget.clear()
        self.tableWidget.setColumnCount(n_col)
        self.tableWidget.setRowCount(n_row)
        # self.tableWidget.setColumnWidth(0, 250)
        # self.tableWidget.setColumnWidth(1, 75)
        # self.tableWidget.setColumnWidth(2, 150)
        # self.tableWidget.setColumnWidth(3, 200)
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)




        self.tableWidget.setHorizontalHeaderLabels(['Band Name', 'Path', 'Resampling', 'Normalization'])

        for i in range(n_row):
            self.tableWidget.setItem(i, 0, QTableWidgetItem(band_name_list[i]))
            rs_cb = QComboBox()
            rs_cb.addItems(['nearest', 'bilinear', 'cubic', 'cubic_spline', 'lanczos', 'average', 'mode', 'gauss'])
            self.tableWidget.setCellWidget(i, 2, rs_cb)
            # tr_cb = QComboBox()
            # tr_cb.addItems(['standard-scaler', 'logarithmic', 'linear', 'sigmoid', 'clip', 'winsorize', 'binarize'])
            # self.tableWidget.setCellWidget(i, 3, tr_cb)
