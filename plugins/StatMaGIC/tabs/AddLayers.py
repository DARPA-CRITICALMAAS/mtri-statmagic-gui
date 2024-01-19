from pathlib import Path

import geopandas as gpd
from shapely import box

from statmagic_backend.geo.transform import get_tiles_for_ll_bounds, download_tiles, process_tiles, \
    dissolve_vector_files_by_property
from statmagic_backend.dev.match_stack_raster_tools import match_and_stack_rasters, add_matched_arrays_to_data_raster

from PyQt5 import QtWidgets
from qgis.core import QgsProject, QgsVectorLayer

from .TabBase import TabBase
from ..gui_helpers import *
from ..constants import resampling_dict
from ..popups.AddRasterLayer import AddRasterLayer
from ..fileops import path_mkdir
from ..layerops import  add_macrostrat_vectortilemap_to_project, return_selected_macrostrat_features_as_qgsLayer


class AddLayersTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Add Layers")

        self.parent = parent

        self.addLayerButton = addButton(self, "Add Layer to List", self.addLayerDialog, align="Left")
        self.listWidget = addListWidget(self)

        stackWidget = addWidgetFromLayout(QtWidgets.QHBoxLayout(), self)
        self.add_rasters_to_stack_button = addButton(stackWidget, "Add List to Raster Stack", self.process_add_raster_list)
        self.num_threads_resamp_spinBox = addSpinBox(stackWidget, "# Threads:", value=1, max=32)
        addToParentLayout(stackWidget)

        self.macrostrat_button = addButton(self, "Pull Macrostrat Tile \n Data in Bounds", self.grab_macrostrat_data_in_bounds, align="Right")
        self.macrostrat_streamButton = addButton(self, 'Load Macrostrat Vector Tiles', self.load_macrostrat_tile_server, align="Left")
        self.macrostrat_returnSelected = addButton(self, 'Return Selected MacroStrat', self.add_selected_macrostrat_to_proj, align="Right")

        # initialize lists to hold stuff later
        self.pathlist = []
        self.methodlist = []
        self.desclist = []

    def addLayerDialog(self):
        popup = AddRasterLayer(self)
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

        # turn method string to resampling type using the dictionary in helperFuncs
        riomethod_list = [resampling_dict.get(m, m) for m in method_list]

        resampled_arrays = match_and_stack_rasters(template_path, input_raster_list, riomethod_list, num_threads=num_threads)
        add_matched_arrays_to_data_raster(data_raster_path, resampled_arrays, description_list)

        self.listWidget.clear()

        message = "Layers appended to the raster data stack"
        self.iface.messageBar().pushMessage(message)

    def grab_macrostrat_data_in_bounds(self):
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

        tile_indices = get_tiles_for_ll_bounds(**bounds)
        m2 = f'retrieved {len(m1)} tiles'
        self.iface.messageBar().pushMessage(m2)

        mapbox_tiles = download_tiles(tile_indices, "https://dev.macrostrat.org/tiles/", "carto")
        m3 = 'downloading tiles'
        self.iface.messageBar().pushMessage(m3)

        js_paths = process_tiles(mapbox_tiles, tile_indices, processing_dir, "units", 4096)
        m4 = 'dissolving tiles'
        self.iface.messageBar().pushMessage(m4)
        # TODO: Figure out why this is crashing and not being caught in the debugger.
        # Also a note that referencing self. in the debug console also crashes, but the folder on line 96 does
        # get created
        # TODO: Somethign off with the function. Another argumnet needed after 'map_id' to specifying which geometries.
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
        QgsProject.instance().addMapLayer(macrostrat_qgs_layer)

    def add_selected_macrostrat_to_proj(self):
        qgs_layer_list = return_selected_macrostrat_features_as_qgsLayer()
        for l in qgs_layer_list:
            QgsProject.instance().addMapLayer(l)

    def refreshList(self, elem):
        self.listWidget.addItem(elem)
