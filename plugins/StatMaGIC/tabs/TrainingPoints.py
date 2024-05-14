from pathlib import Path

import geopandas as gpd
from osgeo import gdal
import pandas as pd
import rasterio as rio
from sklearn import svm
from sklearn.ensemble import IsolationForest
import tempfile
from pathlib import Path
from rasterio import features
import numpy as np
from shapely.geometry import shape
from ..layerops import addVectorLayer

from PyQt5 import QtWidgets
from qgis.core import QgsProject, QgsMapLayerProxyModel, QgsFieldProxyModel
from PyQt5.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QSpinBox, QCheckBox, QPushButton, \
    QDoubleSpinBox, QFormLayout, QMessageBox

from qgis.core import QgsProject, QgsVectorLayer


from statmagic_backend.dev.rasterize_training_data import training_vector_rasterize
from statmagic_backend.extract.raster import extractBands, extractBandsInBounds, getCanvasRasterDict, getFullRasterDict
from statmagic_backend.geo.transform import boundingBoxToOffsets, geotFromOffsets
from ..widgets.collapsible_box import CollapsibleBox

from .TabBase import TabBase
from ..fileops import gdalSave, parse_vector_source
from ..gui_helpers import *
from ..layerops import addGreyScaleLayer, apply_model_to_array, dataframeFromSampledPoints, dataframFromSampledPolys
from ..plotting import makePCAplot
from ..popups.SRI_dialog import SRI_PopUp_Menu
from ..popups.Beak_dialog import Beak_PopUp_Menu

import logging
logger = logging.getLogger("statmagic_gui")


