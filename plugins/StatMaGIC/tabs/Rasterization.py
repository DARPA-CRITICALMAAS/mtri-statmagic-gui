from PyQt5.QtWidgets import QCheckBox, QPushButton, QLabel, QSpinBox
from qgis.core import QgsProject, QgsFieldProxyModel, QgsMapLayerProxyModel, QgsRasterLayer
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox


from statmagic_backend.dev.rasterization_functions import qgs_features_to_gdf, vector_proximity_raster, rasterize_vector
from statmagic_backend.dev.rasterize_training_data import training_vector_rasterize

from .TabBase import TabBase
from ..gui_helpers import *

import logging
logger = logging.getLogger("statmagic_gui")

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
        label5.setToolTip("Will only consider selected features for analysis")
        self.with_selected_check_mid = QCheckBox()
        self.with_selected_check_mid.setToolTip("Will only consider selected features for analysis")

        self.run_rasterize_numField_button = QPushButton()
        self.run_rasterize_numField_button.setText('Rasterize Chosen Attribute')
        self.run_rasterize_numField_button.clicked.connect(self.rasterize_numeric_field)
        midFormLayout.addRow(label3, self.vector_layer_input)
        midFormLayout.addRow(label4, self.vector_field_input)
        midFormLayout.addRow(label5, self.with_selected_check_mid)
        midFormLayout.addWidget(self.run_rasterize_numField_button)
        addWidgetFromLayoutAndAddToParent(midFormLayout, midFrame)
        addToParentLayout(midFrame)

        # NEXT FRAME - Rasterize Training Points
        tpFrame, tpLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        tpFrameLabel = addLabel(tpLayout, "Rasterize Training Points")
        makeLabelBig(tpFrameLabel)
        tpGridLayout = QtWidgets.QGridLayout()

        label10 = QLabel('Select Point \n Data Layer:')
        label20 = QLabel('Value Field:')
        label30 = QLabel('Buffer Points')
        label40 = QLabel('With Selected Points')

        self.training_point_layer_box = QgsMapLayerComboBox()
        self.training_field_box = QgsFieldComboBox()
        self.training_buffer_box = QSpinBox()
        self.with_selected_training = QCheckBox()
        self.rasterize_training_button = QPushButton()

        self.training_point_layer_box.layerChanged.connect(self.training_field_box.setLayer)
        self.training_field_box.setFilters(QgsFieldProxyModel.Numeric)
        self.rasterize_training_button.clicked.connect(self.rasterize_training)
        self.rasterize_training_button.setText('Rasterize\n Training Points')

        self.training_buffer_box.setRange(0, 10000)
        self.training_buffer_box.setSingleStep(50)

        """
        So in lay.addWidget(widget, 2, 0, 1, 3) it means that "widget" 
        will be placed at position 2x0 and will occupy 1 row and 3 columns.
        """
        tpGridLayout.addWidget(label10, 0, 0)
        tpGridLayout.addWidget(self.training_point_layer_box, 0, 1)
        tpGridLayout.addWidget(label40, 0, 2)
        tpGridLayout.addWidget(self.with_selected_training, 0, 3)
        tpGridLayout.addWidget(label20, 1, 0)
        tpGridLayout.addWidget(self.training_field_box, 1, 1)
        tpGridLayout.addWidget(label30, 2, 0)
        tpGridLayout.addWidget(self.training_buffer_box, 2, 1)
        tpGridLayout.addWidget(label40, 3, 0)
        tpGridLayout.addWidget(self.rasterize_training_button, 1, 2, 2, 2)

        tpGridLayout.setColumnStretch(0, 0)
        tpGridLayout.setColumnStretch(1, 2)
        tpGridLayout.setColumnStretch(2, 1)
        tpGridLayout.setColumnStretch(3, 1)

        addWidgetFromLayoutAndAddToParent(tpGridLayout, tpFrame)
        addToParentLayout(tpFrame)



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

    def rasterize_training(self):
        selectedLayer = self.training_point_layer_box.currentLayer()
        withSelected = self.with_selected_training.isChecked()
        buffer = self.training_buffer_box.value()
        gdf = qgs_features_to_gdf(selectedLayer, selected=withSelected)
        gdf.to_crs(self.parent.meta_data['project_CRS'], inplace=True)

        message = training_vector_rasterize(gdf, self.parent.meta_data['template_path'],
                                            self.parent.meta_data['project_path'] + '/training_raster.tif', buffer)

        self.iface.messageBar().pushMessage(message)








