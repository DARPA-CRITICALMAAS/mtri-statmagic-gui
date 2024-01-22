
# Found at https://gis.stackexchange.com/questions/446174/filtering-qgscheckablecombobox-items-in-pyqgis
from qgis.PyQt.QtWidgets import QDialog, QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMenu, QAction
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QDialogButtonBox
from statmagic_backend.dev.match_stack_raster_tools import drop_selected_layers_from_raster

class RasterBandSelectionDialog(QDialog):

    def __init__(self, parent, raster_layer):
        self.iface = parent.iface
        self.raster_layer = raster_layer
        QDialog.__init__(self)
        self.setGeometry(500, 300, 500, 300)
        # Create an instance of the widget wrapper class
        self.list_widget = CustomCheckableListWidget(parent)
        band_list = []
        for b in range(self.raster_layer.bandCount()):
            band_list.append(self.raster_layer.bandName(b))
        self.list_widget.set_items(band_list)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.list_widget)


class CustomCheckableListWidget(QWidget):
    '''
    Copy and paste this class into your PyQGIS project/ plugin
    '''

    def __init__(self, parent=None):
        self.parent = parent
        QDialog.__init__(self)
        self.layout = QVBoxLayout(self)
        self.filter_le = QLineEdit(self)
        self.filter_le.setPlaceholderText('Type to filter...')
        self.items_le = QLineEdit(self)
        self.items_le.setReadOnly(True)
        self.lw = QListWidget(self)
        self.lw.setMinimumHeight(100)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.layout.addWidget(self.filter_le)
        self.layout.addWidget(self.items_le)
        self.layout.addWidget(self.lw)
        self.layout.addWidget(self.buttonBox)

        self.lw.viewport().installEventFilter(self)

        self.filter_le.textChanged.connect(self.filter_items)
        self.context_menu = QMenu(self)
        self.action_check_all = QAction('Select All', self)
        self.action_check_all.triggered.connect(self.select_all)
        self.action_uncheck_all = QAction('De-select All', self)
        self.action_uncheck_all.triggered.connect(self.deselect_all)
        self.context_menu.addAction(self.action_check_all)
        self.context_menu.addAction(self.action_uncheck_all)

        self.signals_connection()

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

    def run_drop_layers(self):
        # Todo Return just the band indices for dropping
        bandlist = self.return_checked_items()
        drop_selected_layers_from_raster(self.parent.parent.metadata['data_raster_path'], bandlist)

    def signals_connection(self):
        self.buttonBox.accepted.connect(self.run_drop_layers)
        self.buttonBox.rejected.connect(self.cancel)

    def cancel(self):
        print('canceled')
        self.close()
#
# dlg = TestDialog(iface)
# dlg.show()