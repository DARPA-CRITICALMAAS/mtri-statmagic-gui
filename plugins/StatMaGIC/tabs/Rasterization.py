from PyQt5.QtWidgets import QCheckBox, QPushButton, QLabel
from qgis.core import QgsProject, QgsFieldProxyModel, QgsMapLayerProxyModel, QgsRasterLayer
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox

from statmagic_backend.dev.proximity_raster import qgs_features_to_gdf, vector_proximity_raster, rasterize_vector

from .TabBase import TabBase
from ..gui_helpers import *

class RasterizationTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Rasterization Tools")

        self.parent = parent
        self.iface = self.parent.iface

        #### TOP FRAME - Proximity Tools
        topFrame, topLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        topFrameLabel = addLabel(topLayout, "Derive Proximity Layers")
        makeLabelBig(topFrameLabel)
        topFormLayout = QtWidgets.QFormLayout()

        label1 = QLabel('Distance Feature Layer:')
        self.proximity_layer_box = QgsMapLayerComboBox()
        self.proximity_layer_box.setFilters(QgsMapLayerProxyModel.VectorLayer)
        label2 = QLabel('Use Selected Features:')
        self.with_selected_check_top = QCheckBox()

        self.run_proximity_button = QPushButton()
        self.run_proximity_button.setText('Create Proximity Raster')
        self.run_proximity_button.clicked.connect(self.distance_to_features_raster)

        topFormLayout.addRow(label1, self.proximity_layer_box)
        topFormLayout.addRow(label2, self.with_selected_check_top)
        topFormLayout.addWidget(self.run_proximity_button)
        addWidgetFromLayoutAndAddToParent(topFormLayout, topFrame)
        addToParentLayout(topFrame)
        
        ### MIDDLE FRAME - Rasterize Numerics #####
        midFrame, midLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        midFrameLabel = addLabel(midLayout, "Rasterize Numeric Vector Attributes")
        makeLabelBig(midFrameLabel)
        midFormLayout = QtWidgets.QFormLayout()

        label3 = QLabel('Vector Layer to Rasterize:')
        self.vector_layer_input = QgsMapLayerComboBox()
        self.vector_layer_input.setFilters(QgsMapLayerProxyModel.VectorLayer)
        label4 = QLabel("Field to Rasterize:")
        self.vector_field_input = QgsFieldComboBox()
        self.vector_layer_input.layerChanged.connect(self.vector_field_input.setLayer)
        # self.vector_field_input.setLayer(self.vector_layer_input.currentLayer())
        self.vector_field_input.setFilters(QgsFieldProxyModel.Numeric)
        label5 = QLabel("Use Selected Features:")
        self.with_selected_check_mid = QCheckBox()

        self.run_rasterize_numField_button = QPushButton()
        self.run_rasterize_numField_button.setText('Create Proximity Raster')
        self.run_rasterize_numField_button.clicked.connect(self.rasterize_numeric_field)
        midFormLayout.addRow(label3, self.vector_layer_input)
        midFormLayout.addRow(label4, self.vector_field_input)
        midFormLayout.addRow(label5, self.with_selected_check_mid)
        midFormLayout.addWidget(self.run_rasterize_numField_button)
        addWidgetFromLayoutAndAddToParent(midFormLayout, midFrame)
        addToParentLayout(midFrame)



    def distance_to_features_raster(self):
        selectedLayer = self.proximity_layer_box.currentLayer()
        withSelected = self.with_selected_check_top.isChecked()

        gdf = qgs_features_to_gdf(selectedLayer, selected=withSelected)
        gdf.to_crs(self.parent.meta_data['project_CRS'], inplace=True)

        output_file_path, message = vector_proximity_raster(gdf, self.parent.meta_data['template_path'])

        res = QgsRasterLayer(output_file_path, 'Proximity_Layer')
        # Todo: Make this be added to the top of the TOC
        QgsProject.instance().addMapLayer(res)
        self.iface.messageBar().pushMessage(message)

    def rasterize_numeric_field(self):
        selectedLayer = self.vector_layer_input.currentLayer()
        withSelected = self.with_selected_check_mid.isChecked()
        field = self.vector_field_input.currentField()
        gdf = qgs_features_to_gdf(selectedLayer, selected=withSelected)
        gdf.to_crs(self.parent.meta_data['project_CRS'], inplace=True)
        output_file_path, message = rasterize_vector(gdf, self.parent.meta_data['template_path'], field)

        res = QgsRasterLayer(output_file_path, f'Rasterized {field} Layer')
        QgsProject.instance().addMapLayer(res)

        self.iface.messageBar().pushMessage(message)








