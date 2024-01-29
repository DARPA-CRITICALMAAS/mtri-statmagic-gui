from PyQt5.QtWidgets import QDialogButtonBox,  QLineEdit, QDialog, QVBoxLayout, QPushButton, QLabel, QCheckBox
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapLayerComboBox, QgsFileWidget
from qgis.core import QgsProject
from shapely.geometry import box
from shapely.wkt import loads
import geopandas as gpd

class ChooseExtent(QDialog):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        # super(AddRasterLayer, self).__init__(parent)
        super(ChooseExtent, self).__init__()

        # preserve a pointer to the dockwidget to access its attributes
        self.parent = parent
        self.extent_gdf = None
        self.crs_epsg = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.drawButton = QPushButton(self)
        self.drawButton.setText('Draw On Canvas')
        self.drawButton.clicked.connect(self.draw_on_canvas)
        self.drawButton.setToolTip('Click points on the canvas to create a polygon to define bounds')

        self.captureButton = QPushButton(self)
        self.captureButton.setText('Capture From Canvas')
        self.captureButton.clicked.connect(self.capture_canvas_extent)
        self.captureButton.setToolTip('Click points on the canvas to create a polygon to define bounds')

        self.label0 = QLabel('Select From Loaded Layer')

        self.selectfromLayerBox = QgsMapLayerComboBox(self)
        self.selectfromLayerBox.setPlaceholderText('Choose From Layer...')
        self.selectfromLayerBox.setToolTip('Uses the rectangular extent of layer to define bounds')

        label1 = QLabel('Use Selected Feature')
        self.useSelectedFeatureCheck = QCheckBox(self)
        self.useSelectedFeatureCheck.setToolTip('Will only consider the selected feature for determining extent')

        self.process_layerBox = QPushButton()
        self.process_layerBox.setText('Capture From Selected Layer')
        self.process_layerBox.clicked.connect(self.get_extent_from_LayerComboBox)
        self.process_layerBox.setToolTip('Will pull the geometry from the selected layer to define bounds')

        label2 = QLabel('Select From File')
        self.fileInput = QgsFileWidget(self)

        # self.extentBox = QgsExtentGroupBox(self)

        self.DeterminedExtentText = QLineEdit(self)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)


        layout.addWidget(self.drawButton)
        layout.addWidget(self.captureButton)
        layout.addWidget(self.label0)
        layout.addWidget(self.selectfromLayerBox)
        layout.addWidget(label1)
        layout.addWidget(self.useSelectedFeatureCheck)
        layout.addWidget(self.process_layerBox)
        layout.addWidget(label2)
        layout.addWidget(self.fileInput)
        layout.addWidget(self.DeterminedExtentText)
        layout.addWidget(self.buttonBox)

        self.signals_connection()
        self.setLayout(layout)

    def signals_connection(self):
        self.buttonBox.accepted.connect(self.returnExtent)
        self.buttonBox.rejected.connect(self.cancel)

    def capture_canvas_extent(self):
        self.crs_epsg = QgsProject.instance().crs().authid()
        bb = self.parent.parent.canvas.extent()
        bb.asWktCoordinates()
        bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
        shapelyBox = box(*bbc)
        self.extent_gdf = gpd.GeoDataFrame(geometry=[shapelyBox], crs=self.crs_epsg)
        self.DeterminedExtentText.setText('Bounds Pulled From Canvas Extent')

    def get_extent_from_LayerComboBox(self):
        selectedLayer = self.selectfromLayerBox.currentLayer()
        self.crs_epsg = selectedLayer.crs().authid()
        bb = selectedLayer.extent()
        bb.asWktCoordinates()
        bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
        shapelyBox = box(*bbc)

        if self.useSelectedFeatureCheck.isChecked():
            sel = selectedLayer.selectedFeatures()[0]
            shapely_poly = loads(sel.geometry().asWkt())
            self.extent_gdf = gpd.GeoDataFrame(geometry=[shapely_poly], crs=self.crs_epsg)
            self.DeterminedExtentText.setText('Bounds And Geometry Pulled From Selected Features')
        else:
            self.extent_gdf = gpd.GeoDataFrame(geometry=[shapelyBox], crs=self.crs_epsg)
            self.DeterminedExtentText.setText('Bounds Pulled From Selected Layer Extent')

    def returnExtent(self):
        self.parent.extent_gdf = self.extent_gdf
        self.parent.src_crs = self.crs_epsg
        self.close()

    def draw_on_canvas(self):
        bb = self.parent.canvas.extent()
        bb.asWktCoordinates()
        bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]


    def cancel(self):
        self.close()
