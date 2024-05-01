from PyQt5.QtWidgets import QPushButton, QCheckBox, QWizard, QSpinBox, QWizardPage, QLabel, QLineEdit, QVBoxLayout, \
    QGridLayout, QTextEdit, QMessageBox, QTextBrowser
from qgis._gui import QgsMapToolPan
from qgis.gui import QgsProjectionSelectionTreeWidget, QgsFileWidget, QgsMapLayerComboBox

from qgis.core import QgsProject, QgsUnitTypes, QgsMapLayerProxyModel
from qgis.PyQt import QtGui

from shapely.geometry import box
from shapely.wkt import loads
import geopandas as gpd
from ..popups.grab_polygon import PolygonMapTool
from ..popups.grab_rectangle import RectangleMapTool
from ..popups.add_drop_layers.wizard_add_layers_to_proj import AddLayerToProject
from pathlib import Path
import math
# modified from https://north-road.com/2018/03/09/implementing-an-in-house-new-project-wizard-for-qgis/


class ProjectWizard(QWizard):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.iface = self.parent.iface

        self.setWindowTitle("Initiate CMA Wizard")

        self.extent_gdf = None
        self.bounds = None

        self.addPage(Page1(self))
        self.addPage(Page2(self))
        self.addPage(Page3(self))
        self.addPage(Page4(self))
        self.addPage(Page5(self))

        self.button(QWizard.FinishButton).clicked.connect(self.parent.initiate_CMA_workflow)

    def reject(self):
        # we need to call QWizard's reject method to actually close the window
        super().reject()


class Page1(QWizardPage):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setTitle('Initiate CMA Wizard')
        self.setSubTitle('Define metadata, geospatial settings, and properties for this CMA.')

        # create some widgets
        self.UserNameLineEdit = QLineEdit()
        self.CMA_NameLineEdit = QLineEdit()
        self.CMA_MineralLineEdit = QLineEdit()
        self.CommentsText = QTextEdit()

        # set the page layout
        layout = QGridLayout()
        layout.addWidget(QLabel('User Name'), 0, 0)
        layout.addWidget(self.UserNameLineEdit, 0, 1)
        layout.addWidget(QLabel('CMA Name'), 1, 0)
        layout.addWidget(self.CMA_NameLineEdit, 1, 1)
        layout.addWidget(QLabel('CMA Mineral'), 2, 0)
        layout.addWidget(self.CMA_MineralLineEdit, 2, 1)
        layout.addWidget(QLabel('Comments'), 3, 0)
        layout.addWidget(self.CommentsText, 3, 1)

        self.setLayout(layout)

        self.registerField('user_name*', self.UserNameLineEdit)
        self.registerField('cma_name*', self.CMA_NameLineEdit)
        self.registerField('cma_mineral*', self.CMA_MineralLineEdit)
        self.registerField('comments', self.CommentsText)

        self.CommentsText.textChanged.connect(self.commentsTyped)


        # Delete this when done testing
        # self.registerField('user_name', self.UserNameLineEdit)
        # self.registerField('cma_name', self.CMA_NameLineEdit)
        # self.registerField('cma_mineral', self.CMA_MineralLineEdit)
        # self.registerField('comments', self.CommentsText)

    def commentsTyped(self):
        self.setField("comments", self.CommentsText.toPlainText())

    def reject(self):
        pass

class Page2(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setTitle('Select Project Directory')
        self.setSubTitle('Choose the directory where your project data will be stored.')

        self.proj_dir_input = QgsFileWidget()
        self.proj_dir_input.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)

        self.registerField("input_path*", self.proj_dir_input, "filePath", self.proj_dir_input.fileChanged)
        self.proj_dir_input.fileChanged.connect(self.dir_selected)

        layout = QGridLayout()
        layout.addWidget(QLabel('Select Directory'), 0, 0)
        layout.addWidget(self.proj_dir_input, 0, 1)

        self.setLayout(layout)

    def dir_selected(self):
        self.setField("input_path", self.proj_dir_input.filePath())

    def isComplete(self):
        return bool(self.proj_dir_input.filePath())


