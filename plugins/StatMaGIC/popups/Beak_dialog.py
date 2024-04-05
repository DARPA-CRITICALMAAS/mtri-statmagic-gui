from pathlib import Path
from qgis.PyQt.QtWidgets import QDialog
import geopandas as gpd
from PyQt5.QtWidgets import QMessageBox
from shapely.geometry import box


try:
    from statmagic_backend.dev.beak_som_workflow import *
    SOMOCLU_FAILED = False
except ImportError:
    SOMOCLU_FAILED = True

from statmagic_backend.dev.match_stack_raster_tools import split_cube

from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer, QFileInfo
from qgis.gui import QgsProjectionSelectionWidget, QgsExtentWidget
from qgis.core import QgsRasterLayer, QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsCoordinateTransformContext

from ..gui_helpers import *

import logging
logger = logging.getLogger("statmagic_gui")

class Beak_PopUp_Menu(QDialog):

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        super(Beak_PopUp_Menu, self).__init__(parent)
        QDialog.setWindowTitle(self, "Beak Modelling Menu")
        self.setLayout(QtWidgets.QVBoxLayout())

        ##### TOP FRAME #####
        topFrame, topLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)

        topFrameLabel = addLabel(topLayout, "INPUT / OUTPUT PATHS")
        makeLabelBig(topFrameLabel)

        topFormLayout = QtWidgets.QFormLayout()

        # we need objects that don't have a layout yet, so don't use the helpers
        self.numericalPath = QgsFileWidget()
        self.categoricalPath = QgsFileWidget()
        self.outputPath = QgsFileWidget()

        # self.numericalPath.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
        # self.categoricalPath.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
        self.outputPath.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)

        addFormItem(topFormLayout, "Path to Numerical Data:", self.numericalPath)
        addFormItem(topFormLayout, "Path to Categorical Data:", self.categoricalPath)
        addFormItem(topFormLayout, "Output Path:", self.outputPath)

        addWidgetFromLayoutAndAddToParent(topFormLayout, topFrame)

        addToParentLayout(topFrame)

        ##### MIDDLE FRAME #####
        middleFrame, middleLayout = addFrame(self, "Grid", "Panel", "Sunken", 3)

        middleFrameLabel = addLabel(middleLayout, "SOM ARGUMENTS", gridPos=(0, 0, 1, 3))
        makeLabelBig(middleFrameLabel)

        addLabel(middleLayout, "Dimensions of Generated SOM:", gridPos=(1, 0))

        self.som_x = addSpinBoxToGrid(middleFrame, "X", value=30, min=1, max=100, gridPos=(2, 0))
        self.som_y = addSpinBoxToGrid(middleFrame, "Y", value=30, min=1, max=100, gridPos=(3, 0))
        self.epochs = addSpinBoxToGrid(middleFrame, "# of epochs to run:", value=10, min=1, max=100, step=10,
                                       gridPos=(4, 0))

        kmeansFormLayout = QtWidgets.QFormLayout()

        self.kmeansCheckBox = addCheckboxToForm(kmeansFormLayout, "Run k-means clustering", isChecked=True)
        self.kmeans_init = addSpinBoxToForm(kmeansFormLayout, "# of Initializations:", value=5, min=1, max=10)
        self.kmeans_min = addSpinBoxToForm(kmeansFormLayout, "Minimum # of k-means clusters:", value=11, min=1, max=100)
        self.kmeans_max = addSpinBoxToForm(kmeansFormLayout, "Maximum # of k-means clusters:", value=12, min=1, max=100)

        addWidgetFromLayoutAndAddToParent(kmeansFormLayout, middleFrame, gridPos=(1, 1, 4, 2))

        miscFormLayout = QtWidgets.QFormLayout()

        self.neighborhood = addComboBoxToForm(miscFormLayout, "Shape of the Neighborhood Function:",
                                              ["gaussian", "bubble"])
        self.std_coeff = addSpinBoxToForm(miscFormLayout, "Coefficient in the Gaussian Neighborhood Function:",
                                          dtype=float, value=0.5, min=0, max=1, step=0.1)
        self.maptype = addComboBoxToForm(miscFormLayout, "Type of SOM:", ["toroid", "sheet"])
        # TODO: translate this line into a gui element
        # args.initialcodebook = None  # File path of initial codebook, 2D numpy.array of float32.
        self.radius0 = addSpinBoxToForm(miscFormLayout, "Initial Size of the Neighborhood:", value=0, min=0, max=10)
        self.radiusN = addSpinBoxToForm(miscFormLayout, "Final Size of the Neighborhood:", value=1, min=1, max=10)
        self.radiuscooling = addComboBoxToForm(miscFormLayout, "Function Defining Decrease in Neighborhood Size:",
                                               ["linear", "exponential"])
        self.scalecooling = addComboBoxToForm(miscFormLayout, "Function Defining Decrease in Learning Scale:",
                                              ["linear", "exponential"])
        self.scale0 = addSpinBoxToForm(miscFormLayout, "Initial Learning Rate:", dtype=float, value=0.1, min=0, max=1,
                                       step=0.01)
        self.scaleN = addSpinBoxToForm(miscFormLayout, "Final Learning Rate:", dtype=float, value=0.01, min=0, max=1,
                                       step=0.01)
        self.initialization = addComboBoxToForm(miscFormLayout, "Type of SOM Initialization:", ["random", "pca"])
        self.gridtype = addComboBoxToForm(miscFormLayout, "Type of SOM Grid:", ["hexagonal", "rectangular"])

        addWidgetFromLayoutAndAddToParent(miscFormLayout, middleFrame, gridPos=(5, 0, 11, 3))

        addToParentLayout(middleFrame)

        ##### BOTTOM FRAME #####
        bottomFrame, bottomLayout = addFrame(self, "HBox", "StyledPanel", "Raised", 3)

        self.run_SOM_button = addButton(bottomFrame, "Run SOM Workflow", self.run_som_workflow)
        self.plot_SOM_results = addButton(bottomFrame, "Plot SOM Results", self.plot_som_results)

        addToParentLayout(bottomFrame)

    def setup_paths(self):
        self.numerical_path = self.numericalPath.filePath()
        input_files = split_cube(self.numerical_path, standardize=True)
        self.input_files = ",".join(input_files)
        self.categorical_path = self.categoricalPath.filePath()
        self.output_folder = self.outputPath.filePath()
        self.output_file_somspace = str(Path(self.output_folder) / "result_som.txt")
        self.outgeofile = str(Path(self.output_folder) / "result_geo.txt")
        # (
        #     self.input_files,
        #     self.output_file_somspace,
        #     self.outgeofile
        # ) = prepare_args(self.numerical_path, self.categorical_path, self.output_folder)

    def run_som_workflow(self):
        if SOMOCLU_FAILED:
            msgBox = QMessageBox()
            msgBox.setText("The package <pre>somoclu</pre> is not installed on your system. "
                           "Please install it before running the Beak tab.")
            msgBox.exec()
            return
        self.setup_paths()
        som_args = {
            "input_file": self.input_files,
            "geotiff_input": self.input_files,      # geotiff_input files, separated by comma
            "output_folder": self.output_folder,
            "som_x": self.som_x.value(),
            "som_y": self.som_y.value(),
            "epochs": self.epochs.value(),
            "kmeans": str(self.kmeansCheckBox.isChecked()).lower(),
            "kmeans_init": self.kmeans_init.value(),
            "kmeans_min": self.kmeans_min.value(),
            "kmeans_max": self.kmeans_max.value(),
            "neighborhood": self.neighborhood.currentText(),
            "std_coeff": self.std_coeff.value(),
            "maptype": self.maptype.currentText(),
            # "initialcodebook": None,
            "radius0": self.radius0.value(),
            "radiusN": self.radiusN.value(),
            "radiuscooling": self.radiuscooling.currentText(),
            "scalecooling": self.scalecooling.currentText(),
            "scale0": self.scale0.value(),
            "scaleN": self.scaleN.value(),
            "initialization": self.initialization.currentText(),
            "gridtype": self.gridtype.currentText(),
            "output_file_somspace": self.output_file_somspace,
            # Additional optional parameters below:
            "outgeofile": self.outgeofile,
            "output_file_geospace": self.outgeofile
        }
        beak_som_workflow(som_args)

    def plot_som_results(self):
        if SOMOCLU_FAILED:
            msgBox = QMessageBox()
            msgBox.setText("The package <pre>somoclu</pre> is not installed on your system. "
                           "Please install it before running the Beak tab.")
            msgBox.exec()
            return
        self.setup_paths()
        # TODO: make some kind of GUI for the ones that are still hardcoded
        plot_args = {
            "som_x": self.som_x.value(),
            "som_y": self.som_y.value(),
            "input_file": self.input_files,
            "outsomfile": self.output_file_somspace,
            "dir": self.output_folder,
            "grid_type": 'rectangular',  # grid type (square or hexa), (rectangular or hexagonal)
            "redraw": 'true',
            # whether to draw all plots, or only those required for clustering (true: draw all. false:draw only for clustering).
            "outgeofile": self.outgeofile,
            "dataType": 'grid',  # Data type (scatter or grid)
            "noDataValue": '-9999'  # noData value
        }
        plot_som_results(plot_args)
