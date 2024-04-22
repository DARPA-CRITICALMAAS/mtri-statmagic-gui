from pathlib import Path

from statmagic_backend.geo_chem.link_black_shales_db import prep_black_shales
from statmagic_backend.dev.simple_CT_point_interpolation import interpolate_gdf_value

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QCheckBox, QPushButton, QLabel, QComboBox
from qgis.core import QgsVectorLayer, QgsProject, QgsRasterLayer, QgsMapLayerProxyModel

from .TabBase import TabBase
from ..gui_helpers import *

import logging
logger = logging.getLogger("statmagic_gui")


class GeochemistryTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Geochemistry")

        self.parent = parent
        self.iface = self.parent.iface

        ## Top Frame - Acquire Geochem Data
        topFrame, topLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        topFrameLabel = addLabel(topLayout, "Acquire Geochem Data")
        makeLabelBig(topFrameLabel)
        topFormLayout = QtWidgets.QFormLayout()

        pointSamples = ["Black Shale", "NGDB Rock"]

        label1 = QLabel('Data Source')
        self.geochem_data_selection_box = QComboBox()
        self.geochem_data_selection_box.addItems(pointSamples)

        label2 = QLabel('AOI')
        self.aoi_selection_box = QgsMapLayerComboBox()
        self.aoi_selection_box.setFilters(QgsMapLayerProxyModel.VectorLayer)

        self.run_geochem_acquire_btn = QPushButton()
        self.run_geochem_acquire_btn.setText('Acquire Data')
        self.run_geochem_acquire_btn.clicked.connect(self.acquire_geochem_data)

        topFormLayout.addRow(label1, self.geochem_data_selection_box)
        topFormLayout.addRow(label2, self.aoi_selection_box)
        topFormLayout.addWidget(self.run_geochem_acquire_btn)
        addWidgetFromLayoutAndAddToParent(topFormLayout, topFrame)
        addToParentLayout(topFrame)

        ## Middle Frame - Choose Elements of Interest
        midFrame, midLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        midFrameLabel = addLabel(midLayout, "Choose Elements of Interest")
        makeLabelBig(midFrameLabel)
        midFormLayout = QtWidgets.QFormLayout()

        label3 = QLabel('Data Source')
        self.geochem_data_selection_1_box = QComboBox()
        self.geochem_data_selection_1_box.addItems(pointSamples)

        label4 = QLabel('Elements')
        elements = ["Ag", "Al", "As", "Au", "B", "Ba", "Be", "Bi", "Ca", "Cd"]
        self.element_selection_box = QComboBox()
        self.element_selection_box.addItems(elements)

        self.run_select_elements_btn = QPushButton()
        self.run_select_elements_btn.setText('Select Elements')
        self.run_select_elements_btn.clicked.connect(self.select_elements)

        midFormLayout.addRow(label3, self.geochem_data_selection_1_box)
        midFormLayout.addRow(label4, self.element_selection_box)
        midFormLayout.addWidget(self.run_select_elements_btn)
        addWidgetFromLayoutAndAddToParent(midFormLayout, midFrame)
        addToParentLayout(midFrame)

        ## Bottom Frame - Interpolate Geochem Data
        botFrame, botLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        botFrameLabel = addLabel(botLayout, "Interpolate Geochem Data")
        makeLabelBig(botFrameLabel)
        botFormLayout = QtWidgets.QFormLayout()

        label5 = QLabel('Data Source')
        self.geochem_data_selection_2_box = QComboBox()
        self.geochem_data_selection_2_box.addItems(pointSamples)

        label6 = QLabel('Methods')
        methods = ["Clough Tocher", "Option 2"]
        self.interpolation_method_box = QComboBox()
        self.interpolation_method_box.addItems(methods)

        self.run_interpolation_btn = QPushButton()
        self.run_interpolation_btn.setText('Run Interpolation')
        self.run_interpolation_btn.clicked.connect(self.interpolate_geochem_points)

        botFormLayout.addRow(label5, self.geochem_data_selection_2_box)
        botFormLayout.addRow(label6, self.interpolation_method_box)
        botFormLayout.addWidget(self.run_interpolation_btn)
        addWidgetFromLayoutAndAddToParent(botFormLayout, botFrame)
        addToParentLayout(botFrame)



        # formLayout = QtWidgets.QFormLayout()
        #
        # pointSamples = ["Black Shale", "NGDB Rock"]
        # methods = ["Clough Tocher", "Option 2"]
        # elements = ["Ag", "Al", "As", "Au", "B", "Ba", "Be", "Bi", "Ca", "Cd"]
        #
        # self.geochem_data_selection_box = addComboBoxToForm(formLayout, "Point Sample Data", pointSamples)
        # self.interpolation_method_box = addComboBoxToForm(formLayout, "Method", methods)
        # self.element_selection_box = addComboBoxToForm(formLayout, "Element", elements)
        #
        # alignLayoutAndAddToParent(formLayout, self, "Left")
        #
        # self.do_interpolate_button = addButton(self, "Create Interpolated Layer", self.interpolate_geochem_points, align="Center")

    def acquire_geochem_data(self):
        return

    def select_elements(self):
        return

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
            logger.info('using black shales database')
            gdf, element_col = prep_black_shales(template_path, element_input)
        elif geochem_data_input == 1:
            logger.info("using NGDB rock")
        else:
            logger.error('no valid selection')

        output_file_path, message = interpolate_gdf_value(gdf, element_col, template_path)

        # Save out gdf
        gdf_out = Path(project_path) / 'black_shales.gpkg'
        gdf.to_file(gdf_out, driver='GPKG')
        logger.info(f'saved to {gdf_out}')
        vlayer = QgsVectorLayer(str(gdf_out), 'Black Shales Points', "ogr")
        QgsProject.instance().addMapLayer(vlayer)

        res = QgsRasterLayer(output_file_path, 'Interpolated_Layer')
        QgsProject.instance().addMapLayer(res)
