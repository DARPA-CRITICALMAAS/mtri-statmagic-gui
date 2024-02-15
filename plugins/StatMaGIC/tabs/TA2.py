import sys
if sys.version_info < (3, 9):
    from importlib_resources import files
else:
    from importlib.resources import files

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QPushButton, QLabel, QMessageBox, QTextEdit, QComboBox, QTableView
from PyQt5.QtCore import Qt, QAbstractTableModel
from qgis.core import QgsVectorLayer, QgsProject, QgsRasterLayer, QgsMapLayerProxyModel, QgsPoint, QgsCoordinateTransform

from .TabBase import TabBase
from ..gui_helpers import *
import rasterio as rio
from rasterio.windows import Window
import requests
import pandas as pd


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
        self.query_text_label = QLabel('Query Type')
        self.query_type_selection_box = QComboBox()
        self.query_type_selection_box.addItems(['MinMod', 'GeoKB'])
        self.query_text_box = QTextEdit()
        self.query_text_box.setReadOnly(False)
        self.query_text_box.setMaximumHeight(100)

        print("Create run minmod query button")
        self.run_minmod_query_btn = QPushButton()
        self.run_minmod_query_btn.setText('Run MinMod Query')
        self.run_minmod_query_btn.clicked.connect(self.process_minmod_query)

        print("Create layout")
        topFormLayout.addRow(self.query_text_label, self.query_type_selection_box)
        topFormLayout.addRow(self.query_text_box)
        topFormLayout.addRow(self.run_minmod_query_btn)
        addWidgetFromLayoutAndAddToParent(topFormLayout, topFrame)
        addToParentLayout(topFrame)

        ## Middle Frame - See minmod response
        respFrame, respLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        respFrameLabel = addLabel(respLayout, "MinMod Response")
        makeLabelBig(respFrameLabel)
        respFormLayout = QtWidgets.QFormLayout()

        #self.resp_text_box = QTextEdit()
        #self.resp_text_box.setReadOnly(True)
        #self.resp_text_box.setMaximumHeight(100)
        self.resp_view = QTableView()
        #self.resp_view.resize()

        respFormLayout.addRow(self.resp_view)
        addWidgetFromLayoutAndAddToParent(respFormLayout, respFrame)
        addToParentLayout(respFrame)

    def process_minmod_query(self):
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

        model = pandasModel(res_df)
        self.resp_view.setModel(model)

        print("Done running query")
        #self.resp_text_box.setText(res_df.head())

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
        print(response.status_code)
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



