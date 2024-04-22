from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QPushButton, QLabel, QMessageBox, QTextEdit, QComboBox, QTableView, QCheckBox, QVBoxLayout, QHBoxLayout, QFrame, QFormLayout, QSpacerItem, QGridLayout
from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5.QtGui import QPalette, QColor
from qgis.core import QgsVectorLayer, QgsProject, QgsRasterLayer, QgsMapLayerProxyModel, QgsPoint, QgsCoordinateTransform

from .TabBase import TabBase
from ..gui_helpers import *
from ..widgets.collapsible_box import CollapsibleBox
from ..popups.sparql_queries.ore_grades_cutoffs import OreGradeCutoffQueryBuilder
from ..popups.sparql_queries.colocated_coms import ColocatedCommoditiesQueryBuilder
from statmagic_backend.sparql import sparql_utils
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

        self.section_title_font = QtGui.QFont()
        self.section_title_font.setFamily("Ubuntu Mono")
        self.section_title_font.setPointSize(12)
        self.section_title_font.setBold(True)
        self.section_title_font.setWeight(75)

        self.query_btns = [("Commodities", self.clicked_get_commodities_btn, "Get a list of commodities known in the MinMod knowledge graph"),
                           ("Deposit Types", self.clicked_get_deposit_types_btn, "Get a list of all the Deposit Types in the MinMod knowledge graph"),
                           ("Ore Grades", self.clicked_get_ore_grades_btn, "Get selected ore values, grades, and cutoffs from all inventories in the MinMod knowledge graph"),
                           ("Colocated Coms", self.clicked_get_colocated_coms_btn, "Get commodities that appear in the same mineral inventories as a given commodity"),
                           ("btn5", self.clicked_btn5, "Placeholder"),
                           ("btn6", self.clicked_btn6, "Placeholder"),
                           ("btn7", self.clicked_btn7, "Placeholder"),
                           ("btn8", self.clicked_btn8, "Placeholder"),
                           ("btn9", self.clicked_btn9, "Placeholder")]
        self.num_query_btns = len(self.query_btns)

        query_creation_label = QLabel("Create Query")
        query_creation_label.setFont(self.section_title_font)
        self.tabLayout.addWidget(query_creation_label)

        self.queryFrame = QFrame()
        self.queryLayout = QGridLayout()
        num_cols = 2
        for i, (btn_name, btn_callback, btn_tooltip) in enumerate(self.query_btns):
            btn = QPushButton(btn_name)
            btn.setToolTip(btn_tooltip)
            if btn_callback is not None:
                btn.clicked.connect(btn_callback)
            self.queryLayout.addWidget(btn, int(i / num_cols), i % num_cols)

        self.queryFrame.setLayout(self.queryLayout)
        self.tabLayout.addWidget(self.queryFrame)

        self.query_edit_box = CollapsibleBox("View / Edit Sparql Query")
        self.query_edit_box_layout = QGridLayout()
        self.query_edit_text_box = QTextEdit()
        self.query_edit_text_box.textChanged.connect(self.query_changed)
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
        self.run_query_btn.setDisabled(True)
        self.runLayout.addRow(self.query_type_label, self.query_type_selection_box)
        self.runLayout.addRow(self.run_query_btn)
        self.runFrame.setLayout(self.runLayout)
        self.tabLayout.addWidget(self.runFrame)

        ## See the response from the query
        query_response_label = QLabel("Query Response")
        query_response_label.setFont(self.section_title_font)
        self.tabLayout.addWidget(query_response_label)

        self.tableFrame = QFrame()
        self.tableLayout = QFormLayout()
        self.resp_view = QTableView()
        self.tableLayout.addRow(self.resp_view)
        self.tableFrame.setLayout(self.tableLayout)
        self.tabLayout.addWidget(self.tableFrame)

        self.response_description_label = QLabel("No Response Available")
        self.tableLayout.addWidget(self.response_description_label)

        ## Convert response to a GIS layer or CSV
        save_response_label = QLabel("Save Response to File")
        save_response_label.setFont(self.section_title_font)
        self.tabLayout.addWidget(save_response_label)

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
        logger.info("Saving response as csv")
        file_path = self.output_file_text_box.filePath()
        self.last_response.to_csv(file_path, index=False)

    def save_response_to_gis_file(self, location_feature):
        logger.info("Saving path as GeoJSON")
        resp_file_path = Path(self.output_file_text_box.filePath())
        loc_feature = self.location_feature_combo_box.currentText()
        logger.debug("Location feature: ", loc_feature)

        # You will probably need to add code here to convert one of the columns of the response into shapely points,
        # and use that as the geometry column when creating the GeoDataFrame
        df = self.last_response
        logger.info("Loading location feature to WKT")
        df['loc_wkt'] = df[loc_feature].apply(self.safe_wkt_load)
        logger.info("Creating GeoDataFrame")
        logger.debug(df.head())
        gdf = gpd.GeoDataFrame(df, geometry=df['loc_wkt'], crs="EPSG:4326")
        logger.info("Dropping column loc_wkt")
        gdf.drop(columns=['loc_wkt'], inplace=True)
        logger.info("Saving to file")
        gdf.to_file(resp_file_path, driver="GeoJSON")

        logger.info("Opening file as GIS layer", resp_file_path)
        resp_layer = QgsVectorLayer(str(resp_file_path), resp_file_path.stem, "ogr")
        if not resp_layer.isValid():
            msgBox = QMessageBox()
            msgBox.setText("Error creating GIS layer")
            msgBox.exec()
            return
        else:
            QgsProject.instance().addMapLayer(resp_layer)
            #self.iface.messageBar().pushMessage(f"Added {resp_file_path.stem} to map", level=QMessageBox.Information)

    def clicked_btn5(self):
        logger.debug("Clicked button 5!")

    def clicked_btn6(self):
        logger.debug("Clicked button 6!")

    def clicked_btn7(self):
        logger.debug("Clicked button 7!")

    def clicked_btn8(self):
        logger.debug("Clicked button 8!")

    def clicked_btn9(self):
        logger.debug("Clicked button 9!")

    def clicked_get_commodities_btn(self):
        query = ''' SELECT ?ci ?clabel ?cname
                    WHERE {
                        ?ci a :Commodity .
                        ?ci rdfs:label ?clabel .
                        ?ci :name ?cname .
                    } 
                    '''
        self.query_edit_text_box.setText(query)

    def clicked_get_deposit_types_btn(self):
        query = ''' SELECT ?ci ?cn ?cg ?ce
                    WHERE {
                    ?ci a :DepositType .
                    ?ci rdfs:label ?cn .
                    ?ci :deposit_group ?cg .
                    ?ci :environment ?ce .
                    }
                    '''
        self.query_edit_text_box.setText(query)

    def clicked_get_ore_grades_btn(self):
        popup = OreGradeCutoffQueryBuilder(self)
        if popup.exec_():
            self.query_edit_text_box.setText(popup.query)
        else:
            logger.info("Ore / Grades / Cutoff popup closed without setting query")

    def clicked_get_colocated_coms_btn(self):
        popup = ColocatedCommoditiesQueryBuilder(self)
        if popup.exec_():
            self.query_edit_text_box.setText(popup.query)
        else:
            logger.info("Colocated commodities popup closed without setting query")

    def run_query(self):
        self.response_description_label.setText("No Response Available")
        query = self.query_edit_text_box.toPlainText()
        if self.query_type_selection_box.currentText() == 'MinMod':
            res_df = self.run_minmod_query(query)
        else:
            res_df = self.run_geokb_query(query)

        if res_df is None:
            msgBox = QMessageBox()
            msgBox.setText("Query returned None\nQuery may be invalid or the Sparql endpoint may be down")
            msgBox.exec()
            self.resp_view.setModel(None)
            return

        self.last_response = res_df
        self.response_description_label.setText("Number of Response Records = "+str(len(self.last_response)))
        model = pandasModel(res_df)
        self.resp_view.setModel(model)

    def run_minmod_query(self, query):
        logger.debug("Run MindMod Query")
        return statmagic_backend.sparql.sparql_utils.run_minmod_query(query, values=True)

    def run_geokb_query(self, query):
        logger.debug("Run GeoKB Query")
        return statmagic_backend.sparql.sparql_utils.run_sparql_query(query, values=True)

    def query_changed(self):
        text = self.query_edit_text_box.toPlainText()
        if text == "":
            self.run_query_btn.setDisabled(True)
        else:
            self.run_query_btn.setDisabled(False)
