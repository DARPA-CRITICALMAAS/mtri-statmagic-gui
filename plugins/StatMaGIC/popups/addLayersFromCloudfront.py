import rasterio.enums
# Edited this Found at https://gis.stackexchange.com/questions/446174/filtering-qgscheckablecombobox-items-in-pyqgis
from qgis.PyQt.QtWidgets import QDialog, QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMenu, QAction
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QDialogButtonBox, QComboBox, QSpinBox, QCheckBox
from statmagic_backend.dev.match_stack_raster_tools import *
from qgis.core import QgsRasterLayer, QgsProject
from ..constants import nationdata_raster_dict, resampling_dict




class CloudFrontSelectionDialog(QDialog):

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        self.band_list = None
        self.cog_paths = None
        QDialog.__init__(self)
        self.setGeometry(500, 300, 500, 300)
        # Create an instance of the widget wrapper class
        self.list_widget = CustomCheckableListWidget(self)
        self.list_widget.set_items(list(nationdata_raster_dict.keys()))
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.list_widget)
        ## Testing
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.layout.addWidget(self.buttonBox)

        self.signals_connection()

    def return_bands(self):
        self.band_list = self.list_widget.return_checked_items()
        self.cog_paths = [nationdata_raster_dict[key] for key in self.band_list]
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
        self.samplingBox = QComboBox(self)
        self.samplingBox.addItems(['nearest', 'bilinear', 'cubic'])
        # Add the spinBox for num threads
        self.num_threads_resamp_spinBox = QSpinBox()
        self.num_threads_resamp_spinBox.setMaximum(32)
        self.num_threads_resamp_spinBox.setMinimum(1)
        self.num_threads_resamp_spinBox.setSingleStep(1)
        self.num_threads_resamp_spinBox.setValue(1)
        self.rioXcheck = QCheckBox('Use rioxarray', self)
        # self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.layout.addWidget(self.filter_le)
        self.layout.addWidget(self.items_le)
        self.layout.addWidget(self.lw)
        self.layout.addWidget(self.samplingBox)
        self.layout.addWidget(self.num_threads_resamp_spinBox)
        self.layout.addWidget(self.rioXcheck)
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
        for i in range(self.lw.count()):
            item = self.lw.item(i)
            if item.checkState() == Qt.Checked:
                selection.append(item.text())
        selection.sort()
        return selection

    # def run_add_layers(self):
    #     bandlist = self.return_checked_items()
    #     method = self.samplingBox.currentText()
    #     num_threads = self.num_threads_resamp_spinBox.value()
    #     use_rioX = self.rioXcheck.isChecked()
    #
    #     # Right now this is just doing the same resampling for all
    #     # Todo: Create a flow where the user can select which bands to resample with which method
    #     rs_list = [resampling_dict.get(method) for i in range(len(bandlist))]
    #     cog_paths = [nationdata_raster_dict[key] for key in bandlist]
    #
    #
    #     import time
    #     t = time.time()
    #
    #     if use_rioX:
    #         # Using rioxarray functions
    #         resampled_arrays = match_cogList_to_template_andStack(self.parent.parent.meta_data['template_path'],
    #                                                               cog_paths, rs_list)
    #     else:
    #         # With rasterio and previously defined methods
    #         resampled_arrays = match_and_stack_rasters(self.parent.parent.meta_data['template_path'], cog_paths, rs_list, num_threads)
    #
    #     add_matched_arrays_to_data_raster(self.parent.parent.meta_data['data_raster_path'], resampled_arrays, bandlist)
    #
    #     # capture elapsed time
    #     elapsed = time.time() - t
    #     message = "Layers appended to the raster data stack in {} seconds".format(elapsed)
    #     print(message)
    #
    #     QgsProject.instance().removeMapLayer(QgsProject.instance().mapLayersByName('DataCube')[0])
    #     # self.iface.mapCanvas().refreshAllLayers()
    #     data_raster = QgsRasterLayer(self.parent.parent.meta_data['data_raster_path'], 'DataCube')
    #     QgsProject.instance().addMapLayer(data_raster)
    #     self.cancel()

    # def signals_connection(self):
    #     self.buttonBox.accepted.connect(self.run_add_layers)
    #     self.buttonBox.rejected.connect(self.cancel)

    def cancel(self):
        # Todo: this closes the CustomCheckableListWidget but should close the RasterBandSelectionDialog
        # Todo: Close the Dialog after run_drop_layers
        self.parent.close()
