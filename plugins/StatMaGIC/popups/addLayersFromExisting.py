import rasterio.enums
# Edited this Found at https://gis.stackexchange.com/questions/446174/filtering-qgscheckablecombobox-items-in-pyqgis
from qgis.PyQt.QtWidgets import QDialog, QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMenu, QAction
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QDialogButtonBox, QComboBox, QSpinBox
from statmagic_backend.dev.match_stack_raster_tools import add_selected_bands_from_source_raster_to_data_raster
from qgis.core import QgsRasterLayer, QgsProject



class RasterBandSelectionDialog(QDialog):

    def __init__(self, parent, raster_layer_path):
        self.parent = parent
        self.iface = parent.iface
        self.desc_list = None
        self.index_list = None
        self.raster_layer_path = raster_layer_path
        self.raster_layer = QgsRasterLayer(raster_layer_path)
        QDialog.__init__(self)
        self.setGeometry(500, 300, 500, 300)
        # Create an instance of the widget wrapper class
        self.list_widget = CustomCheckableListWidget(self)
        band_list = []
        for b in range(self.raster_layer.bandCount()):
            band_list.append(self.raster_layer.bandName(b+1))
        self.list_widget.set_items(band_list)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.list_widget)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.layout.addWidget(self.buttonBox)

        self.signals_connection()

    def return_bands(self):
        descs, idxs = self.list_widget.return_checked_items()
        self.desc_list = descs
        self.index_list = idxs
        self.close()

    def signals_connection(self):
        self.buttonBox.accepted.connect(self.return_bands)
        self.buttonBox.rejected.connect(self.cancel)

    def cancel(self):
        self.close()


class CustomCheckableListWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        QDialog.__init__(self)
        self.layout = QVBoxLayout(self)
        self.filter_le = QLineEdit(self)
        self.filter_le.setPlaceholderText('Type to filter...')
        self.items_le = QLineEdit(self)
        self.items_le.setReadOnly(True)
        self.lw = QListWidget(self)
        self.lw.setMinimumHeight(100)
        # self.samplingBox = QComboBox(self)
        # self.samplingBox.addItems(['nearest', 'bilinear', 'cubic'])
        # # Add the spinBox for num threads
        # self.num_threads_resamp_spinBox = QSpinBox()
        # self.num_threads_resamp_spinBox.setMaximum(32)
        # self.num_threads_resamp_spinBox.setMinimum(1)
        # self.num_threads_resamp_spinBox.setSingleStep(1)
        # self.num_threads_resamp_spinBox.setValue(1)
        # self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.layout.addWidget(self.filter_le)
        self.layout.addWidget(self.items_le)
        self.layout.addWidget(self.lw)
        # self.layout.addWidget(self.samplingBox)
        # self.layout.addWidget(self.num_threads_resamp_spinBox)
        # self.layout.addWidget(self.buttonBox)

        self.lw.viewport().installEventFilter(self)

        self.filter_le.textChanged.connect(self.filter_items)
        self.context_menu = QMenu(self)
        self.action_check_all = QAction('Select All', self)
        self.action_check_all.triggered.connect(self.select_all)
        self.action_uncheck_all = QAction('De-select All', self)
        self.action_uncheck_all.triggered.connect(self.deselect_all)
        self.context_menu.addAction(self.action_check_all)
        self.context_menu.addAction(self.action_uncheck_all)

        # self.signals_connection()

    def select_all(self):
        for i in range(self.lw.count()):
            item = self.lw.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.Checked)
        self.update_items()

    def deselect_all(self):
        for i in range(self.lw.count()):
            item = self.lw.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.Unchecked)
        self.update_items()

    def set_items(self, item_list):
        self.lw.clear()
        for i in item_list:
            lwi = QListWidgetItem(i)
            lwi.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            lwi.setCheckState(Qt.Unchecked)
            self.lw.addItem(lwi)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and obj == self.lw.viewport():
            if event.button() == Qt.LeftButton:
                clicked_item = self.lw.itemAt(event.pos())
                if clicked_item.checkState() == Qt.Checked:
                    clicked_item.setCheckState(Qt.Unchecked)
                else:
                    clicked_item.setCheckState(Qt.Checked)
                self.update_items()
            elif event.button() == Qt.RightButton:
                self.context_menu.exec(QCursor.pos())
            return True
        return False

    def filter_items(self, filter_txt):
        for i in range(self.lw.count()):
            item = self.lw.item(i)
            filter = filter_txt.lower() not in item.text().lower()
            self.lw.setRowHidden(i, filter)

    def update_items(self):
        self.items_le.clear()
        selection = []
        for i in range(self.lw.count()):
            item = self.lw.item(i)
            if item.checkState() == Qt.Checked:
                selection.append(item.text())
        selection.sort()
        self.items_le.setText(', '.join(selection))

    def return_checked_items(self):
        selection = []
        idxs = []
        for i in range(self.lw.count()):
            item = self.lw.item(i)
            if item.checkState() == Qt.Checked:
                selection.append(item.text())
                idxs.append(i)
        selection.sort()
        return selection, idxs

    # def run_add_layers(self):
    #     bandlist = self.return_checked_items()
    #     # Todo: Fix the bug in resampling. Hardcoded for demo
    #     method = rasterio.enums.Resampling.nearest
    #     # method = self.samplingBox.currentText()
    #     num_threads = self.num_threads_resamp_spinBox.value()
    #
    #     add_selected_bands_from_source_raster_to_data_raster(self.parent.parent.meta_data['data_raster_path'],
    #                                                          self.parent.raster_layer_path, bandlist, method,
    #                                                          num_threads)
    #
    #     QgsProject.instance().removeMapLayer(QgsProject.instance().mapLayersByName('DataCube')[0])
    #     # self.iface.mapCanvas().refreshAllLayers()
    #     data_raster = QgsRasterLayer(self.parent.parent.meta_data['data_raster_path'], 'DataCube')
    #     QgsProject.instance().addMapLayer(data_raster)
    #     self.cancel()
    #
    # def signals_connection(self):
    #     self.buttonBox.accepted.connect(self.run_add_layers)
    #     self.buttonBox.rejected.connect(self.cancel)

    def cancel(self):
        # Todo: this closes the CustomCheckableListWidget but should close the RasterBandSelectionDialog
        # Todo: Close the Dialog after run_drop_layers
        self.parent.close()
