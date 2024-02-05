from pathlib import Path

import geopandas as gpd
from osgeo import gdal
import pandas as pd
import rasterio as rio
from sklearn import svm

from PyQt5 import QtWidgets
from qgis.core import QgsProject, QgsMapLayerProxyModel, QgsFieldProxyModel
from PyQt5.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QSpinBox, QCheckBox, QPushButton, QDoubleSpinBox, QFormLayout

from statmagic_backend.dev.rasterize_training_data import training_vector_rasterize
from statmagic_backend.extract.raster import extractBands, extractBandsInBounds
from statmagic_backend.geo.transform import boundingBoxToOffsets, geotFromOffsets

from .TabBase import TabBase
from ..fileops import gdalSave, parse_vector_source
from ..gui_helpers import *
from ..layerops import addRFconfLayer, bandSelToList
from ..plotting import makePCAplot


class TrainingPointsTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Training Points")

        self.parent = parent

        topFrame, topGrid = addFrame(self, "Grid", "NoFrame", "Plain", 3)

        label0 = QLabel('Data Raster Layer')
        label1 = QLabel('Training Vector Layer')
        label2 = QLabel('With Selected:    ')
        label3 = QLabel('Add Buffer:')

        # Todo: Add filters and ToolTips on these
        self.training_layer_box = QgsMapLayerComboBox()
        self.data_raster_box = QgsMapLayerComboBox()
        self.training_buffer_box = QSpinBox()
        self.with_selected_training = QCheckBox()


        topGrid.addWidget(label0, 0, 0)
        topGrid.addWidget(self.data_raster_box, 1, 0, 1, 2)
        topGrid.addWidget(label1, 0, 2)
        topGrid.addWidget(self.training_layer_box, 1, 2, 1, 2)
        topGrid.addWidget(label2, 2, 0)
        topGrid.addWidget(self.with_selected_training, 2, 1)
        topGrid.addWidget(label3, 2, 2)
        topGrid.addWidget(self.training_buffer_box, 2, 3)

        addToParentLayout(topFrame)

        ## EDA Tools

        edaFrame, edaGrid = addFrame(self, "Grid", "Panel", "Sunken", 3)

        self.sample_at_points_button = QPushButton()
        self.sample_at_points_button.setText("Sample DataCube With\n Training Geometry")
        self.sample_at_points_button.clicked.connect(self.sample_raster_at_points)

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

        edaGrid.addWidget(self.sample_at_points_button, 0, 0, 2, 2)
        # edaGrid.addWidget(label4, 0, 3)
        edaGrid.addWidget(label5, 1, 2, 1, 1)
        edaGrid.addWidget(label6, 2, 2, 1, 1)
        edaGrid.addWidget(self.pca_x, 1, 3, 1, 1)
        edaGrid.addWidget(self.pca_y, 2, 3, 1, 1)
        edaGrid.addWidget(self.pca_plot_button, 0, 4, 2, 1)

        addToParentLayout(edaFrame)



    # def populate_comboboxes(self):
    #     self.training_layer_combo_box.setFilters(QgsMapLayerProxyModel.VectorLayer)
    #     training_layer = self.training_layer_combo_box.currentLayer()
    #     if training_layer:
    #         self.training_layer_combo_box.layerChanged.connect(self.trainingFieldComboBox.setLayer)
    #         self.trainingFieldComboBox.setLayer(training_layer)
    #         self.trainingFieldComboBox.setFilters(QgsFieldProxyModel.Numeric)

    def sample_raster_at_points(self):
        # TODO Should be able to do Points or Polygons depending on the geometry type
        data_ras = self.data_raster_box.currentLayer()
        selectedLayer = self.training_layer_box.currentLayer()
        withSelected = self.with_selected_training.isChecked()
        buffer = self.training_buffer_box.value()

        def sample_raster(data_ras, training_vector, selected, buffer):
            if selected:
                sel = training_vector.selectedFeatures()
            else:
                sel = training_vector.getFeatures()
            gdf = gpd.GeoDataFrame.from_features(sel)
            # Now have as geodataframe


        # This function should trim to selected if need be, add buffer to polygons if need be
        # And return a pd.dataframe of point/pixels as rows, and sampled raster features as columns
        #
        # 1) get the selected as gdf

        # 2) add buffer to geometry if needed

        # 3a if poly:

        # 3b if point:





        datastr = selectedLayer.source()
        gdf = parse_vector_source(datastr)
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

        self.parent.labels_tab.PrintBox.setText(statement)
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
