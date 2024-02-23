import sys
if sys.version_info < (3, 9):
    from importlib_resources import files
else:
    from importlib.resources import files

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QPushButton, QLabel, QMessageBox, QTextEdit, QComboBox, QTableView, QCheckBox
from PyQt5.QtCore import Qt, QAbstractTableModel
from qgis.core import QgsVectorLayer, QgsProject, QgsRasterLayer, QgsMapLayerProxyModel, QgsPoint, QgsCoordinateTransform

from .TabBase import TabBase
from ..gui_helpers import *
import rasterio as rio
from rasterio.windows import Window
import requests
import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely import wkt
from shapely.wkt import loads
from shapely.errors import WKTReadingError

class pandasModel(QAbstractTableModel):

    def __init__(self, data):
        QAbstractTableModel.__init__(self)
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[col]
        return None


class TA2Tab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "TA2-USC")

        self.parent = parent
        self.iface = self.parent.iface

        print("Creating TA2 tab")
        ## Top Frame - Input query and run minmod query
        topFrame, topLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        topFrameLabel = addLabel(topLayout, "Run MinMod Query")
        makeLabelBig(topFrameLabel)
        topFormLayout = QtWidgets.QFormLayout()

        print("Create query input box")
        self.query_type_label = QLabel('Query Type')
        self.query_type_selection_box = QComboBox()
        self.query_type_selection_box.addItems(['MinMod', 'GeoKB'])
        self.query_text_label = QLabel('Query Input')
        self.query_text_box = QTextEdit()
        self.query_text_box.setReadOnly(False)
        self.query_text_box.setMaximumHeight(100)

        print("Create run minmod query button")
        self.run_minmod_query_btn = QPushButton()
        self.run_minmod_query_btn.setText('Run MinMod Query')
        self.set_run_query_btn_text()
        self.query_type_selection_box.currentTextChanged.connect(self.set_run_query_btn_text)
        self.run_minmod_query_btn.clicked.connect(self.process_query)

        print("Create layout")
        topFormLayout.addRow(self.query_type_label, self.query_type_selection_box)
        topFormLayout.addRow(self.query_text_label, self.query_text_box)
        topFormLayout.addRow(self.run_minmod_query_btn)
        addWidgetFromLayoutAndAddToParent(topFormLayout, topFrame)
        addToParentLayout(topFrame)

        ## Middle Frame - See minmod response
        respFrame, respLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        respFrameLabel = addLabel(respLayout, "MinMod Response")
        makeLabelBig(respFrameLabel)
        respFormLayout = QtWidgets.QFormLayout()

        self.resp_view = QTableView()

        respFormLayout.addRow(self.resp_view)
        addWidgetFromLayoutAndAddToParent(respFormLayout, respFrame)
        addToParentLayout(respFrame)

        ## Bottom Frame - Convert response to a GIS layer
        tolayerFrame, tolayerLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        tolayerFrameLabel = addLabel(tolayerLayout, "Convert to GIS Layer")
        makeLabelBig(tolayerFrameLabel)
        tolayerFormLayout = QtWidgets.QFormLayout()

        self.has_location_label = QLabel('Response has Location?')
        self.has_location_checkbox = QCheckBox()
        self.has_location_checkbox.setChecked(False)
        self.has_location_checkbox.stateChanged.connect(self.has_location_checkbox_state_changed)
        self.location_feature_combo_box_label = QLabel('Response Location Feature')
        self.location_feature_combo_box = QComboBox()
        self.output_file_label = QLabel('Output File')
        self.output_file_text_box = QgsFileWidget()
        self.output_file_text_box.setStorageMode(QgsFileWidget.StorageMode.SaveFile)
        self.output_file_text_box.setFilter('CSV (*.csv)')
        #self.output_file_text_box.setFilter('GeoJSON (*.geojson)')
        self.save_response_btn = QPushButton()
        self.save_response_btn.setText('Save Response to File')
        self.save_response_btn.clicked.connect(self.save_response_to_file)

        tolayerFormLayout.addRow(self.has_location_label, self.has_location_checkbox)
        tolayerFormLayout.addRow(self.location_feature_combo_box_label, self.location_feature_combo_box)
        tolayerFormLayout.addRow(self.output_file_label, self.output_file_text_box)
        tolayerFormLayout.addWidget(self.save_response_btn)
        addWidgetFromLayoutAndAddToParent(tolayerFormLayout, tolayerFrame)
        addToParentLayout(tolayerFrame)

        self.last_response = None

    def has_location_checkbox_state_changed(self, state):
        if state == Qt.Checked:
            self.output_file_text_box.setFilter('GeoJSON (*.geojson)')
        else:
            self.output_file_text_box.setFilter('CSV (*.csv)')

    def set_run_query_btn_text(self):
        if self.query_type_selection_box.currentText() == 'MinMod':
            self.run_minmod_query_btn.setText('Run MinMod Query')
        else:
            self.run_minmod_query_btn.setText('Run GeoKB Query')

    def process_query(self):
        print("Running minmod query")
        query = self.query_text_box.toPlainText()
        print(query)
        if self.query_type_selection_box.currentText() == 'MinMod':
            res_df = self.run_minmod_query(query)
        else:
            res_df = self.run_geokb_query(query)

        print(res_df)
        if res_df is None:
            msgBox = QMessageBox()
            msgBox.setText("Query returned None")
            msgBox.exec()
            self.resp_view.setModel(None)
            return

        self.last_response = res_df
        model = pandasModel(res_df)
        self.resp_view.setModel(model)

        self.location_feature_combo_box.clear()
        self.location_feature_combo_box.addItems(res_df.columns)

        print("Done running query")

    def run_minmod_query(self, query, values=False):
        print("Run MindMod Query")
        return self.run_sparql_query(query, endpoint='https://minmod.isi.edu/sparql', values=values)

    def run_geokb_query(self, query, values=False):
        print("Run GeoKB Query")
        return self.run_sparql_query(query, endpoint='https://geokb.wikibase.cloud/query/sparql', values=values)

    def run_sparql_query(self, query, endpoint='https://minmod.isi.edu/sparql', values=False):
        # add prefixes
        final_query = '''
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX : <https://minmod.isi.edu/resource/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX gkbi: <https://geokb.wikibase.cloud/entity/>
        PREFIX gkbp: <https://geokb.wikibase.cloud/wiki/Property:>
        PREFIX gkbt: <https://geokb.wikibase.cloud/prop/direct/>
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        \n''' + query
        # send query
        print("Posting final query :", final_query)
        try:
            response = requests.post(
                url=endpoint,
                data={'query': final_query},
                timeout=5,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/sparql-results+json"  # Requesting JSON format
                },
                verify=False  # Set to False to bypass SSL verification as per the '-k' in curl
            )
        except requests.exceptions.Timeout:
            print("Request timed out")
            msgBox = QMessageBox()
            msgBox.setText("Request timed out")
            msgBox.exec()
            return None

        print(response.status_code)
        if response.status_code == 404:
            print("Endpoint not found")
            msgBox = QMessageBox()
            msgBox.setText("Endpoint not found")
            msgBox.exec()
            return None

        #print(response.text)
        try:
            qres = response.json()
            if "results" in qres and "bindings" in qres["results"]:
                df = pd.json_normalize(qres['results']['bindings'])
                if values:
                    filtered_columns = df.filter(like='.value').columns
                    df = df[filtered_columns]
                return df
        except:
            return None

    def save_response_to_file(self):
        if self.last_response is None:
            msgBox = QMessageBox()
            msgBox.setText("No response to save")
            msgBox.exec()
            return

        if self.has_location_checkbox.isChecked():
            location_feature = self.location_feature_combo_box.currentText()
            if location_feature == "":
                msgBox = QMessageBox()
                msgBox.setText("No location feature selected")
                msgBox.exec()
                return
            else:
                self.save_response_to_gis_file(location_feature)
        else:
            self.save_response_to_csv_file()

    def save_response_to_csv_file(self):
        print("Saving response as csv")
        file_path = self.output_file_text_box.filePath()
        self.last_response.to_csv(file_path, index=False)

    def save_response_to_gis_file(self, location_feature):
        print("Saving path as GeoJSON")
        resp_file_path = Path(self.output_file_text_box.filePath())
        loc_feature = self.location_feature_combo_box.currentText()
        print("Location feature: ", loc_feature)

        # You will probably need to add code here to convert one of the columns of the response into shapely points,
        # and use that as the geometry column when creating the GeoDataFrame
        df = self.last_response
        print("Loading location feature to WKT")
        df['loc_wkt'] = df[loc_feature].apply(self.safe_wkt_load)
        print("Creating GeoDataFrame")
        print(df.head())
        gdf = gpd.GeoDataFrame(df, geometry=df['loc_wkt'], crs="EPSG:4326")
        print("Dropping column loc_wkt")
        gdf.drop(columns=['loc_wkt'], inplace=True)
        print("Saving to file")
        gdf.to_file(resp_file_path, driver="GeoJSON")

        print("Opening file as GIS layer", resp_file_path)
        resp_layer = QgsVectorLayer(str(resp_file_path), resp_file_path.stem, "ogr")
        if not resp_layer.isValid():
            msgBox = QMessageBox()
            msgBox.setText("Error creating GIS layer")
            msgBox.exec()
            return
        else:
            print("Adding layer to map")
            QgsProject.instance().addMapLayer(resp_layer)
            #self.iface.messageBar().pushMessage(f"Added {resp_file_path.stem} to map", level=QMessageBox.Information)

    def safe_wkt_load(self, wkt_string):
        try:
            return loads(wkt_string)
        except WKTReadingError as e:
            print(f"Error converting WKT: {e}")
            return None
