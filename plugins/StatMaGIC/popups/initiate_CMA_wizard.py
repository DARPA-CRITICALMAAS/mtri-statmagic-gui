from PyQt5.QtWidgets import QPushButton, QCheckBox, QWizard,QSpinBox, QWizardPage, QLabel, QLineEdit, QVBoxLayout, QGridLayout, QTextEdit, QMessageBox
from qgis.gui import QgsProjectionSelectionTreeWidget, QgsFileWidget, QgsMapLayerComboBox
from PyQt5 import QtCore
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsPoint, Qgis, QgsFeature, QgsGeometry, QgsDistanceArea
from shapely.geometry import box
from shapely.wkt import loads
import geopandas as gpd
from ..popups.grab_polygon import PolygonMapTool
from ..popups.grab_rectangle import RectangleMapTool
# modified from https://north-road.com/2018/03/09/implementing-an-in-house-new-project-wizard-for-qgis/

# icon_path = '/home/nyall/nr_logo.png'

'''
Theres still a lot to figure out here but the workflow is well defined. Don't expect much to work
at this point. Particulaly the extent defintion start. It's mostly just getting the GUI elements and the QWizard Widget setup. 

I expect there will need to be a bit of setup for doing parent type stuff to access the canvas for 
capturing and the canvas drawing tools. 

You'll see there's a bit of stuff commented out for having fields required before passing on, and an example
of it working for the projection selection. 

For Cleanliness it might be better to make each page it's own file and import as well

Also need help on unpacking all hte defined inputs back into Start_Tab to run the initiate CMA function

'''

class ProjectWizard(QWizard):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.addPage(Page1(self))
        self.addPage(Page2(self))
        self.addPage(Page3(self))
        self.addPage(Page4(self))
        self.addPage(Page5(self))
        self.setWindowTitle("Initiate CMA Wizard")

        # when the "finish" button on the last page gets clicked,
        # call the method in StartTab that processes the collected information
        self.button(QWizard.FinishButton).clicked.connect(self.parent.initiate_CMA_workflow)

    def reject(self):
        # TODO: clean up variables on cancel here

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

        layout = QGridLayout()
        layout.addWidget(QLabel('Select Directory'), 0, 0)
        layout.addWidget(self.proj_dir_input, 0, 1)

        self.setLayout(layout)

        self.registerField("input_path", self.proj_dir_input)

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
        self.setTitle('Define Spatial Extent')
        self.setSubTitle('Choose from the options to define the spatial extent of your project.')


        self.drawRectButton = QPushButton(self)
        self.drawRectButton.setText('Draw Rectangle')
        self.drawRectButton.clicked.connect(self.drawRect)
        self.drawRectButton.setToolTip('Click and pull to create a rectangle to define bounds')

        self.drawPolyButton = QPushButton(self)
        self.drawPolyButton.setText('Draw Polygon')
        self.drawPolyButton.clicked.connect(self.drawPoly)
        self.drawPolyButton.setToolTip('Click points on the canvas to create a polygon to define bounds')

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

        self.DeterminedExtentText = QLineEdit(self)

        # layout = QVBoxLayout()
        layout = QGridLayout()
        layout.addWidget(QLabel('Draw on the canvas'), 0, 0)
        # RESUME HERE FOR ADDING A PRETTIER LAYOUT\
        # Think about having a button for adding a few baselayers as well
        layout.addWidget(self.drawRectButton)
        layout.addWidget(self.drawPolyButton)
        layout.addWidget(self.captureButton)
        layout.addWidget(self.label0)
        layout.addWidget(self.selectfromLayerBox)
        layout.addWidget(label1)
        layout.addWidget(self.useSelectedFeatureCheck)
        layout.addWidget(self.process_layerBox)
        layout.addWidget(label2)
        layout.addWidget(self.fileInput)
        layout.addWidget(self.DeterminedExtentText)

        self.setLayout(layout)

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
            # TODO: This should be backend?
            shapely_poly = loads(sel.geometry().asWkt())
            self.extent_gdf = gpd.GeoDataFrame(geometry=[shapely_poly], crs=self.crs_epsg)
            self.DeterminedExtentText.setText('Bounds And Geometry Pulled From Selected Features')
        else:
            self.extent_gdf = gpd.GeoDataFrame(geometry=[shapelyBox], crs=self.crs_epsg)
            self.DeterminedExtentText.setText('Bounds Pulled From Selected Layer Extent')


    def drawRect(self):
        self.c = self.parent.canvas
        self.RectTool = RectangleMapTool(self.c)
        self.c.setMapTool(self.RectTool)

    def drawPoly(self):
        self.c = self.parent.canvas
        self.PolyTool = PolygonMapTool(self.c)
        self.c.setMapTool(self.PolyTool)

    def returnExtent(self):
        # self.parent.extent_gdf = self.extent_gdf
        # self.parent.src_crs = self.crs_epsg
        # self.close()
        pass


class Page5(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setTitle('Define the spatial resolution for the project and add an optinal buffer')
        self.setSubTitle('The spatial resolution will affect the memory requirements for the raster data'
                         'and geoprocessing times.')

        self.pixel_size = QSpinBox()
        self.pixel_size.setRange(1, 10000)
        self.pixel_size.setSingleStep(50)
        self.pixel_size.setValue(100)

        self.buffer_distance = QSpinBox()
        self.buffer_distance.setRange(0, 10000)
        self.buffer_distance.setSingleStep(50)
        self.buffer_distance.setValue(0)

        layout = QGridLayout()
        # Todo: add units from crs.linearUnit()
        layout.addWidget(QLabel('Pixel Size ____'), 0, 0)
        layout.addWidget(self.pixel_size, 0, 1)
        layout.addWidget(QLabel('Buffer Distance'), 1, 0)
        layout.addWidget(self.buffer_distance, 1, 1)

        # Todo: add some type of dynamic layer size (mb) calculator in here

        self.setLayout(layout)

        self.registerField("pixel_size", self.pixel_size)
        self.registerField("buffer_distance", self.buffer_distance)
