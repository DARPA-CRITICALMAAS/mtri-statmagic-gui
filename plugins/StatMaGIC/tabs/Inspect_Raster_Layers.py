from PyQt5 import QtWidgets
from qgis.gui import QgsRasterBandComboBox, QgsRasterHistogramWidget
from qgis.core import QgsMapLayerProxyModel


from .TabBase import TabBase
from ..gui_helpers import *
from ..popups.dropRasterLayer import RasterBandSelectionDialog


class InspectLayersTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Inspect DataCube Layers")

        self.parent = parent
        self.iface = self.parent.iface

        ##### TOP FRAME - Insepetion options#####
        topFrame, topLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        topFormLayout = QtWidgets.QFormLayout()

        # Needs to set a raster box. Will need to think about having a copy of the datacube.tif
        # So that one can be edited and one can be loaded in the QGIS TOC
        self.comboBox = QgsMapLayerComboBox(self)
        self.comboBox.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.rasterBandBox = QgsRasterBandComboBox(self)

        addFormItem(topFormLayout, "Raster / DataCube:", self.comboBox)
        addFormItem(topFormLayout, "Choose Band: ", self.rasterBandBox)
        # self.rasterProps = QgsRasterLayerProperties(self)
        # self.rasterHist = QgsRasterHistogramWidget(self)

        addWidgetFromLayoutAndAddToParent(topFormLayout, topFrame)
        addToParentLayout(topFrame)

        ##### MIDDLE FRAME #####
        # middleFrame, middleLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        # middleFormLayout = QtWidgets.QFormLayout()
        # self.drop_layers_button = addButton(middleFormLayout, "Drop Layers", self.popup_drop_layer_dialogue)
        # addToParentLayout(middleFormLayout)

        self.drop_layers_button = addButton(self, "Drop Layers Menu", self.popup_drop_layer_dialogue)

        self.populate_comboboxes()


    def populate_comboboxes(self):
        raster_layer = self.comboBox.currentLayer()
        if raster_layer:
            self.rasterBandBox.setLayer(raster_layer)
            self.comboBox.layerChanged.connect(self.rasterBandBox.setLayer)



    def popup_drop_layer_dialogue(self):
        popup = RasterBandSelectionDialog(self, raster_layer=self.comboBox.currentLayer())
        popup.exec_()
