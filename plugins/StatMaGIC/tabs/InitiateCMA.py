import json
import shutil
from datetime import date
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from statmagic_backend.dev.template_raster_user_input import print_memory_allocation_from_resolution_bounds, \
    create_template_raster_from_bounds_and_resolution

from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer, QFileInfo
from qgis.gui import QgsProjectionSelectionWidget, QgsExtentWidget
from qgis.core import QgsRasterLayer, QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsCoordinateTransformContext


from .TabBase import TabBase
from ..gui_helpers import *
from ..layerops import set_project_crs
from ..popups.ChooseProjExtentDialog import ChooseExtent


class InitiateCMATab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Initiate CMA")
        self.parent = parent
        self.iface = self.parent.iface

        # geodataframe to hold the project bounds
        # at project initialization, no extent is defined
        # after initialization, this data is loaded from the project json
        self.extent_gdf = None

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
        self.proj_dir_input.fileChanged.connect(self.updateInitiationCheckList)
        self.template_input = QgsMapLayerComboBox()
        self.mQgsProjectionSelectionWidget = QgsProjectionSelectionWidget()
        self.mQgsProjectionSelectionWidget.setCrs(QgsCoordinateReferenceSystem('ESRI:102008'))
        self.mQgsProjectionSelectionWidget.crsChanged.connect(self.crsChanged)

        self.chooseExtentOptions = QtWidgets.QPushButton()
        self.chooseExtentOptions.setText('Open Extent Selection Menu')
        self.chooseExtentOptions.clicked.connect(self.chooseExtentDialog)
        self.chooseExtentOptions.setToolTip('Opens Menu with options for selected an extent')

        addFormItem(middleFormLayout, "Select Project Directory:", self.proj_dir_input)
        addFormItem(middleFormLayout, "Choose Project CRS:", self.mQgsProjectionSelectionWidget)
        addFormItem(middleFormLayout, "Define Project Bounds", self.chooseExtentOptions)
        addWidgetFromLayoutAndAddToParent(middleFormLayout, middleFrame)

        # two labeled spin boxes in one row can't be added to a form layout
        # hence, we need a separate layout just for the spin boxes
        spinBoxWidget = QtWidgets.QWidget(middleFrame)
        spinBoxWidget.setLayout(QtWidgets.QHBoxLayout())

        self.pixel_size_input = addSpinBox(spinBoxWidget, "Pixel Size:", dtype=float, value=100, max=5000, step=50)
        self.buffer_dist_spinBox = addSpinBox(spinBoxWidget, "Buffer:", dtype=float, value=0, max=1000000, step=25)

        addToParentLayout(spinBoxWidget)
        addToParentLayout(middleFrame)

        #### CheckList Labels

        checkFrame, checkLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        checkFrameLabel = addLabel(checkLayout, "Initiation Checklist")
        makeLabelBig(checkFrameLabel)


        # Todo: how to change the text after directory selected, CRS changed, Bounds returned from popup
        self.dirSelectedLabel = QtWidgets.QLabel('Project Not Selected')
        self.crsSelectedLabel = QtWidgets.QLabel('Crs set to default')
        self.boundsSelectedLabel = QtWidgets.QLabel('Bounds not defined')

        self.dirSelectedLabel.setStyleSheet('background-color: red')
        self.crsSelectedLabel.setStyleSheet('background-color: red')
        self.boundsSelectedLabel.setStyleSheet('background-color: red')

        checkLayout.addWidget(self.dirSelectedLabel)
        checkLayout.addWidget(self.crsSelectedLabel)
        checkLayout.addWidget(self.boundsSelectedLabel)

        # addWidgetFromLayoutAndAddToParent(checkListLayout, checkFrame)
        addToParentLayout(checkFrame)

        ##### BIG BUTTONS #####
        buttonLayout = QtWidgets.QHBoxLayout()
        buttonWidget = addWidgetFromLayout(buttonLayout, self)
        self.make_template_raster_button = addButton(buttonWidget, "Create Project Files", self.initiate_CMA_workflow)
        self.check_size_button = addButton(buttonWidget, "Check Memory Size", self.print_estimated_size)
        self.make_template_raster_button.setEnabled(False)
        self.check_size_button.setEnabled(False)

        addToParentLayout(buttonWidget)

        ##### BOTTOM FRAME #####
        bottomFrame, bottomLayout = addFrame(self, "HBox", "StyledPanel", "Raised", 3)

        addLabel(bottomLayout, "Resume Project \n"
                               "From JSON File:")

        self.resume_json_file_input = QgsFileWidget(bottomFrame)
        addToParentLayout(self.resume_json_file_input)

        self.resume_jsonProj_button = addButton(bottomFrame, "Set Project", self.set_project_json)

        addToParentLayout(bottomFrame)

        self.updateInitiationCheckList()

    def crsChanged(self):
        crs = self.mQgsProjectionSelectionWidget.crs()
        if crs.isGeographic():
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Warning: You have selected a geographic coordinate system. Consider choosing a projected coordinate system for better performance.")
            msgBox.exec()
        self.updateInitiationCheckList()

    def updateInitiationCheckList(self):
        project_dir_selected = False
        crs_selected = False
        bounds_selected = False

        project_dir = Path(self.proj_dir_input.filePath())
        project_crs = self.mQgsProjectionSelectionWidget.crs()
        project_bounds = self.extent_gdf

        if project_dir.exists() and not project_dir == Path('.'):
            project_dir_selected = True
            self.dirSelectedLabel.setText('Project Directory Selected')
            self.dirSelectedLabel.setStyleSheet('background-color: lightgreen')
        else:
            self.dirSelectedLabel.setText('Project Not Selected')
            self.dirSelectedLabel.setStyleSheet('background-color: red')

        if project_crs.isValid():
            crs_selected = True
            self.crsSelectedLabel.setText('CRS Set')
            self.crsSelectedLabel.setStyleSheet('background-color: lightgreen')
        else:
            self.crsSelectedLabel.setText('CRS set to default')
            self.crsSelectedLabel.setStyleSheet('background-color: red')

        if project_bounds is not None:
            bounds_selected = True
            self.boundsSelectedLabel.setText('Bounds Defined')
            self.boundsSelectedLabel.setStyleSheet('background-color: lightgreen')
        else:
            self.boundsSelectedLabel.setText('Bounds not defined')
            self.boundsSelectedLabel.setStyleSheet('background-color: red')

        if project_dir_selected and crs_selected and bounds_selected:
            self.make_template_raster_button.setEnabled(True)
            self.check_size_button.setEnabled(True)
        else:
            self.make_template_raster_button.setEnabled(False)
            self.check_size_button.setEnabled(False)

    def chooseExtentDialog(self):
        popup = ChooseExtent(self)
        popup.exec_()
        self.updateInitiationCheckList()

    def initiate_CMA_workflow(self):
        # Retrieve metadata inputs
        username = self.UserNameLineEdit.text()
        cma_mineral = self.CMA_mineralLineEdit.text()
        comments = self.CommentsText.toPlainText()
        input_path = self.proj_dir_input.filePath()
        box_crs = self.mQgsProjectionSelectionWidget.crs()
        pixel_size = self.pixel_size_input.value()
        buffer_distance = self.buffer_dist_spinBox.value()

        today = date.today().isoformat()

        proj_path = Path(input_path, 'CMA_' + cma_mineral)
        # Turned to true for dev. TODO Raise flag of some kind if overwriting
        proj_path.mkdir(exist_ok=True)
        qgis_proj_file = str(Path(proj_path) / f"{cma_mineral}.qgz")
        template_output_path = str(Path(proj_path, cma_mineral + '_template_raster.tif'))
        data_raster_path = str(Path(proj_path, cma_mineral + '_data_raster.tif'))
        dst_crs = box_crs.authid()

        self.extent_gdf.to_crs(dst_crs, inplace=True)
        if buffer_distance > 0:
            self.extent_gdf.geometry = self.extent_gdf.buffer(buffer_distance)
        bounds = self.extent_gdf.total_bounds

        create_template_raster_from_bounds_and_resolution(bounds=bounds, target_crs=dst_crs, pixel_size=pixel_size,
                                                          output_path=template_output_path, clipping_gdf=self.extent_gdf)
        shutil.copy(template_output_path, data_raster_path)

        meta_dict = {'username': username, 'mineral': cma_mineral, 'comments': comments, 'date_initiated': today,
                     'project_path': str(proj_path), 'project_CRS': str(dst_crs), 'project_bounds': str(bounds),
                     'template_path': template_output_path, 'data_raster_path': data_raster_path,
                     'qgis_project_file': qgis_proj_file}

        with open(Path(proj_path, 'project_metadata.json'), 'w') as f:
            json.dump(meta_dict, f)

        self.parent.meta_data = meta_dict

        message = f"Project files saved to: {proj_path}"
        qgs_data_raster = QgsRasterLayer(self.parent.meta_data['data_raster_path'], 'DataCube')
        QgsProject.instance().addMapLayer(qgs_data_raster)
        QgsProject.instance().layerTreeRoot().findLayer(qgs_data_raster.id()).setItemVisibilityChecked(False)
        QgsProject.instance().setCrs(box_crs)
        QgsProject.instance().setFileName(qgis_proj_file)
        QgsProject.instance().write()
        # QTimer.singleShot(10, set_project_crs(box_crs))
        self.iface.messageBar().pushMessage(message)

    def print_estimated_size(self):
        # selectedLayer = self.template_input.currentLayer()
        # pixel_size = self.pixel_size_input.value()
        # buffer_distance = self.buffer_dist_spinBox.value()
        # box_crs = self.mQgsProjectionSelectionWidget.crs()
        #
        # # This just gets the filename
        # datastr = selectedLayer.source()
        # try:
        #     # This will be the case for geopackages, but not shapefile or geojson
        #     fp, layername = datastr.split('|')
        # except ValueError:
        #     fp = datastr
        #
        # # Define the CRSs
        # dst_crs = box_crs.authid()
        # src_crs = selectedLayer.crs().authid()
        #
        # # bounds was the giving the correct answer the original way. So what does this do different than the ways below??
        # bounds = gpd.read_file(fp).to_crs(dst_crs).total_bounds
        #
        # # Going through without chaining the reproject
        # # reading with geopandas. This is what was taking a long time if input contains complicated geometries
        # gbounds_src = gpd.read_file(fp).total_bounds
        # # bounds was the giving the correct answer the original way
        #
        # bbox_src = box(*gbounds_src)
        # # convert to geoseries for projection methods
        # ggeoseries = gpd.GeoSeries(bbox_src).set_crs(src_crs)
        # ggeoseries_dst = ggeoseries.to_crs(dst_crs)
        # # A buffer if needed would go here
        # if buffer_distance > 0:
        #     geom_series1 = ggeoseries_dst.buffer(buffer_distance)
        # else:
        #     geom_series1 = ggeoseries_dst
        # gbounds1 = geom_series1.total_bounds
        #
        #
        # # There may need to be some crs projection stuff here, but wouldn't change the memory much I imagine - Old Comment
        # # This is using the qgsVectorLayer extent and build in pyqgis reproject
        # qRect_extent_src = selectedLayer.extent()
        # xform = QgsCoordinateTransform(selectedLayer.crs(), box_crs, QgsProject.instance())
        # qRect_extent_dst = xform.transformBoundingBox(qRect_extent_src)
        # # you can see here the qRect_extent_dst is will match gbounds1 and not bounds. So what is happening??
        #
        # # Here trying to do get the qgsRect to a geopandas polygon in source crs, then project with geopandas
        # qbox_src = box(qRect_extent_src.xMinimum(), qRect_extent_src.yMinimum(), qRect_extent_src.xMaximum(), qRect_extent_src.yMaximum())
        # gs_src = gpd.GeoSeries(qbox_src).set_crs(src_crs)
        # gs_dst = gs_src.to_crs(dst_crs)
        # if buffer_distance > 0:
        #     geom_series2 = gs_dst.buffer(buffer_distance)
        # else:
        #     geom_series2 = gs_dst
        # # Why is this different than bounds???
        # gbounds2 = geom_series2.total_bounds
        pixel_size = self.pixel_size_input.value()
        box_crs = self.mQgsProjectionSelectionWidget.crs()
        dst_crs = box_crs.authid()
        buffer_distance = self.buffer_dist_spinBox.value()


        self.extent_gdf.to_crs(dst_crs, inplace=True)
        if buffer_distance > 0:
            self.extent_gdf.geometry = self.extent_gdf.buffer(buffer_distance)
        bounds = self.extent_gdf.total_bounds

        memstring = print_memory_allocation_from_resolution_bounds(bounds, pixel_size)
        self.iface.messageBar().pushMessage(memstring)

        # memstring1 = print_memory_allocation_from_resolution_bounds(gbounds1, pixel_size)
        # self.iface.messageBar().pushMessage(memstring1)
        #
        # memstring2 = print_memory_allocation_from_resolution_bounds(gbounds2, pixel_size)
        # self.iface.messageBar().pushMessage(memstring2)

    def set_project_json(self):
        proj_path = self.resume_json_file_input.filePath()
        with open(Path(proj_path), 'r') as f:
            self.parent.meta_data = json.loads(f.read())
        qgis_proj_file = self.parent.meta_data["qgis_project_file"]
        QgsProject.instance().read(qgis_proj_file)
        message = f"Project files loaded from: {proj_path}"
        # These shouldn't have to be here with the new project saving and reloading
        # qgs_data_raster = QgsRasterLayer(self.parent.meta_data['data_raster_path'], 'DataCube')
        # QgsProject.instance().addMapLayer(qgs_data_raster)
        # crs = QgsCoordinateReferenceSystem(self.parent.meta_data['project_CRS'])
        # QgsProject.instance().setCrs(crs)
        self.iface.messageBar().pushMessage(message)