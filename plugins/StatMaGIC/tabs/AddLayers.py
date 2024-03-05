from pathlib import Path

import geopandas as gpd
from shapely import box

from statmagic_backend.geo.transform import get_tiles_for_ll_bounds, download_tiles, process_tiles, \
    dissolve_vector_files_by_property
from statmagic_backend.dev.match_stack_raster_tools import match_and_stack_rasters, add_matched_arrays_to_data_raster


from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer
from PyQt5.QtWidgets import QPushButton, QListWidget, QComboBox, QLabel, QVBoxLayout, QGridLayout, QSpinBox, QHBoxLayout, QSpacerItem, QSizePolicy
from qgis.gui import QgsFileWidget

from .TabBase import TabBase
from ..gui_helpers import *
from ..constants import resampling_dict
from ..popups.AddRasterLayer import AddRasterLayer
from ..popups.addLayersFromExisting import RasterBandSelectionDialog
from ..popups.addLayersFromCloudfront import CloudFrontSelectionDialog
from ..fileops import path_mkdir
from ..layerops import add_macrostrat_vectortilemap_to_project, return_selected_macrostrat_features_as_qgsLayer


class AddLayersTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Add Layers")

        self.parent = parent
        self.iface = self.parent.iface

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
        self.addfromCubeButton.setText('Choose Layers From \n An existing Raster')
        self.addfromCubeButton.clicked.connect(self.chooseLayersFromCubeDialog)
        self.addfromCubeButton.setToolTip('Opens up a new window with options to select layers to add from a existing  dataset.')

        self.dataCubeFile = QgsFileWidget()
        self.dataCubeFile.setFilePath('/home/jagraham/Documents/Local_work/statMagic/hack6_data/MTRI_DataCube/NA_output_noNan.tif')
        self.dataCubeFile.setToolTip('Choose an existing raster to select layers from')

        self.addfromCloudButton = QPushButton()
        self.addfromCloudButton.setText('Add Nationwide Layers \nFrom CloudFront')
        self.addfromCloudButton.clicked.connect(self.chooseLayersFromCloudDialog)
        self.addfromCloudButton.setToolTip(
            'Opens up a new window with options to select layers to add from CloudFront COGs.')


        AddLayerButtonsLayout.addWidget(self.addfromCubeButton, 0, 0)
        AddLayerButtonsLayout.addWidget(self.dataCubeFile, 0, 1)
        AddLayerButtonsLayout.addWidget(self.addfromCloudButton, 2, 0)


        bottomFormLayout = QVBoxLayout()

        # Add Layer Button
        self.addLayerButton = QPushButton()
        self.addLayerButton.setText('Open Add Layer Dialog And Add To List')
        self.addLayerButton.clicked.connect(self.addLayerDialog)
        self.addLayerButton.setToolTip('Opens up a new window with options to add existing layers to the DataCube')

        # Layer List
        self.addLayerList = QListWidget()
        self.addLayerList.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        # Process List Button
        self.processAddLayerButton = QPushButton()
        self.processAddLayerButton.setText('Add List of Layers to DataCube')
        self.processAddLayerButton.clicked.connect(self.process_add_raster_list)
        self.processAddLayerButton.setToolTip('Executes backend functions to resample and add layers in the list \nto the datacube')

        bottomFormLayout.addWidget(self.addLayerButton)
        bottomFormLayout.addWidget(self.addLayerList)
        bottomFormLayout.addWidget(self.processAddLayerButton)

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
        addWidgetFromLayoutAndAddToParent(bottomFormLayout, bottomFrame)
        addWidgetFromLayoutAndAddToParent(veryBottomFormLayout, bottomFrame)
        addToParentLayout(bottomFrame)

        # initialize lists to hold stuff later
        self.pathlist = []
        self.methodlist = []
        self.desclist = []

    def addLayerDialog(self):
        popup = AddRasterLayer(self)
        popup.exec_()

    def chooseLayersFromCubeDialog(self):
        # Todo: This should popup first a file dialog of which to select the raster, then go to the selection menu
        popup = RasterBandSelectionDialog(self.parent, self.dataCubeFile.filePath())
        popup.exec_()

    def chooseLayersFromCloudDialog(self):
        popup = CloudFrontSelectionDialog(self.parent)
        popup.exec_()

    def process_add_raster_list(self):
        try:
            template_path = self.parent.meta_data['template_path']
            data_raster_path = self.parent.meta_data['data_raster_path']
        except KeyError:
            message = "Error: please create a template raster first."
            self.iface.messageBar().pushMessage(message)
            return

        num_threads = self.num_threads_resamp_spinBox.value()

        input_raster_list = self.pathlist
        method_list = self.methodlist
        description_list = self.desclist

        # Todo: Need to be able to handle multiband inputs
        # turn method string to resampling type using the dictionary in helperFuncs
        riomethod_list = [resampling_dict.get(m, m) for m in method_list]
        print(riomethod_list)

        resampled_arrays = match_and_stack_rasters(template_path, input_raster_list, riomethod_list, num_threads=num_threads)
        add_matched_arrays_to_data_raster(data_raster_path, resampled_arrays, description_list)

        self.addLayerList.clear()
        self.pathlist.clear()
        self.methodlist.clear()
        self.desclist.clear()

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

        print(bounds)

        # Starting from the __main__
        # TODO: Make this folder in the project folder
        # TODO: have the zoom level accessible


        # processing_dir = Path('/home/jagraham/Documents/Local_work/statMagic/devtest/macrostrat_output')
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

    def refreshList(self, elem):
        self.addLayerList.addItem(elem)
