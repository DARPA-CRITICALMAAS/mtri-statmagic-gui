from PyQt5 import QtWidgets
from qgis.core import QgsRasterLayer, QgsProject, QgsFieldProxyModel, QgsCoordinateReferenceSystem

from statmagic_backend.dev.proximity_raster import qgs_features_to_gdf, vector_proximity_raster, rasterize_vector

from .TabBase import TabBase
from ..gui_helpers import *


class ProximityLayersTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Proximity Layers")

        self.parent = parent

        self.proximity_layer_box = addQgsMapLayerComboBox(self, "Features Layer", "HBox", align="Left")
        self.withSelectedCheckBox_prox = addCheckbox(self, "With Selected Features Only")
        self.create_proximity_layer_button = addButton(self, "Create Proximity Layer", self.distance_to_features_raster, align="Right")

        # TODO: figure out why this isn't working
        addEmptyFrame(self.tabLayout)

        formLayout = QtWidgets.QFormLayout(self)
        self.attribute_rasterize_field = addQgsFieldComboBoxToForm(formLayout, "Field for Raster Values:")
        self.rasterize_vector_button = addButtonToForm(formLayout, "Rasterize Vector", self.rasterize_vector)
        alignLayoutAndAddToParent(formLayout, self, "Left")

        addEmptyFrame(self.tabLayout)

        self.populate_comboboxes()

    def populate_comboboxes(self):
        rasterize_layer = self.proximity_layer_box.currentLayer()
        if rasterize_layer:
            self.attribute_rasterize_field.setLayer(rasterize_layer)
            self.proximity_layer_box.layerChanged.connect(self.attribute_rasterize_field.setLayer)
            self.attribute_rasterize_field.setFilters(QgsFieldProxyModel.Numeric)


    def distance_to_features_raster(self):
        selectedLayer = self.proximity_layer_box.currentLayer()
        withSelected = self.withSelectedCheckBox_prox.isChecked()

        # TODO Need to deal with the geometries outside of the template extent.
        #      May still want the distance from a feature even if it is outside the extent.
        #      Maybe do the raster creation large but then clip the output

        gdf = qgs_features_to_gdf(selectedLayer, selected=withSelected)

        gdf.to_crs(self.parent.meta_data['project_CRS'], inplace=True)

        output_file_path, message = vector_proximity_raster(gdf, self.meta_data['template_path'])

        res = QgsRasterLayer(output_file_path, 'Proximity_Layer')
        QgsProject.instance().addMapLayer(res)

        self.iface.messageBar().pushMessage(message)

    def rasterize_vector(self):
        selectedLayer = self.proximity_layer_box.currentLayer()
        withSelected = self.withSelectedcheckBox_prox.isChecked()
        field = self.attribute_rasterize_field.currentField()

        gdf = qgs_features_to_gdf(selectedLayer, selected=withSelected)

        gdf.to_crs(self.parent.meta_data['project_CRS'], inplace=True)

        output_file_path, message = rasterize_vector(gdf, self.parent.meta_data['template_path'], field)

        res = QgsRasterLayer(output_file_path, 'Rasterized Layer')
        QgsProject.instance().addMapLayer(res)

        self.iface.messageBar().pushMessage(message)
