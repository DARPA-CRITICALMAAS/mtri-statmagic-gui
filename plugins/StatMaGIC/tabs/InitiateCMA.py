import json
import shutil
from datetime import date
from pathlib import Path

import geopandas as gpd
import rasterio as rio
from shapely.geometry import box

from statmagic_backend.dev.template_raster_user_input import print_memory_allocation_from_resolution_bounds, \
    create_template_raster_from_bounds_and_resolution

from PyQt5 import QtWidgets
from qgis.gui import QgsProjectionSelectionWidget, QgsExtentWidget
from qgis.core import QgsRasterLayer, QgsProject

from .TabBase import TabBase
from ..gui_helpers import *


class InitiateCMATab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Initiate CMA")
        self.parent = parent

        ##### TOP FRAME #####
        topFrame, topLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)

        topFrameLabel = addLabel(topLayout, "Input Metadata")
        makeLabelBig(topFrameLabel)

        topFormLayout = QtWidgets.QFormLayout()

        # we need objects that don't have a layout yet, so don't use the helpers
        self.UserNameLineEdit = QtWidgets.QLineEdit()
        self.CMA_mineralLineEdit = QtWidgets.QLineEdit()
        self.CommentsText = QtWidgets.QTextEdit()

        addFormItem(topFormLayout, "Username:", self.UserNameLineEdit)
        addFormItem(topFormLayout, "CMA Mineral:", self.CMA_mineralLineEdit)
        addFormItem(topFormLayout, "Comments:", self.CommentsText)

        addWidgetFromLayoutAndAddToParent(topFormLayout, topFrame)

        addToParentLayout(topFrame)

        ##### MIDDLE FRAME #####
        middleFrame, middleLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)

        middleFormLayout = QtWidgets.QFormLayout()

        self.proj_dir_input = QgsFileWidget()
        self.proj_dir_input.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
        self.template_input = QgsMapLayerComboBox()
        # self.template_input = QgsExtentGroupBox()
        # self.template_input = QgsExtentWidget()
        self.mQgsProjectionSelectionWidget = QgsProjectionSelectionWidget()

        addFormItem(middleFormLayout, "Select Project Directory:", self.proj_dir_input)
        addFormItem(middleFormLayout, "Select Project Bounds:", self.template_input)
        addFormItem(middleFormLayout, "Select Project CRS:", self.mQgsProjectionSelectionWidget)

        addWidgetFromLayoutAndAddToParent(middleFormLayout, middleFrame)

        # two labeled spin boxes in one row can't be added to a form layout
        # hence, we need a separate layout just for the spin boxes
        spinBoxWidget = QtWidgets.QWidget(middleFrame)
        spinBoxWidget.setLayout(QtWidgets.QHBoxLayout())

        self.pixel_size_input = addSpinBox(spinBoxWidget, "Pixel Size:", dtype=float, value=100, max=5000, step=50)
        self.buffer_dist_spinBox = addSpinBox(spinBoxWidget, "Buffer:", dtype=float, value=0, max=1000000, step=25)

        addToParentLayout(spinBoxWidget)
        addToParentLayout(middleFrame)

        ##### BIG BUTTONS #####
        buttonLayout = QtWidgets.QHBoxLayout()
        buttonWidget = addWidgetFromLayout(buttonLayout, self)
        self.make_template_raster_button = addButton(buttonWidget, "Create Project Files", self.initiate_CMA_workflow)
        self.check_size_button = addButton(buttonWidget, "Check Memory Size", self.print_estimated_size)

        addToParentLayout(buttonWidget)

        ##### BOTTOM FRAME #####
        bottomFrame, bottomLayout = addFrame(self, "HBox", "StyledPanel", "Raised", 3)

        addLabel(bottomLayout, "Resume Project \n"
                               "From JSON File:")

        self.resume_json_file_input = QgsFileWidget(bottomFrame)
        addToParentLayout(self.resume_json_file_input)

        self.resume_jsonProj_button = addButton(bottomFrame, "Set Project", self.set_project_json)

        addToParentLayout(bottomFrame)

    def initiate_CMA_workflow(self):
        # Retrieve metadata inputs
        username = self.UserNameLineEdit.text()
        cma_mineral = self.CMA_mineralLineEdit.text()
        comments = self.CommentsText.toPlainText()
        input_path = self.proj_dir_input.filePath()
        today = date.today().isoformat()

        proj_path = Path(input_path, 'CMA_' + cma_mineral)
        # Turned to true for dev. TODO this should be turned off once stable
        proj_path.mkdir(exist_ok=True)
        template_output_path = str(Path(proj_path, cma_mineral + '_template_raster.tif'))
        data_raster_path = str(Path(proj_path, cma_mineral + '_data_raster.tif'))

        # Retrieve template creation inputs
        selectedLayer = self.template_input.currentLayer()
        datastr = selectedLayer.source()
        pixel_size = self.pixel_size_input.value()
        buffer_distance = self.buffer_dist_spinBox.value()

        try:
            # This will be the case for geopackages, but not shapefile or geojson
            fp, layername = datastr.split('|')
            gdf = gpd.read_file(fp, layername=layername.split('=')[1])
        except ValueError:
            fp = datastr
            gdf = gpd.read_file(fp)

        # Todo: Use this to define the project CRS
        box_crs = self.mQgsProjectionSelectionWidget.crs()
        input_crsWkt = box_crs.toWkt()
        new_crs = rio.crs.CRS.from_wkt(input_crsWkt)
        bounds = gdf.to_crs(new_crs).total_bounds

        geom = box(*bounds)
        geom = geom.buffer(buffer_distance)
        bounds = gpd.GeoSeries(geom).total_bounds
        create_template_raster_from_bounds_and_resolution(bounds=bounds, target_crs=new_crs, pixel_size=pixel_size,
                                                          output_path=template_output_path)
        shutil.copy(template_output_path, data_raster_path)

        meta_dict = {'username': username, 'mineral': cma_mineral, 'comments': comments, 'date_initiated': today,
                     'project_path': str(proj_path), 'project_CRS': str(new_crs), 'project_bounds': str(bounds),
                     'template_path': template_output_path, 'data_raster_path': data_raster_path}

        with open(Path(proj_path, 'project_metadata.json'), 'w') as f:
            json.dump(meta_dict, f)

        self.parent.meta_data = meta_dict

        message = f"Project files saved to: {proj_path}"
        qgs_data_raster = QgsRasterLayer(self.parent.meta_data['data_raster_path'], 'DataCube')
        QgsProject.instance().addMapLayer(qgs_data_raster)
        QgsProject.setCrs(box_crs)
        self.iface.messageBar().pushMessage(message)

    def print_estimated_size(self):
        selectedLayer = self.template_input.currentLayer()
        # TODO Deterimine if it's a raster or vector. Repeat for make template as well
        # TODO have the abiity to get the draw rectangle function
        datastr = selectedLayer.source()
        pixel_size = self.pixel_size_input.value()
        buffer_distance = self.buffer_dist_spinBox.value()

        try:
            # This will be the case for geopackages, but not shapefile or geojson
            fp, layername = datastr.split('|')
        except ValueError:
            fp = datastr

        # There may need to be some crs projection stuff here, but wouldn't change the memory much I imagine
        box_crs = self.mQgsProjectionSelectionWidget.crs()
        input_crsWkt = box_crs.toWkt()
        new_crs = rio.crs.CRS.from_wkt(input_crsWkt)

        bounds = gpd.read_file(fp).to_crs(new_crs).total_bounds

        geom = box(*bounds)
        geom = geom.buffer(buffer_distance)
        bounds = gpd.GeoSeries(geom).total_bounds

        memstring = print_memory_allocation_from_resolution_bounds(bounds, pixel_size)
        self.iface.messageBar().pushMessage(memstring)

    def set_project_json(self):
        proj_path = self.resume_json_file_input.filePath()
        with open(Path(proj_path), 'r') as f:
            self.parent.meta_data = json.loads(f.read())
        message = f"Project files loaded from: {proj_path}"
        qgs_data_raster = QgsRasterLayer(self.parent.meta_data['data_raster_path'], 'DataCube')
        QgsProject.instance().addMapLayer(qgs_data_raster)
        self.iface.messageBar().pushMessage(message)