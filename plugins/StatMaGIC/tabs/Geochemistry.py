from pathlib import Path

from statmagic_backend.geo_chem.link_black_shales_db import prep_black_shales
from statmagic_backend.dev.simple_CT_point_interpolation import interpolate_gdf_value

from PyQt5 import QtWidgets
from qgis.core import QgsVectorLayer, QgsProject, QgsRasterLayer

from .TabBase import TabBase
from ..gui_helpers import *


class GeochemistryTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Geochemistry")

        self.parent = parent

        formLayout = QtWidgets.QFormLayout()

        pointSamples = ["Black Shale", "NGDB Rock"]
        methods = ["Clough Tocher", "Option 2"]
        elements = ["Ag", "Al", "As", "Au", "B", "Ba", "Be", "Bi", "Ca", "Cd"]

        self.geochem_data_selection_box = addComboBoxToForm(formLayout, "Point Sample Data", pointSamples)
        self.interpolation_method_box = addComboBoxToForm(formLayout, "Method", methods)
        self.element_selection_box = addComboBoxToForm(formLayout, "Element", elements)

        alignLayoutAndAddToParent(formLayout, self, "Left")

        self.do_interpolate_button = addButton(self, "Create Interpolated Layer", self.interpolate_geochem_points, align="Center")

    def interpolate_geochem_points(self):
        try:
            template_path = self.parent.meta_data['template_path']
            project_path = self.parent.meta_data["project_path"]
        except KeyError:
            message = "Error: please create a template raster first."
            self.iface.messageBar().pushMessage(message)
            return

        geochem_data_input = self.geochem_data_selection_box.currentIndex()
        # Todo wire this method input in. Currently just does a default
        interpolation_method_input = self.interpolation_method_box.currentIndex()
        element_input = self.element_selection_box.currentText()

        if geochem_data_input == 0:
            print('using black shales database')
            gdf, element_col = prep_black_shales(template_path, element_input)
        elif geochem_data_input == 1:
            print("using NGDB rock")
        else:
            print('no valid selection')

        output_file_path, message = interpolate_gdf_value(gdf, element_col, template_path)

        # Save out gdf
        gdf_out = Path(project_path) / 'black_shales.gpkg'
        gdf.to_file(gdf_out, driver='GPKG')
        print(f'saved to {gdf_out}')
        vlayer = QgsVectorLayer(str(gdf_out), 'Black Shales Points', "ogr")
        QgsProject.instance().addMapLayer(vlayer)

        res = QgsRasterLayer(output_file_path, 'Interpolated_Layer')
        QgsProject.instance().addMapLayer(res)
