from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from statmagic_backend.dev.beak_som_workflow import *

from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer, QFileInfo
from qgis.gui import QgsProjectionSelectionWidget, QgsExtentWidget
from qgis.core import QgsRasterLayer, QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsCoordinateTransformContext


from .TabBase import TabBase
from ..gui_helpers import *


class BeakTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Beak")
        self.parent = parent
        self.iface = self.parent.iface

        ##### TOP FRAME #####
        topFrame, topLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)

        topFrameLabel = addLabel(topLayout, "INPUT / OUTPUT PATHS")
        makeLabelBig(topFrameLabel)

        topFormLayout = QtWidgets.QFormLayout()

        # we need objects that don't have a layout yet, so don't use the helpers
        self.numericalPath = QgsFileWidget()
        self.categoricalPath = QgsFileWidget()
        self.outputPath = QgsFileWidget()

        self.numericalPath.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
        self.categoricalPath.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
        self.outputPath.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)

        addFormItem(topFormLayout, "Path to Numerical Data:", self.numericalPath)
        addFormItem(topFormLayout, "Path to Categorical Data:", self.categoricalPath)
        addFormItem(topFormLayout, "Output Path:", self.outputPath)

        addWidgetFromLayoutAndAddToParent(topFormLayout, topFrame)

        addToParentLayout(topFrame)

        ##### MIDDLE FRAME #####
        middleFrame, middleLayout = addFrame(self, "Grid", "Panel", "Sunken", 3)

        middleFrameLabel = addLabel(middleLayout, "SOM ARGUMENTS", gridPos=(0,0,1,3))
        makeLabelBig(middleFrameLabel)

        addLabel(middleLayout, "Dimensions of Generated SOM:", gridPos=(1,0))

        self.som_x = addSpinBoxToGrid(middleFrame, "X", value=30, min=1, max=100, gridPos=(2,0))
        self.som_y = addSpinBoxToGrid(middleFrame, "Y", value=30, min=1, max=100, gridPos=(3,0))
        self.epochs = addSpinBoxToGrid(middleFrame, "# of epochs to run:", value=10, min=10, max=100, step=10, gridPos=(4,0))

        kmeansFormLayout = QtWidgets.QFormLayout()

        self.kmeansCheckBox = addCheckboxToForm(kmeansFormLayout, "Run k-means clustering", isChecked=True)
        self.kmeans_init = addSpinBoxToForm(kmeansFormLayout, "# of Initializations:", value=5, min=1, max=10)
        self.kmeans_min = addSpinBoxToForm(kmeansFormLayout, "Minimum # of k-means clusters:", value=11, min=1, max=100)
        self.kmeans_max = addSpinBoxToForm(kmeansFormLayout, "Maximum # of k-means clusters:", value=12, min=1, max=100)

        addWidgetFromLayoutAndAddToParent(kmeansFormLayout, middleFrame, gridPos=(1,1,4,2))

        miscFormLayout = QtWidgets.QFormLayout()

        self.neighborhood = addComboBoxToForm(miscFormLayout, "Shape of the Neighborhood Function:", ["gaussian", "bubble"])
        self.std_coeff = addSpinBoxToForm(miscFormLayout, "Coefficient in the Gaussian Neighborhood Function:", dtype=float, value=0.5, min=0, max=1, step=0.1)
        self.maptype = addComboBoxToForm(miscFormLayout, "Type of SOM:", ["toroid", "sheet"])
        # TODO: translate this line into a gui element
        # args.initialcodebook = None  # File path of initial codebook, 2D numpy.array of float32.
        self.radius0 = addSpinBoxToForm(miscFormLayout, "Initial Size of the Neighborhood:", value=0, min=0, max=10)
        self.radiusN = addSpinBoxToForm(miscFormLayout, "Final Size of the Neighborhood:", value=1, min=1, max=10)
        self.radiuscooling = addComboBoxToForm(miscFormLayout, "Function Defining Decrease in Neighborhood Size:", ["linear", "exponential"])
        self.scalecooling = addComboBoxToForm(miscFormLayout, "Function Defining Decrease in Learning Scale:", ["linear", "exponential"])
        self.scale0 = addSpinBoxToForm(miscFormLayout, "Initial Learning Rate:", dtype=float, value=0.1, min=0, max=1, step=0.01)
        self.scale0 = addSpinBoxToForm(miscFormLayout, "Final Learning Rate:", dtype=float, value=0.01, min=0, max=1, step=0.01)
        self.initialization = addComboBoxToForm(miscFormLayout, "Type of SOM Initialization:", ["random", "pca"])
        self.gridtype = addComboBoxToForm(miscFormLayout, "Type of SOM Grid:", ["hexagonal", "rectangular"])

        addWidgetFromLayoutAndAddToParent(miscFormLayout, middleFrame, gridPos=(5, 0, 11, 3))

        addToParentLayout(middleFrame)

        ##### BOTTOM FRAME #####
        bottomFrame, bottomLayout = addFrame(self, "HBox", "StyledPanel", "Raised", 3)

        self.run_SOM_button = addButton(bottomFrame, "Run SOM Workflow", self.run_som_workflow)
        self.plot_SOM_results = addButton(bottomFrame, "Plot SOM Results", self.plot_som_results)

        addToParentLayout(bottomFrame)

    def run_som_workflow(self):
        pass

    def plot_som_results(self):
        pass