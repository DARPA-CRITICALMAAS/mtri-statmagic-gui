from pathlib import Path

import geopandas as gpd
from osgeo import gdal
import pandas as pd
import rasterio as rio
from sklearn import svm

from PyQt5 import QtWidgets
from qgis.core import QgsProject, QgsMapLayerProxyModel, QgsFieldProxyModel
from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QSpinBox, QCheckBox, QPushButton, QDoubleSpinBox, QFormLayout

from statmagic_backend.dev.rasterize_training_data import training_vector_rasterize
from statmagic_backend.extract.raster import extractBands, extractBandsInBounds
from statmagic_backend.geo.transform import boundingBoxToOffsets, geotFromOffsets

from .TabBase import TabBase
from ..fileops import gdalSave
from ..gui_helpers import *
from ..layerops import addRFconfLayer, bandSelToList
from ..plotting import makePCAplot


class TrainingPointsTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Training Points")

        self.parent = parent

        topFrame, topGrid = addFrame(self, "Grid", "NoFrame", "Plain", 3)

        label1 = QLabel('Training Point Layer')
        label2 = QLabel('With Selected')
        label3 = QLabel('Add Buffer')
        self.training_point_layer_box = QgsMapLayerComboBox()
        self.training_buffer_box = QSpinBox()
        self.with_selected_training = QCheckBox()

        topGrid.addWidget(label1, 0, 0)
        topGrid.addWidget(self.training_point_layer_box, 1, 0)
        #
        # topForm = QFormLayout()
        # topForm.addRow(label2, self.with_selected_training)
        # topForm.addRow(label3, self.training_buffer_box)
        #
        # topGrid.addWidget(topForm, 0, 1)

        topGrid.addWidget(label2, 0, 1)
        topGrid.addWidget(self.with_selected_training, 0, 2)
        topGrid.addWidget(label3, 1, 1)
        topGrid.addWidget(self.training_buffer_box, 1, 2)

        topGrid.setColumnStretch(0, 2)
        topGrid.setColumnStretch(1, 1)
        topGrid.setColumnStretch(2, 1)

        addToParentLayout(topFrame)

        ## EDA Tools

        edaFrame, edaGrid = addFrame(self, "Grid", "Panel", "Sunken", 3)

        self.sample_at_points_button = QPushButton()
        self.sample_at_points_button.setText("Sample DataCube at Points")
        self.sample_at_points_button.clicked.connect(self.sample_raster_at_points)
        self.sample_at_points_button

        self.pca_plot_button = QPushButton()
        self.pca_plot_button.setText('Create PCA Plot')
        self.pca_plot_button.clicked.connect(self.runPCAplot)

        self.dbscan_button = QPushButton()
        self.pca_x = QSpinBox()
        self.pca_y = QSpinBox()
        self.dbsca_eta = QDoubleSpinBox()
        self.dbscan_min_sampe = QSpinBox()

        label4 = QLabel('PCA Plot Axis')
        label5 = QLabel('PCA Plot X Axis')
        label6 = QLabel('PCA Plot Y Axis')
        label7 = QLabel('eps')
        label8 = QLabel('min_samples')

        edaGrid.addWidget(self.sample_at_points_button, 0, 0, 1, 2)
        # edaGrid.addWidget(label4, 0, 3)
        edaGrid.addWidget(label5, 1, 2, 1, 1)
        edaGrid.addWidget(label6, 2, 2, 1, 1)
        edaGrid.addWidget(self.pca_x, 1, 3, 1, 1)
        edaGrid.addWidget(self.pca_y, 2, 3, 1, 1)
        edaGrid.addWidget(self.pca_plot_button, 0, 4, 2, 1)

        addToParentLayout(edaFrame)







        #### TOP CLUSTER #####
        # topFrame, topLayout = addFrame(self, "HBox", "NoFrame", "Plain", 3)
        #
        # self.training_layer_combo_box = addQgsMapLayerComboBox(topFrame, "Training Data Layer")
        # self.gather_pt_data_button = addButton(topFrame, "Sample Raster at Points", self.sample_raster_at_points)
        #
        # addToParentLayout(topFrame)
        #
        # ##### LEFT ALIGNED CLUSTER #####
        # leftFrame, leftLayout = addFrame(self, "Grid", "NoFrame", "Plain", 3)
        # leftLayout.setVerticalSpacing(5)
        #
        # label = addLabel(leftLayout, "With Point Sample Data", gridPos=(0,0))
        # makeLabelBig(label)
        #
        # self.train_svm_button = addButton(leftFrame, "Train One Class SVM", self.trainOneClassSVM, gridPos=(1,0))
        # self.map_svm_button = addButton(leftFrame, "Map SVM Scores", self.mapSVMscores, gridPos=(2,0))
        #
        # ##### EMPTY FRAME (to force left alignment) #####
        # # TODO: figure out why this can't be replaced with a call to alignLayoutAndAddToParent()
        # rightFrame = QtWidgets.QFrame(leftFrame)
        # addToParentLayout(rightFrame, gridPos=(0,1))
        #
        # addToParentLayout(leftFrame)
        #
        # ##### MIDDLE FRAME (visible) #####
        # middleFrame, middleLayout = addFrame(self, "VBox", "Panel", "Sunken", 2)
        #
        # formLayout = QtWidgets.QFormLayout(middleFrame)
        #
        # self.training_buffer_dist = addSpinBoxToForm(formLayout, "Buffer Points (units of template CRS):",
        #                                              dtype=float, value=0, max=1000000, step=25)
        # self.trainingFieldComboBox = QgsFieldComboBox()
        # addFormItem(formLayout, "Use Field for Raster Values:", self.trainingFieldComboBox)
        #
        # addWidgetFromLayoutAndAddToParent(formLayout, middleFrame)
        #
        # self.rasterize_training_button = addButton(middleFrame, "Rasterize Training Vector", self.rasterize_training, align="Center")
        #
        # addToParentLayout(middleFrame)
        #
        # ##### BOTTOM CLUSTER #####
        # bottomFrame, bottomLayout = addFrame(self, "HBox", "NoFrame", "Plain", 3)
        #
        # self.generate_plot_button_2 = addButton(bottomFrame, "Plot PCA", self.runPCAplot)
        #
        # plotForm = QtWidgets.QFormLayout(bottomFrame)
        # self.plt_axis_1, self.plt_axis_2 = addTwoSpinBoxesToForm(plotForm, "PCA Dim", "x-axis", "y-axis", 1, 2,
        #                                                          dtype=int, minX=1, maxX=10, minY=2, maxY=10)
        # addWidgetFromLayoutAndAddToParent(plotForm, bottomFrame)
        #
        # addToParentLayout(bottomFrame)
        #
        # self.populate_comboboxes()

    # def populate_comboboxes(self):
    #     self.training_layer_combo_box.setFilters(QgsMapLayerProxyModel.VectorLayer)
    #     training_layer = self.training_layer_combo_box.currentLayer()
    #     if training_layer:
    #         self.training_layer_combo_box.layerChanged.connect(self.trainingFieldComboBox.setLayer)
    #         self.trainingFieldComboBox.setLayer(training_layer)
    #         self.trainingFieldComboBox.setFilters(QgsFieldProxyModel.Numeric)

    def sample_raster_at_points(self):
        # TODO Should be able to do Points or Polygons depending on the geometry type
        data_ras = self.parent.comboBox_raster.currentLayer()
        selectedLayer = self.training_layer_combo_box.currentLayer()
        datastr = selectedLayer.source()

        # TODO: this looks like duplicated code! find it and move to separate function!
        try:
            # This will be the case for geopackages, but not shapefile or geojson
            fp, layername = datastr.split('|')
            gdf = gpd.read_file(fp, layername=layername.split('=')[1])
        except ValueError:
            fp = datastr
            gdf = gpd.read_file(fp)

        # fp, layername = datastr.split('|')
        # gdf = gpd.read_file(fp, layername=layername.split('=')[1])
        raster = rio.open(data_ras.source())
        raster_crs = raster.crs
        if gdf.crs != raster_crs:
            gdf.to_crs(raster_crs, inplace=True)
        nodata = raster.nodata
        bands = raster.descriptions
        coords = [(x, y) for x, y in zip(gdf.geometry.x, gdf.geometry.y)]  # list of gdf lat/longs
        samples = [x for x in raster.sample(coords, masked=True)]
        s = np.array(samples)
        # Drop rows with nodata value
        dat = s[~(s == nodata).any(1), :]
        # Turn into dataframe for keeping
        df = pd.DataFrame(dat, columns=bands)
        print(df.head())

        statement = (f"{dat.shape[0]} sample points collected. \n"
                     f"{s.shape[0] - dat.shape[0]} "
                     f"dropped from intersection with nodata values.")

        self.parent.labels_tab.PrintBox.setText(statement)  # TODO: not this
        self.iface.messageBar().pushMessage(statement)

        self.parent.point_samples = df
    #
    # def trainOneClassSVM(self):
    #     if self.parent.oneClassSVM is not None:
    #         self.parent.oneClassSVM = None
    #
    #     pointdata = self.parent.point_samples
    #     x_train = pointdata.to_numpy()
    #
    #     # One class SVM
    #     # Can add inputs for user defnined parameters later
    #     kernel = 'rbf'
    #     nu = 0.5
    #     gamma = 0.001
    #
    #     ocsvm = svm.OneClassSVM(nu=nu, kernel=kernel, gamma=gamma)
    #     ocsvm.fit(x_train)
    #
    #     # # Isolation Forest
    #     # ocsvm = IsolationForest()
    #     # ocsvm.fit(x_train)
    #
    #     ## Local Outlier Factor
    #     # ocsvm = LocalOutlierFactor(novelty=True)
    #     # ocsvm.fit(x_train)
    #
    #     self.iface.messageBar().pushMessage('SVM Model Fit')
    #     self.parent.oneClassSVM = ocsvm
    #
    # def mapSVMscores(self):
    #     selectedRas = self.parent.comboBox_raster.currentLayer()
    #
    #     root = QgsProject.instance().layerTreeRoot()
    #     if root.findGroup('One Class SVM') == None:
    #         SVMgroup = root.insertGroup(0, 'One Class SVM')
    #     else:
    #         SVMgroup = root.findGroup('One Class SVM')
    #
    #     r_ds = gdal.Open(selectedRas.source())
    #     geot = r_ds.GetGeoTransform()
    #     r_proj = r_ds.GetProjection()
    #     nodata = r_ds.GetRasterBand(1).GetNoDataValue()
    #     cellres = geot[1]
    #     rsizeX, rsizeY = r_ds.RasterXSize, r_ds.RasterYSize
    #
    #     ocsvm = self.parent.oneClassSVM
    #
    #     if self.parent.ClusterWholeExtentBox.isChecked():
    #         layerName = 'Full_Extent_' + 'One Class SVM'
    #
    #         if self.dockwidget.UseBandSelectionBox.isChecked():
    #             bandList = bandSelToList(self.parent.labels_tab.stats_table)    # TODO: not this
    #             dat = extractBands(bandList, r_ds)
    #         else:
    #             dat = r_ds.ReadAsArray()
    #
    #         data_array = np.transpose(dat, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
    #         twoDshape = (data_array.shape[0] * data_array.shape[1], data_array.shape[2])
    #         pred_data = data_array.reshape(twoDshape)
    #         bool_arr = np.all(pred_data == nodata, axis=1)
    #         if np.count_nonzero(bool_arr == 1) < 1:
    #             print('not over no data values')
    #             scores = ocsvm.score_samples(pred_data)
    #
    #         else:
    #             idxr = bool_arr.reshape(pred_data.shape[0])
    #             pstack = pred_data[idxr == 0, :]
    #             scrs = ocsvm.score_samples(pstack)
    #
    #             scores = np.zeros_like(bool_arr, dtype='float32')
    #             scores[~bool_arr] = scrs
    #             scores[bool_arr] = 0
    #
    #         preds = scores.reshape(rsizeY, rsizeX, 1)
    #         classout = np.transpose(preds, (0, 1, 2))[:, :, 0]
    #
    #     else:
    #         layerName = 'Window_Extent_' + 'One Class SVM'
    #
    #         bb = self.canvas.extent()
    #         bb.asWktCoordinates()
    #         bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
    #         offsets = boundingBoxToOffsets(bbc, geot)
    #         new_geot = geotFromOffsets(offsets[0], offsets[2], geot)
    #         geot = new_geot
    #
    #         sizeX = int(((bbc[2] - bbc[0]) / cellres) + 1)
    #         sizeY = int(((bbc[3] - bbc[1]) / cellres) + 1)
    #
    #         if self.parent.UseBandSelectionBox.isChecked():
    #             bandList = bandSelToList(self.parent.labels_tab.stats_table)    # TODO: not this
    #             dat = extractBandsInBounds(bandList, r_ds, offsets[2], offsets[0], sizeX, sizeY)
    #         else:
    #             dat = r_ds.ReadAsArray(offsets[2], offsets[0], sizeX, sizeY)
    #
    #         data_array = np.transpose(dat, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
    #         twoDshape = (data_array.shape[0] * data_array.shape[1], data_array.shape[2])
    #         pred_data = data_array.reshape(twoDshape)
    #
    #         scores = ocsvm.score_samples(pred_data)
    #
    #         preds = scores.reshape(sizeY, sizeX, 1)
    #         classout = np.transpose(preds, (0, 1, 2))[:, :, 0]
    #
    #     savedLayer = gdalSave('SVM_Scores', classout.astype('float32'), gdal.GDT_Float32, geot, r_proj, float(np.finfo('float32').min))
    #     addRFconfLayer(savedLayer, "SVM_Score", SVMgroup)
    #
    #     # TODO: fix runtime error (where is proj_path supposed to be defined?)
    #     message = f"Project files loaded from: {proj_path}"
    #     self.iface.messageBar().pushMessage(message)
    #
    # def rasterize_training(self):
    #     selectedLayer = self.training_layer_combo_box.currentLayer()
    #     datastr = selectedLayer.source()
    #     buffer_distance = self.training_buffer_dist.value()
    #
    #     # TODO update training rasterization to take do the values by attribute
    #     field = self.trainingFieldComboBox.currentField()
    #
    #     # TODO: remove duplicated code
    #     try:
    #         # This will be the case for geopackages, but not shapefile or geojson
    #         fp, layername = datastr.split('|')
    #         training_gdf = gpd.read_file(fp, layername=layername.split('=')[1])
    #     except ValueError:
    #         fp = datastr
    #         training_gdf = gpd.read_file(fp)
    #
    #     training_raster_output_path = str(Path(self.parent.meta_data['project_path'], 'training_raster.tif'))
    #
    #     # TODO add to TOC
    #
    #     message = training_vector_rasterize(training_gdf, self.parent.meta_data['template_path'], training_raster_output_path, buffer_distance)
    #     self.iface.messageBar().pushMessage(message)
    #
    def runPCAplot(self):
        pca_axis_1 = self.plt_axis_1.value()
        pca_axis_2 = self.plt_axis_2.value()
        pct_data_plot = self.pctdataplotBox.value()
        plotsubVal = int(100 / pct_data_plot)
        data_sel = self.data_sel_box.currentIndex()
        print(data_sel)
        # TODO: these global variables might not have been defined yet
        if data_sel == 0:
            data_input = self.parent.fullK
        elif data_sel == 1:
            data_input = self.parent.maskK
        elif data_sel == 2:
            data_input = self.parent.trainingK
        else:
            print('invalid selection')
        if data_input:
            makePCAplot(data_input, pca_axis_1, pca_axis_2, plotsubVal, data_sel)
