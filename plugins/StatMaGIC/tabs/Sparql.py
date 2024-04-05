from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QPushButton, QLabel, QMessageBox, QTextEdit, QComboBox, QTableView, QCheckBox, QVBoxLayout, QHBoxLayout, QFrame, QFormLayout, QSpacerItem, QGridLayout
from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5.QtGui import QPalette, QColor
from qgis.core import QgsVectorLayer, QgsProject, QgsRasterLayer, QgsMapLayerProxyModel, QgsPoint, QgsCoordinateTransform

from .TabBase import TabBase
from ..gui_helpers import *
from ..widgets.collapsible_box import CollapsibleBox
import statmagic_backend.sparql.sparql_utils
import pandas as pd
import geopandas as gpd
from pathlib import Path

import logging
logger = logging.getLogger("statmagic_gui")


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


class SparqlTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Sparql")

        self.parent = parent
        self.iface = self.parent.iface

        self.query_btns = [("Get Commodities", self.clicked_get_commodities_btn), ("btn2", self.clicked_btn), ("btn3", None),
                           ("btn4", None), ("btn5", self.clicked_btn), ("btn6", None),
                           ("btn7", None), ("btn8", self.clicked_btn), ("btn9", None)]
        self.num_query_btns = len(self.query_btns)

        self.queryFrame = QFrame()
        self.queryLayout = QGridLayout()
        num_cols = 2
        for i, (btn_name, btn_callback) in enumerate(self.query_btns):
            btn = QPushButton(btn_name)
            if btn_callback is not None:
                btn.clicked.connect(btn_callback)
            self.queryLayout.addWidget(btn, int(i / num_cols), i % num_cols)

        self.queryFrame.setLayout(self.queryLayout)
        self.tabLayout.addWidget(self.queryFrame)

        self.query_edit_box = CollapsibleBox("Advanced Strats")
        self.query_edit_box_layout = QGridLayout()
        self.query_edit_text_box = QTextEdit()
        self.query_edit_box_layout.addWidget(self.query_edit_text_box)
        self.query_edit_box.setContentLayout(self.query_edit_box_layout)
        self.tabLayout.addWidget(self.query_edit_box)

        self.runFrame = QFrame()
        self.runLayout = QFormLayout()
        self.query_type_label = QLabel('Query Type')
        self.query_type_selection_box = QComboBox()
        self.query_type_selection_box.addItems(['MinMod', 'GeoKB'])
        self.run_query_btn = QPushButton()
        self.run_query_btn.setText("Run Query")
        self.run_query_btn.clicked.connect(self.run_query)
        self.runLayout.addRow(self.query_type_label, self.query_type_selection_box)
        self.runLayout.addRow(self.run_query_btn)
        self.runFrame.setLayout(self.runLayout)
        self.tabLayout.addWidget(self.runFrame)

        ## See the response from the query
        self.tableFrame = QFrame()
        self.tableLayout = QFormLayout()
        self.resp_view = QTableView()
        self.tableLayout.addRow(self.resp_view)
        self.tableFrame.setLayout(self.tableLayout)
        self.tabLayout.addWidget(self.tableFrame)

        ## Convert response to a GIS layer or CSV
        self.convertFrame = QFrame()
        self.convertLayout = QFormLayout()

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
        self.save_response_btn = QPushButton()
        self.save_response_btn.setText('Save Response to File')
        self.save_response_btn.clicked.connect(self.save_response_to_file)

        self.convertLayout.addRow(self.has_location_label, self.has_location_checkbox)
        self.convertLayout.addRow(self.location_feature_combo_box_label, self.location_feature_combo_box)
        self.convertLayout.addRow(self.output_file_label, self.output_file_text_box)
        self.convertLayout.addWidget(self.save_response_btn)
        self.convertFrame.setLayout(self.convertLayout)
        self.tabLayout.addWidget(self.convertFrame)

        self.last_response = None

    def has_location_checkbox_state_changed(self, state):
        if state == Qt.Checked:
            self.output_file_text_box.setFilter('GeoJSON (*.geojson)')
        else:
            self.output_file_text_box.setFilter('CSV (*.csv)')

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
        logger.debug("Saving response as csv")
        file_path = self.output_file_text_box.filePath()
        self.last_response.to_csv(file_path, index=False)

    def save_response_to_gis_file(self, location_feature):
        logger.debug("Saving path as GeoJSON")
        resp_file_path = Path(self.output_file_text_box.filePath())
        loc_feature = self.location_feature_combo_box.currentText()
        logger.debug("Location feature: ", loc_feature)

        # You will probably need to add code here to convert one of the columns of the response into shapely points,
        # and use that as the geometry column when creating the GeoDataFrame
        df = self.last_response
        logger.debug("Loading location feature to WKT")
        df['loc_wkt'] = df[loc_feature].apply(self.safe_wkt_load)
        logger.debug("Creating GeoDataFrame")
        logger.debug(df.head())
        gdf = gpd.GeoDataFrame(df, geometry=df['loc_wkt'], crs="EPSG:4326")
        logger.debug("Dropping column loc_wkt")
        gdf.drop(columns=['loc_wkt'], inplace=True)
        logger.debug("Saving to file")
        gdf.to_file(resp_file_path, driver="GeoJSON")

        logger.debug("Opening file as GIS layer", resp_file_path)
        resp_layer = QgsVectorLayer(str(resp_file_path), resp_file_path.stem, "ogr")
        if not resp_layer.isValid():
            msgBox = QMessageBox()
            msgBox.setText("Error creating GIS layer")
            msgBox.exec()
            return
        else:
            logger.debug("Adding layer to map")
            QgsProject.instance().addMapLayer(resp_layer)
            #self.iface.messageBar().pushMessage(f"Added {resp_file_path.stem} to map", level=QMessageBox.Information)

    def clicked_btn(self):
        print("Clicked the button!")

    def clicked_get_commodities_btn(self):
        query = ''' SELECT ?ci ?cm
                    WHERE {
                        ?ci a :Commodity .
                        ?ci rdfs:label ?cm .
                    } 
                    '''
        self.query_edit_text_box.setText(query)

    def run_query(self):
        query = self.query_edit_text_box.toPlainText()
        if self.query_type_selection_box.currentText() == 'MinMod':
            res_df = self.run_minmod_query(query)
        else:
            res_df = self.run_geokb_query(query)

        if res_df is None:
            msgBox = QMessageBox()
            msgBox.setText("Query returned None")
            msgBox.exec()
            self.resp_view.setModel(None)
            return

        self.last_response = res_df
        model = pandasModel(res_df)
        self.resp_view.setModel(model)

    def run_minmod_query(self, query):
        logger.debug("Run MindMod Query")
        return statmagic_backend.sparql.sparql_utils.run_minmod_query(query, values=True)

    def run_geokb_query(self, query):
        logger.debug("Run GeoKB Query")
        return statmagic_backend.sparql.sparql_utils.run_sparql_query(query, values=True)


