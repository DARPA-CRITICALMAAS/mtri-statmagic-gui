import os
from pathlib import Path

import geopandas as gpd
from PyQt5.QtCore import QPersistentModelIndex
from shapely import box

from statmagic_backend.geo.transform import get_tiles_for_ll_bounds, download_tiles, process_tiles, \
    dissolve_vector_files_by_property
from statmagic_backend.dev.match_stack_raster_tools import *

import logging
logger = logging.getLogger("statmagic_gui")


from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer
from PyQt5.QtWidgets import QPushButton, QListWidget, QTableWidget, QComboBox, QLabel, QVBoxLayout, QGridLayout, \
    QSpinBox, QHBoxLayout, QSpacerItem, QSizePolicy, QFileDialog, QHeaderView, QTableWidgetItem, QAction, QMenu
from qgis.gui import QgsFileWidget

from .TabBase import TabBase
from ..gui_helpers import *
from ..constants import resampling_dict
from ..popups.AddRasterLayer import AddRasterLayer
from ..popups.addLayersFromExisting import RasterBandSelectionDialog
from ..popups.addLayersFromCloudfront import CloudFrontSelectionDialog
from ..popups.rasterLayrers_process_menu import raster_process_menu
from ..fileops import path_mkdir, kosher
from ..layerops import add_macrostrat_vectortilemap_to_project, return_selected_macrostrat_features_as_qgsLayer
from ..popups.choose_raster_dialog import SelectRasterLayer

