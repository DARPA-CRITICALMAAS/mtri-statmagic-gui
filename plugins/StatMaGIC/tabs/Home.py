import json
import shutil
from datetime import date
from pathlib import Path

from PyQt5.QtWidgets import QPushButton, QLabel, QFrame, QGridLayout, QFileDialog
from qgis.core import QgsRasterLayer, QgsProject, QgsUnitTypes

from statmagic_backend.dev.template_raster_user_input import create_template_raster_from_bounds_and_resolution
from .TabBase import TabBase
from qgis.PyQt import QtGui
from ..layerops import set_project_crs

from ..popups.initiate_CMA_wizard import ProjectWizard

import logging
gui_logger = logging.getLogger("statmagic_gui")
backend_logger = logging.getLogger("statmagic_backend")


class HomeTab(TabBase):
    def __init__(self, parent, tabWidget, isEnabled=True):
        super().__init__(parent, tabWidget, "StatMaGIC Home", isEnabled)
        self.parent = parent
        self.iface = self.parent.iface

        self.section_title_font = QtGui.QFont()
        self.section_title_font.setFamily("Ubuntu Mono")
        self.section_title_font.setPointSize(16)
        self.section_title_font.setBold(True)
        self.section_title_font.setWeight(75)

        header_label = QLabel("Welcome to StatMagic Plugin")
        header_label.setFont(self.section_title_font)
        self.tabLayout.addWidget(header_label)


        self.home_button_frame = QFrame()
        home_buttons_Layout = QGridLayout()

        self.initCMA_Button = QPushButton()
        self.initCMA_Button.setText('Initiate CMA')
        self.initCMA_Button.clicked.connect(self.launch_CMA_wizard)
        self.initCMA_Button.setToolTip(
            'Launches the CMA wizard to create a new CMA')

        self.resumeCMA_Button = QPushButton()
        self.resumeCMA_Button.setText('Resume CMA')
        self.resumeCMA_Button.clicked.connect(self.set_project_json)
        self.resumeCMA_Button.setToolTip(
            'Opens up a dialog to select a json project file to resume a CMA')

        self.editCMA_Button = QPushButton()
        self.editCMA_Button.setText('Edit CMA')
        self.editCMA_Button.clicked.connect(self.edit_CMA_dialog)
        self.editCMA_Button.setToolTip('Opens up dialog to edit CMA metadata')
        self.editCMA_Button.setEnabled(False)

        home_buttons_Layout.addWidget(self.initCMA_Button, 0, 0)
        home_buttons_Layout.addWidget(self.resumeCMA_Button, 0, 1)
        home_buttons_Layout.addWidget(self.editCMA_Button, 0, 2)

        self.home_button_frame.setLayout(home_buttons_Layout)
        self.tabLayout.addWidget(self.home_button_frame)

        help_label = QLabel("If this is your first time using StatMagic you can \n"
                            " access help documents and tutorials with these options")

        self.help_msg_font = QtGui.QFont()
        self.help_msg_font.setFamily("Ubuntu Mono")
        self.help_msg_font.setPointSize(12)
        self.help_msg_font.setBold(True)
        self.help_msg_font.setWeight(50)
        help_label.setFont(self.help_msg_font)
        self.tabLayout.addWidget(help_label)

        self.help_button_frame = QFrame()
        help_buttons_Layout = QGridLayout()

        self.viewTutorial_Button = QPushButton()
        self.viewTutorial_Button.setText('Launch Tutorial')
        self.viewTutorial_Button.clicked.connect(self.launch_tutorial)
        self.viewTutorial_Button.setEnabled(False)

        self.viewDocs_Button = QPushButton()
        self.viewDocs_Button.setText('View Documentation Pages')
        self.viewDocs_Button.clicked.connect(self.open_docs_page)
        self.viewDocs_Button.setEnabled(False)

        help_buttons_Layout.addWidget(self.viewTutorial_Button, 0, 0)
        help_buttons_Layout.addWidget(self.viewDocs_Button, 0, 1)

        self.help_button_frame.setLayout(help_buttons_Layout)
        self.tabLayout.addWidget(self.help_button_frame)


    def launch_CMA_wizard(self):
        self.wizard = ProjectWizard(self)
        self.wizard.show()

    def set_project_json(self):
        # Grab and modify from last function on InitiateCMA.py
        jsonFilePath, filter = QFileDialog.getOpenFileName(self, "", "Select JSON", "JSON (*.json)")
        if Path(jsonFilePath).exists() and filter:
            gui_logger.debug(jsonFilePath)
            with open(Path(jsonFilePath), 'r') as f:
                self.parent.meta_data = json.loads(f.read())
            qgis_proj_file = self.parent.meta_data["qgis_project_file"]
            QgsProject.instance().read(qgis_proj_file)
            self.iface.messageBar().pushMessage(f"Files loaded from: {jsonFilePath}")

    def edit_CMA_dialog(self):
        pass

    def launch_tutorial(self):
        pass

    def open_docs_page(self):
        pass

    def flush_logs(self, logger, logfile):
        # create logfile and flush existing logs to it
        with open(logfile, "w") as newLog:
            newLog.write(logger.handlers[0].stream.__str__())
        # future logs will be written both to file and to the in-memory buffer
        log_format = "%(asctime)s %(levelname)s: %(message)s"
        formatter = logging.Formatter(log_format)
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

    def initiate_CMA_workflow(self):
        # Retrieve metadata inputs
        username = self.wizard.field("user_name")
        cma_name = self.wizard.field("cma_name")
        cma_mineral = self.wizard.field("cma_mineral")
        comments = self.wizard.field("comments")
        input_path = self.wizard.field("input_path")
        box_crs = self.wizard.field("crs")
        pixel_size = self.wizard.field("pixel_size")
        buffer_distance = self.wizard.field("buffer_distance")
        extent_gdf = self.wizard.extent_gdf

        gui_logger.debug(extent_gdf)
        gui_logger.debug(QgsUnitTypes.encodeUnit(box_crs.mapUnits()))
        gui_logger.debug(cma_name)
        gui_logger.debug(cma_mineral)
        gui_logger.debug(input_path)
        gui_logger.debug(box_crs)
        gui_logger.debug(pixel_size)

        today = date.today().isoformat()

        proj_path = Path(input_path, 'CMA_' + cma_mineral)
        # Turned to true for dev. TODO Raise flag of some kind if overwriting
        proj_path.mkdir(exist_ok=True)

        # now that we have the project path, we can flush existing logs to file
        gui_logfile = Path(proj_path) / "gui.log"
        backend_logfile = Path(proj_path) / "backend.log"
        self.flush_logs(gui_logger, gui_logfile)
        self.flush_logs(backend_logger, backend_logfile)

        qgis_proj_file = str(Path(proj_path) / f"{cma_mineral}.qgz")
        template_output_path = str(Path(proj_path, cma_mineral + '_template_raster.tif'))
        data_raster_path = str(Path(proj_path, cma_mineral + '_data_raster.tif'))
        dst_crs = box_crs.authid()
        if extent_gdf.crs != dst_crs:
            extent_gdf.to_crs(dst_crs, inplace=True)
        if buffer_distance > 0:
            extent_gdf.geometry = extent_gdf.buffer(buffer_distance)
        bounds = extent_gdf.total_bounds

        create_template_raster_from_bounds_and_resolution(bounds=bounds, target_crs=dst_crs, pixel_size=pixel_size,
                                                          output_path=template_output_path, clipping_gdf=extent_gdf)
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