class Page3(QWizardPage):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setTitle('Project Coordinate System')
        self.setSubTitle(
            'Choosing an appropriate projection is important to ensure accurate distance and area measurements.')

        self.proj_selector = QgsProjectionSelectionTreeWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.proj_selector)
        self.setLayout(layout)

        self.registerField('crs', self.proj_selector)
        self.proj_selector.crsSelected.connect(self.crs_selected)

    def crs_selected(self):
        crs = self.proj_selector.crs()
        if crs.isGeographic():
            msgBox = QMessageBox()
            msgBox.setText("Warning: You have selected a geographic coordinate system. Consider choosing a projected coordinate system for better performance.")
            msgBox.exec()
        self.setField('crs', self.proj_selector.crs())
        self.completeChanged.emit()

    def isComplete(self):
        return self.proj_selector.crs().isValid()


class Page4(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.iface = self.parent.iface

        self.setTitle('Define Spatial Extent')
        self.setSubTitle('Choose from the options to define the spatial extent of your project.')

        self.section_title_font = QtGui.QFont()
        self.section_title_font.setFamily("Ubuntu Mono")
        self.section_title_font.setPointSize(14)
        self.section_title_font.setBold(True)
        self.section_title_font.setWeight(75)

        self.drawRectButton = QPushButton(self)
        self.drawRectButton.setText('Draw Rectangle')
        self.drawRectButton.clicked.connect(self.drawRect)
        self.drawRectButton.setToolTip('Click and pull to create a rectangle to define bounds')

        self.drawPolyButton = QPushButton(self)
        self.drawPolyButton.setText('Draw Polygon')
        self.drawPolyButton.clicked.connect(self.drawPoly)
        self.drawPolyButton.setToolTip('Click points on the canvas to create a polygon to define bounds')

        self.captureButton = QPushButton(self)
        self.captureButton.setText('Capture Current Extent')
        self.captureButton.clicked.connect(self.capture_canvas_extent)
        self.captureButton.setToolTip('Click points on the canvas to create a polygon to define bounds')

        label0 = QLabel('Option 1: Use the Canvas')
        label1 = QLabel('Option 2: Use a Loaded Layer')
        label0.setFont(self.section_title_font)
        label1.setFont(self.section_title_font)

        self.selectfromLayerBox = QgsMapLayerComboBox(self)
        # TODO: Figure out how to filter out TileServer or WMS files
        self.selectfromLayerBox.setFilters(QgsMapLayerProxyModel.RasterLayer | QgsMapLayerProxyModel.VectorLayer)
        self.selectfromLayerBox.allowEmptyLayer()
        self.selectfromLayerBox.setCurrentIndex(-1)

        self.selectfromLayerBox.setPlaceholderText('Choose Layer...')
        # self.selectfromLayerBox.setCurrentIndex(0)
        self.selectfromLayerBox.setToolTip('Uses the rectangular extent of layer to define bounds')


        self.useSelectedFeatureCheck = QCheckBox(self)
        self.useSelectedFeatureCheck.setText("Use Selected Feature")
        self.useSelectedFeatureCheck.setToolTip('Will only consider the selected feature for determining extent')

        self.process_layerBox = QPushButton()
        self.process_layerBox.setText('Capture From Selected Layer')
        self.process_layerBox.clicked.connect(self.get_extent_from_LayerComboBox)
        self.process_layerBox.setToolTip('Will pull the geometry from the selected layer to define bounds')

        self.ExtentSourceText = QLabel(self)
        self.ExtentSourceText.setText('Extent Not Yet Defined')

        self.DeterminedExtentText = QTextBrowser()
        self.DeterminedExtentText.setReadOnly(True)

        # self.DeterminedExtentText = QLabel(self)
        # self.DeterminedExtentText.setText('')

        layout = QGridLayout()

        layout.addWidget(label0, 0, 0)
        layout.addWidget(self.drawRectButton, 1, 0)
        layout.addWidget(self.drawPolyButton, 1, 1)
        layout.addWidget(self.captureButton, 1, 2)

        # layout.setRowStretch(2, 1)
        layout.addWidget(QLabel(""), 2, 0)

        layout.addWidget(label1, 3, 0)
        layout.addWidget(self.selectfromLayerBox, 4, 0)
        layout.addWidget(self.useSelectedFeatureCheck, 4, 1)
        layout.addWidget(self.process_layerBox, 5, 0, 1, 2)

        # layout.setRowStretch(6, 1)
        layout.addWidget(QLabel(""), 6, 0)
        layout.addWidget(QLabel(""), 7, 0)
        layout.addWidget(self.ExtentSourceText, 8, 0)
        layout.addWidget(self.DeterminedExtentText, 9, 0)
        self.setLayout(layout)

        self.registerField("DeterminedExtentText*", self.DeterminedExtentText, "toPlainText", self.DeterminedExtentText.textChanged)
        self.DeterminedExtentText.textChanged.connect(self.onTextChange)

    def initializePage(self):
        # Todo: It would be nice if the previous page disappeared before this came up
        super().initializePage()
        if QgsProject.instance().count() == 0:
            popup = AddLayerToProject(self)
            popup.exec()


    def capture_canvas_extent(self):
        self.crs_epsg = QgsProject.instance().crs().authid()
        bb = self.parent.parent.canvas.extent()
        bb.asWktCoordinates()
        bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
        shapelyBox = box(*bbc)
        self.parent.extent_gdf = gpd.GeoDataFrame(geometry=[shapelyBox], crs=self.crs_epsg)
        if self.parent.extent_gdf.crs.to_string() != self.field("crs").authid():
            self.parent.extent_gdf.to_crs(self.field("crs").authid(), inplace=True)
        geotext = self.parent.extent_gdf.geometry.to_string()
        self.DeterminedExtentText.setText(geotext)
        self.ExtentSourceText.setText('Bounds Pulled From Canvas Extent')
        self.parent.bounds = self.parent.extent_gdf.total_bounds

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
            self.parent.extent_gdf = gpd.GeoDataFrame(geometry=[shapely_poly], crs=self.crs_epsg)
            if self.parent.extent_gdf.crs.to_string() != self.field("crs").authid():
                self.parent.extent_gdf.to_crs(self.field("crs").authid(), inplace=True)
            self.ExtentSourceText.setText('Bounds And Geometry Pulled From Selected Features')
        else:
            self.parent.extent_gdf = gpd.GeoDataFrame(geometry=[shapelyBox], crs=self.crs_epsg)
            if self.parent.extent_gdf.crs.to_string() != self.field("crs").authid():
                self.parent.extent_gdf.to_crs(self.field("crs").authid(), inplace=True)
            self.ExtentSourceText.setText('Bounds Pulled From Selected Layer Extent')
        geotext = self.parent.extent_gdf.geometry.to_string()
        self.DeterminedExtentText.setText(geotext)
        self.parent.bounds = self.parent.extent_gdf.total_bounds

    def drawRect(self):
        self.c = self.parent.parent.canvas
        self.RectTool = RectangleMapTool(self.c)
        self.c.setMapTool(self.RectTool)
        self.RectTool.rect_created.connect(self.captureRect)

    def captureRect(self):
        bb = self.RectTool.rectangle()
        self.crs_epsg = self.parent.parent.canvas.mapSettings().destinationCrs().authid()
        bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
        self.parent.extent_gdf = gpd.GeoDataFrame(geometry=[box(*bbc)], crs=self.crs_epsg)
        if self.parent.extent_gdf.crs.to_string() != self.field("crs").authid():
            self.parent.extent_gdf.to_crs(self.field("crs").authid(), inplace=True)
        geotext = self.parent.extent_gdf.geometry.to_string()
        self.DeterminedExtentText.setText(geotext)
        self.ExtentSourceText.setText('Bounds Drawn From Rectangle')
        self.parent.bounds = self.parent.extent_gdf.total_bounds

    def drawPoly(self):
        self.c = self.parent.parent.canvas
        self.PolyTool = PolygonMapTool(self.c)
        self.c.setMapTool(self.PolyTool)
        self.PolyTool.poly_created.connect(self.capturePoly)

    def capturePoly(self):
        poly = self.PolyTool.geometry()
        self.crs_epsg = self.parent.parent.canvas.mapSettings().destinationCrs().authid()
        wkt = poly.asWkt()
        shapely_geom = loads(wkt)
        self.parent.extent_gdf = gpd.GeoDataFrame(geometry=[list(shapely_geom.geoms)[0]], crs=self.crs_epsg)
        if self.parent.extent_gdf.crs.to_string() != self.field("crs").authid():
            self.parent.extent_gdf.to_crs(self.field("crs").authid(), inplace=True)
        geotext = self.parent.extent_gdf.geometry.to_string()
        self.DeterminedExtentText.setText(geotext)
        self.ExtentSourceText.setText('Bounds Drawn From Polygon')
        self.parent.bounds = self.parent.extent_gdf.total_bounds

    def onTextChange(self):
        self.setField("DeterminedExtentText", self.DeterminedExtentText.toPlainText())

    def isComplete(self):
        return bool(self.DeterminedExtentText.toPlainText())


class Page5(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.iface = self.parent.iface
        self.setTitle('Define the spatial resolution for the project and add an optinal buffer')
        self.setSubTitle('The spatial resolution will affect the memory requirements for the raster data'
                         'and geoprocessing times.')

        self.pixel_size = QSpinBox()
        self.pixel_size.setRange(1, 10000)
        self.pixel_size.setSingleStep(50)
        self.pixel_size.setValue(100)
        self.pixel_size.valueChanged.connect(self.calc_memory_allocation)

        self.buffer_distance = QSpinBox()
        self.buffer_distance.setRange(0, 10000)
        self.buffer_distance.setSingleStep(50)
        # self.buffer_distance.setValue(0)

        self.unit_label = QLabel()
        self.approx_size_label = QLabel()

        layout = QGridLayout()
        layout.addWidget(self.unit_label, 0, 0)
        layout.addWidget(QLabel(""), 1, 0)
        layout.addWidget(QLabel('Pixel Size'), 2, 0)
        layout.addWidget(self.pixel_size, 2, 1)
        layout.addWidget(QLabel('Buffer Distance (Optional)'), 3, 0)
        layout.addWidget(self.buffer_distance, 3, 1)
        layout.addWidget(QLabel(""), 4, 0)
        layout.addWidget(self.approx_size_label, 5, 0)

        self.setLayout(layout)

        self.registerField("pixel_size", self.pixel_size)
        self.registerField("buffer_distance", self.buffer_distance)

    def initializePage(self):
        # turn off rectangle or polygon selection from previous page if present
        self.iface.actionPan().trigger()
        crs = self.field("crs")
        linear_unit = QgsUnitTypes.encodeUnit(crs.mapUnits())
        self.unit_label.setText(f"Based on the CRS selected the values are in: {linear_unit}")
        self.calc_memory_allocation()
        super().initializePage()


    def calc_memory_allocation(self):
        bounds = self.parent.bounds
        pixel_size = self.pixel_size.value()
        coord_west, coord_south, coord_east, coord_north = bounds[0], bounds[1], bounds[2], bounds[3]

        raster_width = math.ceil(abs(coord_west - coord_east) / pixel_size)
        raster_height = math.ceil(abs(coord_north - coord_south) / pixel_size)

        bytesize = raster_width * raster_height * 4
        statement = f"Each layer will be approximately {int(round(bytesize * 0.000001))} MB"
        self.approx_size_label.setText(statement)
        # only for dev. will be deleted
        print(f"Bounds: {bounds}")
        print(f"raster width: {raster_width}")
        print(f"raster height: {raster_height}")
        print(statement)




