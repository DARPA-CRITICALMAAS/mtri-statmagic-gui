from qgis.PyQt.QtWidgets import QDialog, QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMenu, QAction
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QDialogButtonBox
from statmagic_backend.dev.match_stack_raster_tools import drop_selected_layers_from_raster
from qgis.core import QgsRasterLayer, QgsProject


class SimpleQtPlot(QDialog):

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        QDialog.__init__(self)
        self.setGeometry(500, 300, 500, 300)
        # Create an instance of the widget wrapper class
        # self.list_widget = CustomCheckableListWidget(self)
        # band_list = []
        # for b in range(self.raster_layer.bandCount()):
        #     band_list.append(self.raster_layer.bandName(b+1))
        # self.list_widget.set_items(band_list)
        self.layout = QVBoxLayout(self)
        #self.layout.addWidget(self.list_widget)