class AddLayersTab(TabBase):
    def __init__(self, parent, tabWidget, isEnabled=True):
        super().__init__(parent, tabWidget, "Add Layers", isEnabled)

        self.parent = parent
        self.iface = self.parent.iface
        self.target_raster_layer = None

        # #### TOP FRAME - Macrostrat Tools ####
        topFrame, topLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)

        topFrameLabel = addLabel(topLayout, "Access MacroStrat")
        makeLabelBig(topFrameLabel)
        topFormLayout = QGridLayout()
        # topFormLayout.setColumnStretch(1, 3)
        # topFormLayout.setColumnStretch(1, 3)

        self.addMSbutton = QPushButton()
        self.addMSbutton.setText('Add Macrostrat \n Tile Stream')
        self.addMSbutton.clicked.connect(self.load_macrostrat_tile_server)
        self.addMSbutton.setToolTip('Adds the Macrostrat Tile Service to the current QGIS project')

        # Todo: Make this text dynamic by reading the current zoom level
        # possibly get help here https://gist.github.com/ThomasG77/7c2ecd106091a335a2138dcd82565db8
        self.zoomLevelLabel = QLabel('Current zoom level is _')

        self.returnSelectedButton = QPushButton()
        self.returnSelectedButton.setText('Return Selected \n Macrostrat Features')
        self.returnSelectedButton.clicked.connect(self.add_selected_macrostrat_to_proj)
        self.returnSelectedButton.setToolTip('Downloads the selected Macrostrat Polygons \n and Faults to a temporary layer')

        self.pullMsInBounds = QPushButton()
        self.pullMsInBounds.setText('Download All Macrostrat \n In Canvas Bounds')
        self.pullMsInBounds.clicked.connect(self.grab_macrostrat_data_in_bounds)
        self.pullMsInBounds.setToolTip('This function will download full tiles includign all features within the bounds of the canvas. \n Depending on the zoom level and extent this may take some time')

        self.chooseZoomLabel = QLabel('Select Zoom \nLevel For Download')

        self.selectZoomBox = QComboBox()
        self.selectZoomBox.addItems([str(x+1) for x in range(7)])
        self.selectZoomBox.setToolTip('The zoom level at which features will be downloaded. ')

        topFormLayout.addWidget(self.addMSbutton, 0, 0)
        topFormLayout.addWidget(self.zoomLevelLabel, 0, 1)
        topFormLayout.addWidget(self.returnSelectedButton, 0, 2)
        topFormLayout.addWidget(self.pullMsInBounds, 1, 0)
        topFormLayout.addWidget(self.chooseZoomLabel, 1, 1)
        topFormLayout.addWidget(self.selectZoomBox, 1, 2)

        addWidgetFromLayoutAndAddToParent(topFormLayout, topFrame)
        addToParentLayout(topFrame)

        #### Bottom Frame - Adding Layers Options
        bottomFrame, bottomLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        bottomFrameLabel = addLabel(bottomLayout, "Add Layers To DataCube")
        makeLabelBig(bottomFrameLabel)

        AddLayerButtonsLayout = QGridLayout()

        self.addfromCubeButton = QPushButton()
        self.addfromCubeButton.setText('Add Layers From \n An existing Raster')
        self.addfromCubeButton.clicked.connect(self.chooseLayersFromCubeDialog)
        self.addfromCubeButton.setToolTip('Opens up a new window with options to select layers to add from a existing  dataset.')

        self.addfromCloudButton = QPushButton()
        self.addfromCloudButton.setText('Add Nationwide Layers \nFrom CloudFront')
        self.addfromCloudButton.clicked.connect(self.chooseLayersFromCloudDialog)
        self.addfromCloudButton.setToolTip(
            'Opens up a new window with options to select layers to add from CloudFront COGs.')

        self.addfromCurrentButton = QPushButton()
        self.addfromCurrentButton.setText('Add Layer from \ncurrent QGIS project')
        self.addfromCurrentButton.clicked.connect(self.addLayerDialog)
        self.addfromCloudButton.setToolTip('Opens up window to select from current project layers')

        AddLayerButtonsLayout.addWidget(self.addfromCubeButton, 0, 0)
        AddLayerButtonsLayout.addWidget(self.addfromCloudButton, 0, 1)
        AddLayerButtonsLayout.addWidget(self.addfromCurrentButton, 0, 2)

        tableFrame, tableLayout = addFrame(self, "VBox", "NoFrame", "Plain", 3, spacing=(0,0))

        # Layer table
        self.layer_table = QTableWidget(0, 4)
        self.layer_table.setAlternatingRowColors(True)


        # self.layer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.layer_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        # self.layer_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.layer_table.setHorizontalHeaderLabels(['Band Name', 'Resampling', 'Path', 'Source'])
        self.layer_table.setColumnWidth(0, 200)
        self.layer_table.setColumnWidth(1, 100)
        self.layer_table.setColumnWidth(2, 75)
        self.layer_table.setColumnWidth(3, 75)

        deleteFrame, deleteLayout = addFrame(tableFrame, "HBox", "NoFrame", "Plain", 3, spacing=(5,5))

        self.deleteRowButton = addButton(deleteFrame, "Delete Selected Rows", self.deleteRowsFromTable)
        self.clearTableButton = addButton(deleteFrame, "Clear Table", self.clearTable)

        self.deleteRowButton.setToolTip("Removes selected rows from the table of layers to add.")
        self.clearTableButton.setToolTip("Empties the entire table of layers to add.")

        # Process List Button
        self.processAddLayerButton = QPushButton()
        self.processAddLayerButton.setText('Add List of Layers to DataCube')
        self.processAddLayerButton.clicked.connect(self.process_add_raster_list)
        self.processAddLayerButton.setToolTip('Executes backend functions to resample and add layers in the list \nto the datacube')

        tableLayout.addWidget(self.layer_table)
        tableLayout.addWidget(deleteFrame)
        tableLayout.addWidget(self.processAddLayerButton)

        # Core Count Selection
        self.num_core_label = QLabel('Number of Cores for Processing:')

        veryBottomFormLayout = QHBoxLayout()

        # Add the spinBox for num threads
        self.num_threads_resamp_spinBox = QSpinBox()
        self.num_threads_resamp_spinBox.setMaximum(32)
        self.num_threads_resamp_spinBox.setMinimum(1)
        self.num_threads_resamp_spinBox.setSingleStep(1)
        self.num_threads_resamp_spinBox.setValue(1)

        veryBottomFormLayout.addWidget(self.num_core_label)
        veryBottomFormLayout.addWidget(self.num_threads_resamp_spinBox)

        addWidgetFromLayoutAndAddToParent(AddLayerButtonsLayout, bottomFrame)
        addWidgetFromLayoutAndAddToParent(tableLayout, bottomFrame)
        addWidgetFromLayoutAndAddToParent(veryBottomFormLayout, bottomFrame)
        addToParentLayout(bottomFrame)

        # initialize lists to hold stuff later
        self.sourcelist = []
        self.pathlist = []
        self.methodlist = []
        self.desclist = []
        self.refreshTable()

    def deleteRowsFromTable(self):
        selectedRows = self.layer_table.selectionModel().selectedRows()
        rowsToRemove = [QPersistentModelIndex(row) for row in selectedRows]
        for row in rowsToRemove:
            rowIndex = row.row()
            self.layer_table.removeRow(rowIndex)
            self.desclist.pop(rowIndex)
            self.pathlist.pop(rowIndex)
            self.sourcelist.pop(rowIndex)

    def clearTable(self):
        self.layer_table.clearContents()
        self.layer_table.model().removeRows(0, self.layer_table.rowCount())
        self.desclist.clear()
        self.pathlist.clear()
        self.sourcelist.clear()

    def openDataLayerTable(self):
        # Todo: This functionality should be exposed at the SRI and BEAK tabs and
        # switched to have scaling functions for each band in the raster
        # Todo: Move from this tab
        raster_path_popup = SelectRasterLayer(self.parent)
        raster_path_popup.exec_()
        raster = raster_path_popup.chosen_raster
        logger.debug(f"User chose raster {raster}")

        popup = raster_process_menu(self.parent, raster_layer=raster)
        popup.exec_()

    def addLayerDialog(self):
        # Todo: Find out why cancel is still adding to the table
        popup = AddRasterLayer(self)
        if popup.exec_():
            filepath = popup.currentfile
            # Todo: Check if the 'Band #' in the text needs to be dropped
            description = popup.description
            self.pathlist.append(filepath)
            self.desclist.append(description)
            self.sourcelist.append('Qgs')
            self.refreshTable()

    def chooseLayersFromCubeDialog(self):
        rasterFilePath, _ = QFileDialog.getOpenFileName(self, "Select Raster", str(Path.home()), "GeoTIFFs (*.tif *.tiff)")
        if os.path.exists(rasterFilePath):
            popup = RasterBandSelectionDialog(self.parent, rasterFilePath)
            if popup.exec_():
                band_list = popup.desc_list
                raster_path = popup.raster_layer_path
                band_indexs = popup.index_list
                srs = ['Local' for x in range(len(band_list))]
                paths = [raster_path + '_' + str(x) for x in band_indexs]

                self.pathlist.extend(paths)
                self.desclist.extend(band_list)
                self.sourcelist.extend(srs)
                self.refreshTable()

    def chooseLayersFromCloudDialog(self):
        popup = CloudFrontSelectionDialog(self.parent)
        if popup.exec_():
            band_list = popup.band_list
            cog_list = popup.cog_paths
            srs = ['CloudFront' for x in range(len(band_list))]

            self.pathlist.extend(cog_list)
            self.desclist.extend(band_list)
            self.sourcelist.extend(srs)
            self.refreshTable()

    def process_add_raster_list(self):
        # Todo: There should be some stringent checking to see if each selected layer has
        # - defined CRS
        # - is within the target bounds
        # - a specified transform
        # - a set nodata value
        # If these aren't set they should either try some auto defaults or drop from the list and notify the user
        try:
            template_path = self.parent.meta_data['template_path']
            data_raster_path = self.parent.meta_data['data_raster_path']
        except KeyError:
            message = "Error: please create a template raster first."
            self.iface.messageBar().pushMessage(message)
            return
        num_threads = self.num_threads_resamp_spinBox.value()

        # Set up inputs for the backend
        raster_paths = self.pathlist
        # description_list = self.desclist
        source_list = self.sourcelist

        # Extract table items
        # Make a quick reference to the table
        table = self.layer_table

        method_list = []
        for i in range(table.rowCount()):
            method_string = table.cellWidget(i, 1).currentText()
            method = resampling_dict.get(method_string)
            method_list.append(method)

        description_list = []
        for i in range(table.rowCount()):
            desc = table.item(i, 0).text()
            description_list.append(desc)

        local, cog, order = parse_raster_processing_table_elements(raster_paths, source_list, method_list)

        local_array_list = match_and_stack_rasters(template_path, local['paths'], local['methods'], local['band'], num_threads)
        cog_array_list = match_cogList_to_template_andStack(template_path, cog['paths'], cog['methods'])
        array_stack = reorder_array_lists_to_stack(local_array_list, cog_array_list, order)
        masked_stack = apply_template_mask_to_array(template_path, array_stack)
        add_matched_arrays_to_data_raster(data_raster_path, masked_stack, description_list)

        self.sourcelist.clear()
        self.pathlist.clear()
        self.methodlist.clear()
        self.desclist.clear()
        # Todo: make a table reset method
        self.layer_table.setRowCount(0)

        message = "Layers appended to the raster data stack"
        QgsProject.instance().removeMapLayer(QgsProject.instance().mapLayersByName('DataCube')[0])
        self.iface.mapCanvas().refreshAllLayers()
        data_raster = QgsRasterLayer(self.parent.meta_data['data_raster_path'], 'DataCube')
        QgsProject.instance().addMapLayer(data_raster)

        self.iface.messageBar().pushMessage(message)

    def grab_macrostrat_data_in_bounds(self):
        zoomlevel = int(self.selectZoomBox.currentText())
        bb = self.canvas.extent()
        bb.asWktCoordinates()
        crs_epsg = self.canvas.mapSettings().destinationCrs().authid()

        bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
        bounding_gdf = gpd.GeoDataFrame(geometry=[box(*bbc)], crs=crs_epsg)
        bounding_gdf.to_crs(epsg=4326, inplace=True)

        bounds = bounding_gdf.bounds

        bounds = {
            'n': bounds.maxy[0],
            's': bounds.miny[0],
            'e': bounds.maxx[0],
            'w': bounds.minx[0],
        }

        logger.debug(bounds)

        processing_dir = Path(self.parent.meta_data['project_path']) / 'macrostrat'
        path_mkdir(processing_dir)

        output_path = str(processing_dir / "dissovle_macrostrat.json")
        m1 = 'querying the Macrostrat Tile Server'
        self.iface.messageBar().pushMessage(m1)

        tile_indices = get_tiles_for_ll_bounds(**bounds, zoom_level=zoomlevel)
        m2 = f'retrieved {len(m1)} tiles'
        self.iface.messageBar().pushMessage(m2)

        mapbox_tiles = download_tiles(tile_indices, "https://dev.macrostrat.org/tiles/", "carto")
        m3 = 'downloading tiles'
        self.iface.messageBar().pushMessage(m3)

        js_paths = process_tiles(mapbox_tiles, tile_indices, processing_dir, "units", 4096)
        m4 = 'dissolving tiles'
        self.iface.messageBar().pushMessage(m4)
        # TODO: Return Faults (Polyline) also. Separate file
        dissolve_vector_files_by_property(
            js_paths,
            'map_id',
            ['Polygon', 'MultiPolygon'],
            output_path,
            **bounds
        )

        m5 = 'dissolve finished'
        self.iface.messageBar().pushMessage(m5)
        vlayer = QgsVectorLayer(output_path, "Macrostat_vectors", "ogr")
        QgsProject.instance().addMapLayer(vlayer)

    def load_macrostrat_tile_server(self):
        macrostrat_qgs_layer = add_macrostrat_vectortilemap_to_project()
        QgsProject.instance().setCrs(macrostrat_qgs_layer.crs())
        QgsProject.instance().addMapLayer(macrostrat_qgs_layer)

    def add_selected_macrostrat_to_proj(self):
        qgs_layer_list = return_selected_macrostrat_features_as_qgsLayer()
        for l in qgs_layer_list:
            QgsProject.instance().addMapLayer(l)

    def refreshTable(self):
        logger.debug(f"sourcelist: {self.sourcelist}")
        logger.debug(f"desclist: {self.desclist}")
        # Get current index of last row
        rowPosition = self.layer_table.rowCount()
        # Get total amount of layers to be added
        numLayers = len(self.sourcelist)
        # Calculate number of rows to add
        numNewRow = numLayers - rowPosition
        logger.debug(f"starting at row {rowPosition}")
        # Todo: See here for setting things uneditable
        # https://stackoverflow.com/questions/7727863/how-to-make-a-cell-in-a-qtablewidget-read-only

        for i in range(numNewRow):
            logger.debug(f"adding to table at row {rowPosition + i}")
            logger.debug(self.desclist[i])
            self.layer_table.insertRow(rowPosition + i)
            self.layer_table.setItem(rowPosition + i, 0, QTableWidgetItem(self.desclist[rowPosition + i]))
            # Need to construct the combo box for each row
            rs_cb = QComboBox()
            rs_cb.addItems(['nearest', 'bilinear', 'cubic', 'cubic_spline', 'lanczos', 'average', 'mode', 'gauss'])
            rs_cb.setCurrentIndex(1)
            self.layer_table.setCellWidget(rowPosition + i, 1, rs_cb)
            self.layer_table.setItem(rowPosition + i, 2, QTableWidgetItem(self.pathlist[rowPosition + i]))
            self.layer_table.setItem(rowPosition + i, 3, QTableWidgetItem(self.sourcelist[rowPosition + i]))