class TrainingPointsTab(TabBase):
    def __init__(self, parent, tabWidget, isEnabled=True):
        super().__init__(parent, tabWidget, "Training Points", isEnabled)

        self.parent = parent
        self.iso_forest = None

        topFrame, topGrid = addFrame(self, "Grid", "NoFrame", "Plain", 3)

        label0 = QLabel('Data Raster Layer')
        label1 = QLabel('Training Vector Layer')
        label2 = QLabel('With Selected:    ')
        label3 = QLabel('Add Buffer:')

        # Todo: Add filters and ToolTips on these
        self.training_layer_box = QgsMapLayerComboBox()
        self.training_layer_box.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.training_layer_box.setToolTip('The layer to define the geometry for sampling the raster')

        self.data_raster_box = QgsMapLayerComboBox()
        self.data_raster_box.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.data_raster_box.setToolTip('The Raster Layer that will be sampled and predicted on')

        self.training_buffer_box = QSpinBox()
        self.training_buffer_box.setToolTip('Option to add buffer to geometry before sampling. \n '
                                            'if a point geometry the buffer will covert to polygon')

        self.with_selected_training = QCheckBox()
        self.with_selected_training.setToolTip('Will only consider currently selected features for model training')

        self.sample_at_points_button = QPushButton()
        self.sample_at_points_button.setText("Sample DataCube With Training Geometry")
        self.sample_at_points_button.clicked.connect(self.sample_raster_with_training_layer)
        self.sample_at_points_button.setToolTip('Creates an in memory dataframe of the sampled raster values for each '
                                                'in the training layer geometry')

        topGrid.addWidget(label0, 0, 0)
        topGrid.addWidget(self.data_raster_box, 1, 0, 1, 2)
        topGrid.addWidget(label1, 0, 2)
        topGrid.addWidget(self.training_layer_box, 1, 2, 1, 2)
        topGrid.addWidget(label2, 2, 0)
        topGrid.addWidget(self.with_selected_training, 2, 1)
        topGrid.addWidget(label3, 2, 2)
        topGrid.addWidget(self.training_buffer_box, 2, 3)
        topGrid.addWidget(self.sample_at_points_button, 3, 0, 1, 4)

        addToParentLayout(topFrame)

        # ## EDA Tools
        #
        # edaFrame, edaGrid = addFrame(self, "Grid", "Panel", "Sunken", 3)
        #
        # self.sample_at_points_button = QPushButton()
        # self.sample_at_points_button.setText("Sample DataCube With\n Training Geometry")
        # self.sample_at_points_button.clicked.connect(self.sample_raster_with_training_layer)
        #
        # self.pca_plot_button = QPushButton()
        # self.pca_plot_button.setText('Create PCA Plot')
        # self.pca_plot_button.clicked.connect(self.runPCAplot)
        #
        #
        # self.pca_x = QSpinBox()
        # self.pca_x.setValue(1)
        # self.pca_y = QSpinBox()
        # self.pca_y.setValue(2)
        #
        # self.dbscan_button = QPushButton()
        # self.dbsca_eta = QDoubleSpinBox()
        # self.dbscan_min_sampe = QSpinBox()
        #
        # label4 = QLabel('PCA Plot Axis')
        # label5 = QLabel('PCA Plot X Axis')
        # label6 = QLabel('PCA Plot Y Axis')
        # label7 = QLabel('eps')
        # label8 = QLabel('min_samples')
        #
        # edaGrid.addWidget(self.sample_at_points_button, 0, 0, 2, 2)
        # # edaGrid.addWidget(label4, 0, 3)
        # edaGrid.addWidget(label5, 1, 2, 1, 1)
        # edaGrid.addWidget(label6, 2, 2, 1, 1)
        # edaGrid.addWidget(self.pca_x, 1, 3, 1, 1)
        # edaGrid.addWidget(self.pca_y, 2, 3, 1, 1)
        # edaGrid.addWidget(self.pca_plot_button, 0, 4, 2, 1)
        #
        # addToParentLayout(edaFrame)

        ## Modelling Options
        isoFrame, isoLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        isoFrameLabel = addLabel(isoLayout, "Isolation Forest Modeling")
        makeLabelBig(isoFrameLabel)

        modelling_main = QHBoxLayout()

        self.train_iso_button = QPushButton()
        self.train_iso_button.setText("Train Isolation\n Forest")
        self.train_iso_button.clicked.connect(self.train_iso)

        self.pred_iso_button = QPushButton()
        self.pred_iso_button.setText("Predict with \n Isolation Forest")
        self.pred_iso_button.clicked.connect(self.pred_iso)

        self.iso_est_spin = QSpinBox()
        self.iso_est_spin.setValue(100)
        self.iso_est_spin.setRange(50, 1000)
        self.iso_est_spin.setSingleStep(25)
        self.iso_est_spin.setToolTip('The number of base estimators in the ensemble')

        self.iso_contamination_spin = QDoubleSpinBox()
        self.iso_contamination_spin.setRange(0, 0.5)
        self.iso_contamination_spin.setSingleStep(0.05)
        self.iso_contamination_spin.setValue(0.1)
        self.iso_contamination_spin.setToolTip("The amount of contamination of the data set, i.e. the proportion of \n"
                                                "outliers in the data set. Used when fitting to define the threshold \n"
                                                "on the scores of the samples.")

        self.iso_njob_spin = QSpinBox()
        self.iso_njob_spin.setRange(1, 32)
        self.iso_njob_spin.setToolTip("Number of cores to allocate for training and prediction")
        self.full_check = QCheckBox()
        self.full_check.setToolTip("If checked predictions occur on full dataset, unchecked within the canvas extent")

        iso_input_form = QFormLayout()
        addFormItem(iso_input_form, "Number Estimators:", self.iso_est_spin)
        addFormItem(iso_input_form, "Contaimination:", self.iso_contamination_spin)
        addFormItem(iso_input_form, "n jobs:", self.iso_njob_spin)
        addFormItem(iso_input_form, "Predict Full Extent:", self.full_check)

        iso_button_layout = QVBoxLayout()
        iso_button_layout.addWidget(self.train_iso_button)
        iso_button_layout.addWidget(self.pred_iso_button)

        modelling_main.addLayout(iso_input_form)
        modelling_main.addLayout(iso_button_layout)

        isoLayout.addLayout(modelling_main)
        addToParentLayout(isoFrame)

        ##---------- Area for the Beak and SRI tabs ---------------- ##
        ta3Frame, ta3Layout = addFrame(self, "HBox", "Panel", "Sunken", 3)
        # ta3FrameLabel = addLabel(ta3Layout, "TA-3 Modelling Menus")
        # makeLabelBig(ta3FrameLabel)

        self.launch_sri_button = QPushButton()
        self.launch_sri_button.setText("Open SRI Menu")
        self.launch_sri_button.clicked.connect(self.launch_sri)

        self.launch_beak_button = QPushButton()
        self.launch_beak_button.setText("Open Beak Menu")
        self.launch_beak_button.clicked.connect(self.launch_beak)

        ta3Layout.addWidget(self.launch_sri_button)
        ta3Layout.addWidget(self.launch_beak_button)

        addToParentLayout(ta3Frame)

        self.threshold_outputs_box = CollapsibleBox("Create Negative Labels")
        self.negatives_layout = QGridLayout()


        train_layer_label = QLabel('Training Points Layer')
        self.train_layer_select = QgsMapLayerComboBox()
        self.train_layer_select.setFilters(QgsMapLayerProxyModel.VectorLayer)

        prox_layer_label = QLabel('Proximity Layer')
        self.prox_layer_select = QgsMapLayerComboBox()
        self.prox_layer_select.setFilters(QgsMapLayerProxyModel.RasterLayer)

        self.num_samples = QSpinBox()
        self.num_samples.setValue(100)
        self.num_samples.setRange(0, 200000)
        self.num_samples.setSingleStep(25)

        self.neg_label_button = QPushButton()
        self.neg_label_button.setText('Generate Random Negative Labels')
        self.neg_label_button.clicked.connect(self.make_negative_label)

        self.negatives_layout.addWidget(train_layer_label, 0, 0)
        self.negatives_layout.addWidget(prox_layer_label, 0, 1)
        self.negatives_layout.addWidget(self.train_layer_select, 1, 0)
        self.negatives_layout.addWidget(self.prox_layer_select, 1, 1)
        self.negatives_layout.addWidget(self.num_samples, 2, 0)
        self.negatives_layout.addWidget(self.neg_label_button, 2, 1)


        self.threshold_outputs_box.setContentLayout(self.negatives_layout)
        self.tabLayout.addWidget(self.threshold_outputs_box)

    def make_negative_label(self):
        prox_path = self.prox_layer_select.currentLayer().source()
        num_samples = self.num_samples.value()

        # Create an output path
        tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
        # Todo: for some reason the writing as geojson wasn't fully writing out the file.
        # Changed to GPKG
        # tfile1 = tempfile.mkstemp(dir=tfol, suffix='.json', prefix='negative_labels_')
        tfile1 = tempfile.mkstemp(dir=tfol, suffix='.gpkg', prefix='negative_labels_')
        tfile2 = tempfile.mkstemp(dir=tfol, suffix='.tif', prefix='negative_labels_')
        vector_output_file_path = tfile1[1]
        raster_output_file_path = tfile2[1]
        # todo: this seems non ideal. Creating the file just to get the path then delete?
        # I couldn't find a method in tempfile to create just a filename without creating the file
        Path.unlink(vector_output_file_path)
        Path.unlink(raster_output_file_path)

        # Todo: Make a backend function
        raster = rio.open(prox_path)
        arr = raster.read()

        a1 = arr.ravel()
        b = np.arange(0, len(a1))
        probs = a1 / a1.sum(axis=0, keepdims=1)
        samples = np.random.choice(b, size=num_samples, replace=False, p=probs)
        idxs = np.isin(b, samples)

        labels = np.reshape(idxs, arr.shape).astype('uint8')
        labels_prof = raster.profile.copy()
        labels_prof.update({'dtype': 'uint8', 'nodata': 255})

        label_raster = rio.open(raster_output_file_path, 'w', **labels_prof)
        label_raster.write(labels)
        label_raster.close()

        with rio.open(raster_output_file_path) as src:
            shapes = list(rio.features.shapes(src.read(1), transform=src.transform))

            slist = []
            for s, v in shapes:
                if v == 1:
                    slist.append(shape(s))

        points = [s.centroid for s in slist]
        gdf = gpd.GeoDataFrame(geometry=points, crs=src.crs)
        # gdf.to_file(vector_output_file_path, driver='GeoJSON')
        gdf.to_file(vector_output_file_path, driver='GPKG')
        print(vector_output_file_path)

        vlayer = QgsVectorLayer(vector_output_file_path, 'Negative Labels', "ogr")
        QgsProject.instance().addMapLayer(vlayer)


    def sample_raster_with_training_layer(self):
        data_ras = self.data_raster_box.currentLayer()
        logger.debug(data_ras.source())
        selectedLayer = self.training_layer_box.currentLayer()
        withSelected = self.with_selected_training.isChecked()
        buffer = self.training_buffer_box.value()

        if withSelected:
            sel = selectedLayer.selectedFeatures()
        else:
            sel = selectedLayer.getFeatures()
        gdf = gpd.GeoDataFrame.from_features(sel)
        gdf.set_crs(selectedLayer.crs().toWkt(), inplace=True)
        gdf.to_crs(data_ras.crs().toWkt(), inplace=True)
        # TODO: Convert to the CRS of the project if need be.
        if buffer > 0:
            gdf['geometry'] = gdf.geometry.buffer(buffer)
        if gdf.geom_type[0] == 'Point':
            df = dataframeFromSampledPoints(gdf, data_ras.source())
        else:
            df = dataframFromSampledPolys(gdf, data_ras.source())

        self.training_df = df
        print(self.training_df)

    def train_iso(self):
        if self.iso_forest is not None:
            self.iso_forest = None

        n_estimators = self.iso_est_spin.value()
        contaim = self.iso_contamination_spin.value()
        n_job = self.iso_njob_spin.value()

        if not hasattr(self, "training_df"):
            msgBox = QMessageBox()
            msgBox.setText("You must sample your datacube with training geometry "
                           "before training with Isolation Forest.")
            msgBox.exec()
            return

        x_train = self.training_df.to_numpy()
        isofor = IsolationForest(n_estimators=n_estimators, contamination=contaim, n_jobs=n_job)
        isofor.fit(x_train)

        self.iface.messageBar().pushMessage('Isolation Forest Model Fit')
        self.iso_forest = isofor

    def pred_iso(self):
        fullExtent = self.full_check.isChecked()
        data_ras = self.data_raster_box.currentLayer()

        r_ds = gdal.Open(data_ras.source())

        if fullExtent:
            raster_dict = getFullRasterDict(r_ds)
            raster_array = r_ds.ReadAsArray()
        else:
            full_dict = getFullRasterDict(r_ds)
            raster_dict = getCanvasRasterDict(full_dict, self.parent.canvas.extent())
            raster_array = r_ds.ReadAsArray(raster_dict['Xoffset'], raster_dict['Yoffset'],
                                            raster_dict['sizeX'], raster_dict['sizeY'])

        if raster_array is None:
            msgBox = QMessageBox()
            msgBox.setText(f"{data_ras.name()} appears to be an empty raster. "
                           f"Please select a different raster layer.")
            msgBox.exec()
            return

        classout = apply_model_to_array(self.iso_forest, raster_array, raster_dict)

        savedLayer = gdalSave('SVM_Scores', classout.astype('float32'), gdal.GDT_Float32, raster_dict['GeoTransform'],
                              raster_dict['Projection'], float(np.finfo('float32').min))

        root = QgsProject.instance().layerTreeRoot()
        if root.findGroup('IsolationForestOutputs') == None:
            TOCgroup = root.insertGroup(0, 'IsolationForestOutputs')
        else:
            TOCgroup = root.findGroup('IsolationForestOutputs')

        addGreyScaleLayer(savedLayer, "Isolation Forest Output", TOCgroup)

    def trainOneClassSVM(self):
        if self.parent.oneClassSVM is not None:
            self.parent.oneClassSVM = None

        training_df = self.training_df
        x_train = training_df.to_numpy()

        # One class SVM
        # Can add inputs for user defnined parameters later
        kernel = 'rbf'
        nu = 0.5
        gamma = 0.001

        ocsvm = svm.OneClassSVM(nu=nu, kernel=kernel, gamma=gamma)
        ocsvm.fit(x_train)

        self.iface.messageBar().pushMessage('SVM Model Fit')
        self.parent.oneClassSVM = ocsvm

    def runPCAplot(self):
        pca_axis_1 = self.plt_axis_1.value()
        pca_axis_2 = self.plt_axis_2.value()
        pct_data_plot = self.pctdataplotBox.value()
        plotsubVal = int(100 / pct_data_plot)
        data_sel = self.data_sel_box.currentIndex()
        logger.debug(data_sel)
        # TODO: these global variables might not have been defined yet
        if data_sel == 0:
            data_input = self.parent.fullK
        elif data_sel == 1:
            data_input = self.parent.maskK
        elif data_sel == 2:
            data_input = self.parent.trainingK
        else:
            logger.debug('invalid selection')
        if data_input:
            makePCAplot(data_input, pca_axis_1, pca_axis_2, plotsubVal, data_sel)

    def launch_sri(self):
        popup = SRI_PopUp_Menu(self.parent)
        self.sri_menu = popup.show()

    def launch_beak(self):
        popup = Beak_PopUp_Menu(self.parent)
        self.sri_menu = popup.show()

    def add_label_to_grid(self):
        # This should pop up a dialog that asks the user what value the label will have, which
        # vector data set it will append to, and which field(column) of the vector data will hold
        # the value. A button is then added to a grid layout with the button text set to f"Draw {value}
        # polygon. When the added button is pressed the user can draw geometry on the screen and the
        # geometry and set value is added to the vector dataset.
        # https://stackoverflow.com/questions/62918743/how-to-create-a-qpushbutton-dynamically-in-qgridlayout
        # https://stackoverflow.com/questions/49948742/pyqt-add-qpushbutton-dynamically
        pass
