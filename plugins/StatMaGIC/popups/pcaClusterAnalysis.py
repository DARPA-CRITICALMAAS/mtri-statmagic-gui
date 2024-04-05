from qgis.PyQt.QtWidgets import QDialog, QLineEdit, QTextEdit
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.gui import QgsMapLayerComboBox, QgsRasterBandComboBox, QgsFieldComboBox, QgsCheckableComboBox
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QGridLayout, QFormLayout, QLabel, QPushButton, QComboBox, QSpinBox

from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject, QgsMapLayerProxyModel, QgsMapLayer
from qgis.core import QgsPoint, QgsCoordinateTransform

from pathlib import Path
import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock

import rasterio as rio
from rasterio import RasterioIOError
from rasterio.windows import Window, from_bounds
import numpy as np
from shapely import box
import pandas as pd
import geopandas as gpd

import logging
logger = logging.getLogger("statmagic_gui")


class PCAClusterQtPlot(QDialog):
    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        super(PCAClusterQtPlot, self).__init__(parent)
        QDialog.setWindowTitle(self, "PCA and Cluster Analysis")

        logger.debug("Create layout")
        self.layout = QGridLayout(self)
        self.area = DockArea()

        logger.debug("Create plot dock")
        self.plot_dock = Dock("PCA and Cluster Analysis", size=(1000, 600))
        self.area.addDock(self.plot_dock, 'left')

        logger.debug("Create parameter dock")
        self.param_dock = Dock("Parameters", size=(200, 600))
        self.area.addDock(self.param_dock, 'right')

        logger.debug("add area to layout")
        self.layout.addWidget(self.area, 0, 0)
        logger.debug("set layout")
        self.setLayout(self.layout)
        logger.debug("Done")

        ### User parameters
        # Pick layer to perform analysis on
        self.layerComboBoxLabel = QLabel("Select Layer to Analyze")
        self.layerComboBox = QgsMapLayerComboBox(self)
        self.layerComboBox.setShowCrs(True)

        # Choose features to analyze
        self.featureComboBoxLabel = QLabel("Select Features to Analyze")
        self.featureComboBox = QgsCheckableComboBox(self)
        self.set_feature_combo_box_items(self.layerComboBox.currentLayer())
        self.layerComboBox.layerChanged.connect(self.set_feature_combo_box_items)

        ### Add plot areas
        self.plotsWidget = pg.GraphicsLayoutWidget(show=True, title="PCA and Cluster Analysis")
        self.plotsWidget.resize(1000, 600)
        self.p1 = self.plotsWidget.addPlot(title="PCA1 va PC2")
        self.p2 = self.plotsWidget.addPlot(title="PCA1 va PC2")
        self.plotsWidget.nextRow()
        self.p3 = self.plotsWidget.addPlot(title="PCA1 va PC2")
        self.p4 = self.plotsWidget.addPlot(title="PCA1 va PC2")

        self.p1.plot(np.random.normal(size=100), pen=(255, 0, 0))
        self.p2.plot(np.random.normal(size=100), pen=(0, 255, 0))
        self.p3.plot(np.random.normal(size=100), pen=(0, 0, 255))
        self.p4.plot(np.random.normal(size=100), pen=(255, 255, 0))

        for p in [self.p1, self.p2, self.p3, self.p4]:
            p.showGrid(x=True, y=True)
            p.setLabel('left', 'PCA1')
            p.setLabel('bottom', 'PCA2')
            p.addItem(pg.InfiniteLine(angle=90, movable=False), ignoreBounds=True)
            p.addItem(pg.InfiniteLine(angle=0, movable=False), ignoreBounds=True)

        # Create for input panel
        self.input_layout = QFormLayout()
        self.input_layout.addRow(self.layerComboBoxLabel, self.layerComboBox)
        self.input_layout.addRow(self.featureComboBoxLabel, self.featureComboBox)

        # Populate dialog layout
        self.layout = QGridLayout(self)
        self.layout.addWidget(self.plotsWidget, 0, 0)
        self.layout.addLayout(self.input_layout, 0, 1)
        self.setLayout(self.layout)

    def set_feature_combo_box_items(self, layer: QgsMapLayer):
        logger.debug(layer, layer.type())
        self.featureComboBox.clear()
        if layer.type() == QgsMapLayer.VectorLayer:
            self.featureComboBox.addItems([field.name() for field in layer.fields() if field.typeName() in ["Integer", "Real"]])
        elif layer.type() == QgsMapLayer.RasterLayer:
            self.featureComboBox.addItems([str(i) for i in range(1, layer.bandCount() + 1)])
        else:
            self.featureComboBox.clear()

