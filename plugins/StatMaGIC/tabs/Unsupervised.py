import pandas as pd
from osgeo import gdal
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from PyQt5 import QtCore, QtWidgets
from qgis.core import QgsProject

from statmagic_backend.extract.raster import extractBands, extractBandsInBounds, placeLabels_inRaster, \
    getFullRasterDict, getCanvasRasterDict
from statmagic_backend.geo.transform import boundingBoxToOffsets
from statmagic_backend.math.clustering import unpack_fullK, soft_clustering_weights, doPCA_kmeans, clusterDataInMask
from statmagic_backend.math.sampling import dropSelectedBandsforSupClass, balancedSamples

from .TabBase import TabBase
from ..fileops import gdalSave, kosher
from ..gui_helpers import *
from ..layerops import bandSelToList, addLayerSymbolMutliClassGroup, rasterBandDescAslist, getTrainingDataFromFeatures


class UnsupervisedTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Unsupervised")

        self.parent = parent

        ##### TOP STUFF #####
        topFrame1, topLayout1 = addFrame(self, "HBox", "NoFrame", "Plain", 3)

        data_items = ["Full Data", "Within Mask", "Within Polygons"]
        self.data_sel_box = addComboBox(topFrame1, "Data Selection", data_items, layout_str="VBox")
        self.NumClustersBox = addSpinBox(topFrame1, "# Clusters", "VBox", dtype=int, value=5, min=2)
        self.pca_var_exp = addSpinBox(topFrame1, "PCA var exp", "VBox", dtype=float,
                                      value=0.95, min=0.25, max=0.99, step=0.025)
        self.pca_var_exp.setDecimals(3)     # TODO: add to helper if this is a common operation
        self.DetectNumClustersButton = addButton(topFrame1, "Detect #\nClusters", self.DetectNumberClusters)

        addToParentLayout(topFrame1)

        topFrame2, topLayout2 = addFrame(self, "HBox", "NoFrame", "Plain", 3)

        self.PCAbox = addCheckbox(topFrame2, "Standardize and PCA", isChecked=True)
        addEmptyFrame(topLayout2)    # force space between checkbox and button
        self.RunKmeansButton = addButton(topFrame2, "Run Kmeans", self.selectKmeansData)

        addToParentLayout(topFrame2)

        addEmptyFrame(self.layout())     # force space between top stuff and map clusters frame

        ##### MAP CLUSTERS FRAME #####
        mapClustersFrame, mapClustersLayout = addFrame(self, "VBox", "Box", "Plain", 2, margins=10)

        self.ArchetypeCheckBox = addCheckbox(mapClustersFrame, "Return Archetypes")

        subFrame, subLayout = addFrame(mapClustersFrame, "HBox", "NoFrame", "Plain", 3)
        subLayout.setSpacing(5)

        formLayout = QtWidgets.QFormLayout(subFrame)
        self.ConfValue = addLineEditToForm(formLayout, "Confidence Threshold", value=0.95)
        self.FuzzinessValue = addLineEditToForm(formLayout, "Fuzziness Metric (1-5)", value=2)
        subLayout.addLayout(formLayout)

        self.MapClustersButton = addButton(subFrame, "Map Clusters", self.NewMapClusters)

        addToParentLayout(subFrame)
        addToParentLayout(mapClustersFrame)

        ##### PCA PLOTTING FRAME #####
        PCA_frame, PCA_layout = addFrame(self, "VBox", "Box", "Plain", 2, margins=10)
        addBigLabel(PCA_layout, "PCA Plotting")
        PCA_subFrame, PCA_subLayout = addFrame(PCA_frame, "HBox", "NoFrame", "Plain", 3)
        PCA_subLayout.setSpacing(5)

        PCA_leftForm = QtWidgets.QFormLayout(PCA_subFrame)

        self.plt_axis_1, self.plt_axis_2 = addTwoSpinBoxesToForm(PCA_leftForm, "PCA Dim", "x-axis", "y-axis", 1, 2,
                                                                 dtype=int, minX=1, maxX=10, minY=2, maxY=10)
        self.pctdataplotBox = addSpinBoxToForm(PCA_leftForm, "% Data to Plot", value=5, min=1, max=100, step=5)
        self.generate_plot_button = addButtonToForm(PCA_leftForm, "Generate Plot", self.runPCAtrainingPointplot)

        PCA_subLayout.addLayout(PCA_leftForm)

        PCA_rightForm = QtWidgets.QFormLayout(PCA_subFrame)
        PCA_rightForm.setLabelAlignment(QtCore.Qt.AlignRight)

        self.refres_data_button = addButtonToForm(PCA_rightForm, "Refresh Data", self.RefreshData)
        self.burnBox_2 = addCheckboxToForm(PCA_rightForm, "Use Exploratory Options")
        self.burnBox_2.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.pca_var_exp_list = addLineEditToForm(PCA_rightForm, "Var Exp Limits List")
        self.n_clusters_list = addLineEditToForm(PCA_rightForm, "# Clusters List")

        PCA_subLayout.addLayout(PCA_rightForm)
        addToParentLayout(PCA_subFrame)
        addToParentLayout(PCA_frame)

        ##### SUB-CLASS CLUSTERING FRAME #####
        subClassClusteringFrame, subClassClusteringLayout = addFrame(self, "VBox", "Box", "Plain", 2, margins=10)

        addBigLabel(subClassClusteringLayout, "Sub-Class Clustering")

        subFrame2, subLayout2 = addFrame(subClassClusteringFrame, "HBox", "NoFrame", "Plain", 3)
        subLayout2.setSpacing(5)

        subLeftForm = QtWidgets.QFormLayout(subFrame2)
        self.comboBox_ClassRaster = addQgsMapLayerComboBoxToForm(subLeftForm, "Class Layer")
        self.class_parse_lineEdit = addLineEditToForm(subLeftForm, "Mask Class(es)")
        self.numNewClustersBox = addSpinBoxToForm(subLeftForm, "# New Clusters", value=2, min=2, max=2, step=1)

        subLayout2.addLayout(subLeftForm)

        subRightForm = QtWidgets.QFormLayout(subFrame2)
        addEmptyFrame(subRightForm)
        self.mapSubClustersButton = addButtonToForm(subRightForm, "Map Sub Clusters", self.mapMaskedClusters)
        self.burnBox = addCheckboxToForm(subRightForm, "Burn Over Input")

        alignLayoutAndAddToParent(subRightForm, subFrame2, "Bottom")

        addToParentLayout(subFrame2)
        addToParentLayout(subClassClusteringFrame)
        
        ##### VARIABLES SPECIFIC TO THIS TAB #####
        self.fullK = {}
        self.trainingK = {}
        self.maskK = {}
        self.point_samples = pd.DataFrame()

    def DetectNumberClusters(self):
        '''
        The entire of the raster extraction and saving out is from the CreateRasterFromMapExtent Function.
        Just in between is the Kmeans Clustering stuff
        :return:
        '''

        def find_Nclust(data, start=3, stop=20, show_plot=False):
            intertias = []
            for i in range(start, stop):
                print(i)
                km = MiniBatchKMeans(n_clusters=i, init='k-means++', random_state=101)
                km.fit(data)
                intertias.append(km.inertia_)
            # if show_plot:
            # plt.plot(intertias)
            # plt.show()
            # Copied from
            # https://stackoverflow.com/questions/2018178/finding-the-best-trade-off-point-on-a-curve
            nPoints = len(intertias)
            allCoord = np.vstack((range(nPoints), intertias)).T
            firstPoint = allCoord[0]
            lineVec = allCoord[-1] - allCoord[0]
            lineVecNorm = lineVec / np.sqrt(np.sum(lineVec ** 2))
            vecFromFirst = allCoord - firstPoint
            scalarProduct = np.sum(vecFromFirst * np.matlib.repmat(lineVecNorm, nPoints, 1), axis=1)
            vecFromFirstParallel = np.outer(scalarProduct, lineVecNorm)
            vecToLine = vecFromFirst - vecFromFirstParallel
            distToLine = np.sqrt(np.sum(vecToLine ** 2, axis=1))
            bestidx = np.argmax(distToLine)
            n_clust = bestidx + start + 1
            print("Data organizes into {} clusters".format(n_clust))
            return n_clust

        def subsetter(data, num_samp=1000000):
            datlen = data.shape[0]
            datdim = data.shape[1]
            datsize = datlen * datdim
            if datsize > 100000:
                # print("taking a subset of {} rows to sample for best cluster size".format(num_samp))
                return data[np.random.choice(data.shape[0], num_samp, replace=True)]
            else:
                return data

        selectedRas = self.parent.comboBox_raster.currentLayer()
        r_ds = gdal.Open(selectedRas.source())
        geot = r_ds.GetGeoTransform()
        cellres = geot[1]
        nodata = r_ds.GetRasterBand(1).GetNoDataValue()

        if self.parent.ClusterWholeExtentBox.isChecked():
            if self.parent.UseBandSelectionBox.isChecked():
                bandList = bandSelToList()
                dat = extractBands(bandList, r_ds)
            else:
                dat = r_ds.ReadAsArray()
            data_array = np.transpose(dat, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
            twoDshape = (data_array.shape[0] * data_array.shape[1], data_array.shape[2])
            rs_data = data_array.reshape(twoDshape)
            bool_arr = np.all(rs_data == nodata, axis=1)
            if np.count_nonzero(bool_arr == 1) < 1:
                pred_data  = rs_data
            else:
                idxr = bool_arr.reshape(rs_data.shape[0])
                pred_data = rs_data[idxr == 0, :]
            nclust = find_Nclust(subsetter(pred_data, num_samp=1000000), start=3, stop=20, show_plot=True)
            clustprintstatement = f'Data of the Full Raster best described in {nclust} clusters'

        else:
            bb = self.canvas.extent()
            bb.asWktCoordinates()

            bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
            offsets = boundingBoxToOffsets(bbc, geot)

            sizeX = int(((bbc[2] - bbc[0]) / cellres) + 1)
            sizeY = int(((bbc[3] - bbc[1]) / cellres) + 1)

            if self.parent.UseBandSelectionBox.isChecked():
                bandList = bandSelToList(self.labels_tab.stats_table)
                dat = extractBandsInBounds(bandList, r_ds, offsets[2], offsets[0], sizeX, sizeY)
            else:
                dat = r_ds.ReadAsArray(offsets[2], offsets[0], sizeX, sizeY)

            data_array = np.transpose(dat, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
            twoDshape = (data_array.shape[0] * data_array.shape[1], data_array.shape[2])
            pred_data = data_array.reshape(twoDshape)
            nclust = find_Nclust(subsetter(pred_data, num_samp=1000000), start=3, stop=20, show_plot=True)
            clustprintstatement = f'Data in Extent best described in {nclust} clusters'

        self.PrintBox.setText(clustprintstatement)

    def selectKmeansData(self):
        data_sel = self.data_sel_box.currentIndex()
        print(data_sel)
        if data_sel == 0:
            self.doKmeansFull_Window()
        elif data_sel == 1:
            self.doMaskedKmeans()
        elif data_sel == 2:
            self.doTrainingPolyKmeans()
        else:
            print('invalid selection')

    def NewMapClusters(self):
        if not self.fullK:
            print('need to run Kmeans first')
        labels1, km, pca, ras_dict, bool_arr, fitdat, rasBands, nclust = unpack_fullK(self.fullK)

        if self.ArchetypeCheckBox.isChecked():
            classout, labels = placeLabels_inRaster(labels1, bool_arr, ras_dict, 'uint8', return_labels=True)
        else:
            classout = placeLabels_inRaster(labels1, bool_arr, ras_dict, 'uint8')

        #
        # labels = np.zeros_like(bool_arr).astype('uint8')
        # labels[~bool_arr] = labels1
        # labels[bool_arr] = 0
        #
        # preds = labels.reshape(ras_dict['sizeY'], ras_dict['sizeX'], 1)
        # classout = np.transpose(preds, (0, 1, 2))[:, :, 0]

        root = QgsProject.instance().layerTreeRoot()
        layerName = 'Kmeans_' + str(nclust) + '_clusters'

        if root.findGroup('Kmeans') == None:
            Kgroup = root.insertGroup(0, 'Kmeans')
        else:
            Kgroup = root.findGroup('Kmeans')

        savedLayer = gdalSave('Window_Kmeans_', classout, gdal.GDT_Byte, ras_dict['GeoTransform'], ras_dict['Projection'], 0)
        addLayerSymbolMutliClassGroup(savedLayer, layerName, Kgroup, np.unique(classout).tolist(), "Classes")

        if self.ArchetypeCheckBox.isChecked():
            conflevel = float(self.ConfValue.text())
            fuzzval = float(self.FuzzinessValue.text())
            weights = soft_clustering_weights(fitdat, km.cluster_centers_, fuzzval)
            conf = np.max(weights, axis=1).astype('float32')

            if conf.shape[0] == labels.shape[0]:
                best_clusts = np.where(conf > conflevel, labels, 0).astype('uint8')
            else:
                # need to use the mask to fill in values
                new_conf = np.zeros_like(bool_arr).astype('float32')
                new_conf[~bool_arr] = conf
                new_conf[bool_arr] = 0
                best_clusts = np.where(new_conf > conflevel, labels, 0).astype('uint8')

            # bestsout = best_clusts.reshape(data_array.shape[0], data_array.shape[1])
            bestsout = best_clusts.reshape(ras_dict['sizeY'], ras_dict['sizeX'])
            confLayerName = 'Conf_' + str(conflevel).split(".")[1] + "_" + str(fuzzval)
            savedConf = gdalSave('Conf_', bestsout, gdal.GDT_Byte, ras_dict['GeoTransform'], ras_dict['Projection'], 0)
            addLayerSymbolMutliClassGroup(savedConf, confLayerName, Kgroup, np.unique(classout).tolist(), "Classes")

    def runPCAtrainingPointplot(self):
        df = self.point_samples

        nclust = self.NumClusterBox.value()
        varexp = self.pca_var_exp.value()
        pca_bool = self.PCAbox.isChecked()

        km = MiniBatchKMeans(n_clusters=nclust, init='k-means++', random_state=101)
        pca = PCA(n_components=varexp, svd_solver='full')

        pred_data = df.to_numpy()

        standata = StandardScaler().fit_transform(pred_data)
        fitdat = pca.fit_transform(standata)
        print(f'PCA uses {pca.n_components_} to get to {varexp} variance explained')
        km.fit_predict(fitdat)
        labels = km.labels_ + 1

        # This is just to make doPCA_kmeans have something
        rasBands = df.columns
        bool_arr = np.array([0])
        if np.count_nonzero(bool_arr == 1) < 1:
            print(True)
        # ras_dict =

        data_input = {'labels': labels, 'km': km, 'pca': pca, 'fitdat': fitdat,
                      'bool_arr': bool_arr, 'rasBands': rasBands, 'nclust': nclust}

        k_dict = {'labels': labels, 'km': km, 'pca': pca, 'fitdat': fitdat,
                  'bool_arr': bool_arr, 'rasBands': rasBands, 'nclust': nclust}
        self.trainingK = k_dict

    def mapMaskedClusters(self):
        if not self.maskK:
            print('need to run Kmeans first')
        labels1, km, pca, ras_dict, bool_arr, fitdat, rasBands, nclust, class_arr = unpack_fullK(self.maskK)

        if self.ArchetypeCheckBox.isChecked():
            classout, labels = placeLabels_inRaster(labels1, bool_arr, ras_dict, 'uint8', return_labels=True)
        else:
            classout = placeLabels_inRaster(labels1, bool_arr, ras_dict, 'uint8')

        burnOver = self.burnBox.isChecked()
        inputClasses = self.class_parse_lineEdit.text()
        clusclass = [int(x) for x in inputClasses.split(',')]

        layerName = 'Class_' + inputClasses + 'into' + str(nclust) + '_Classes'

        if burnOver:
            print('burning new clusters over classified map')
            class_mask = np.isin(class_arr[0, :, :], clusclass)
            classout = np.where(class_mask, classout, class_arr[0, :, :])

        root = QgsProject.instance().layerTreeRoot()
        if root.findGroup('Kmeans') == None:
            Kgroup = root.insertGroup(0, 'Kmeans')
        else:
            Kgroup = root.findGroup('Kmeans')

        savedLayer = gdalSave('Window_Kmeans_', classout, gdal.GDT_Byte, ras_dict['GeoTransform'], ras_dict['Projection'], 0)
        addLayerSymbolMutliClassGroup(savedLayer, layerName, Kgroup, np.unique(classout).tolist(), "Classes")

        if self.ArchetypeCheckBox.isChecked():
            conflevel = float(self.ConfValue.text())
            fuzzval = float(self.FuzzinessValue.text())
            weights = soft_clustering_weights(fitdat, km.cluster_centers_, fuzzval)
            conf = np.max(weights, axis=1).astype('float32')

            if conf.shape[0] == labels.shape[0]:
                best_clusts = np.where(conf > conflevel, labels, 0).astype('uint8')
            else:
                # need to use the mask to fill in values
                new_conf = np.zeros_like(bool_arr).astype('float32')
                new_conf[~bool_arr] = conf
                new_conf[bool_arr] = 0
                best_clusts = np.where(new_conf > conflevel, labels, 0).astype('uint8')

            bestsout = best_clusts.reshape(ras_dict['sizeY'], ras_dict['sizeX'])
            confLayerName = 'Conf_' + str(conflevel).split(".")[1] + "_" + str(fuzzval)
            savedConf = gdalSave('Conf_', bestsout, gdal.GDT_Byte, ras_dict['GeoTransform'], ras_dict['Projection'], 0)
            addLayerSymbolMutliClassGroup(savedConf, confLayerName, Kgroup, np.unique(classout).tolist(), "Classes")

        doneClusters = 'Finished Mapping Clusters '
        print(doneClusters)
        self.PrintBox.setText(doneClusters)

    def RefreshData(self):
        self.iface.messageBar().pushMessage("Refresh Data Not Implemented.")

    def doKmeansFull_Window(self):
        '''
        This function does the Kmeans on the full extent of the raster or window
        :return:
        '''
        # Print Statements
        doingClusters = 'Running Kmeans'
        print(doingClusters)
        self.PrintBox.setText(doingClusters)

        # Gather Inputs
        data_ras = self.parent.comboBox_raster.currentLayer()
        nclust = self.NumClusterBox.value()
        varexp = self.pca_var_exp.value()
        pca_bool = self.PCAbox.isChecked()

        # Open the data raster and get metadata
        r_ds = gdal.Open(data_ras.source())
        ras_dict = getFullRasterDict(r_ds)
        rasBands = rasterBandDescAslist(data_ras.source())

        # Arrange the data from the whole raster or canvas extent into pixel feature format
        if self.parent.ClusterWholeExtentBox.isChecked():
            if self.parent.UseBandSelectionBox.isChecked():
                bandList = bandSelToList(self.labels_tab.stats_table)
                rasBands = [rasBands[i-1] for i in bandList]
                dat = extractBands(bandList, r_ds)
            else:
                dat = r_ds.ReadAsArray()
        else:
            bb = self.canvas.extent()
            ras_dict = getCanvasRasterDict(ras_dict, bb)
            if self.parent.UseBandSelectionBox.isChecked():
                bandList = bandSelToList(self.labels_tab.stats_table)
                rasBands = [rasBands[i - 1] for i in bandList]
                dat = extractBandsInBounds(bandList, r_ds, ras_dict['Xoffset'], ras_dict['Yoffset'], ras_dict['sizeX'], ras_dict['sizeY'])
            else:
                dat = r_ds.ReadAsArray(ras_dict['Xoffset'], ras_dict['Yoffset'], ras_dict['sizeX'], ras_dict['sizeY'])

        data_array = np.transpose(dat, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
        twoDshape = (data_array.shape[0] * data_array.shape[1], data_array.shape[2])
        pred_data = data_array.reshape(twoDshape)
        bool_arr = np.any(pred_data == ras_dict['NoData'], axis=1)

        kosher({'pred_data': pred_data, 'bool_arr': bool_arr, 'nd': ras_dict['NoData']},
               '/home/jagraham/Documents/temp_work/temp_space/kmeans')

        labels, km, pca, fitdat = doPCA_kmeans(pred_data, bool_arr, nclust, varexp, pca_bool)
        fullK_dict = {'labels': labels, 'km': km, 'pca': pca, 'fitdat': fitdat,
                      'bool_arr': bool_arr, 'rasBands': rasBands, 'nclust': nclust}

        self.fullK = fullK_dict
        print('added to gvars')

    def doMaskedKmeans(self):
        # Get inputs
        data_ras = self.parent.comboBox_raster.currentLayer()
        class_ras = self.comboBox_ClassRaster.currentLayer()
        nclust = self.numNewClustersBox.value()
        inputClasses = self.class_parse_lineEdit.text()
        varexp = self.pca_var_exp.value()
        pca_bool = self.PCAbox.isChecked()
        clusclass = [int(x) for x in inputClasses.split(',')]

        # Open the data raster and get metadata
        r_ds = gdal.Open(data_ras.source())
        ras_dict = getFullRasterDict(r_ds)
        rasBands = rasterBandDescAslist(data_ras.source())

        # Open the class raster
        classRaster = gdal.Open(class_ras.source())
        print(classRaster)

        # Arrange the data from the whole raster or canvas extent into pixel feature format
        if self.parent.ClusterWholeExtentBox.isChecked():
            if self.parent.UseBandSelectionBox.isChecked():
                bandList = bandSelToList(self.labels_tab.stats_table)
                rasBands = [rasBands[i - 1] for i in bandList]
                stack_arr = extractBands(bandList, r_ds)
            else:
                stack_arr = r_ds.ReadAsArray()
            class_arr = classRaster.ReadAsArray()
        else:

            bb = self.canvas.extent()
            ras_dict = getCanvasRasterDict(ras_dict, bb)
            if self.parent.UseBandSelectionBox.isChecked():
                bandList = bandSelToList(self.labels_tab.stats_table)
                rasBands = [rasBands[i - 1] for i in bandList]
                stack_arr = extractBandsInBounds(bandList, r_ds, ras_dict['Xoffset'], ras_dict['Yoffset'], ras_dict['sizeX'],
                                           ras_dict['sizeY'])
            else:
                stack_arr = r_ds.ReadAsArray(ras_dict['Xoffset'], ras_dict['Yoffset'], ras_dict['sizeX'], ras_dict['sizeY'])

            # This is jank. should put in a if canvas extent is smaller than the class raster then use the window read
            class_arr = classRaster.ReadAsArray()
            # class_arr = classRaster.ReadAsArray(ras_dict['Xoffset'], ras_dict['Yoffset'], ras_dict['sizeX'], ras_dict['sizeY'])

        if len(class_arr.shape) == 2:
            class_arr = np.expand_dims(class_arr, axis=0)

        print(f'class_arr shape {class_arr.shape}')
        print(f'stack_arr shape {stack_arr.shape}')
        re_class = np.transpose(class_arr, (1, 2, 0))
        re_stack = np.transpose(stack_arr, (1, 2, 0))

        twoDshape = (re_stack.shape[0] * re_stack.shape[1], re_stack.shape[2])

        pred_data = re_stack.reshape(twoDshape)
        class_data = re_class.reshape(twoDshape[0])

        nodata_mask = np.any(pred_data == ras_dict['NoData'], axis=1)

        print(f'class shape {class_data.shape}')
        print(f'pred shape {pred_data.shape}')

        labels, km, pca, fitdat, bool_arr = clusterDataInMask(pred_data, class_data, nodata_mask, nclust, varexp, pca_bool, clusclass)

        maskK_dict = {'labels': labels, 'km': km, 'pca': pca, 'fitdat': fitdat,
                      'bool_arr': bool_arr, 'rasBands': rasBands, 'nclust': nclust, 'class_arr': class_arr}
        self.maskK = maskK_dict
        print('added to gvars')

        # if perclass_bool:
        #     print('do per class')
        #     # Make mask to block out nodata
        #     outclassList = []
        #     for cls in clusclass:
        #         noncluster_mask = np.isin(class_data, cls, invert=True)
        #         bool_arr = np.logical_or(noncluster_mask, nodata_mask)
        #         outclass = clusterDataInMask(pred_data, bool_arr, nclust, varexp, rsizeY, rsizeX)
        #         newValarr = np.where(outclass != 0, outclass + (cls * 10), 0)
        #         outclassList.append(newValarr)
        #     classout = sum(outclassList)
        # else:
        #     print('do pooled classes')
        #     noncluster_mask = np.isin(class_data, clusclass, invert=True)
        #     bool_arr = np.logical_or(noncluster_mask, nodata_mask)
        #     classout, fitdat, labels, km = clusterDataInMask(pred_data, bool_arr, nclust, rsizeY, rsizeX)
        #

    def doTrainingPolyKmeans(self):
        selectedLayer = self.parent.comboBox_vector.currentLayer()
        data_ras = self.parent.comboBox_raster.currentLayer()
        retain_pct = float(self.TestHoldPct_spinBox.value()) / 100

        samplingRate = self.samplingRatespinBox.value()
        maxPixPoly = self.max_pix_poly_spinBox.value()
        maxClassPix = self.max_sample_spinBox.value()

        nclust = self.NumClusterBox.value()
        varexp = self.pca_var_exp.value()
        pca_bool = self.PCAbox.isChecked()

        r_ds = gdal.Open(data_ras.source())
        ras_dict = getFullRasterDict(r_ds)
        rasBands = rasterBandDescAslist(data_ras.source())

        trainingstarting = 'Training Model'
        print(trainingstarting)
        self.PrintBox.setText(trainingstarting)

        if self.withSelectedcheckBox.isChecked():
            train_dat = getTrainingDataFromFeatures(data_ras, selectedLayer, withSelected=True,
                                                    samplingRate=samplingRate, maxPerPoly=maxPixPoly)
        else:
            train_dat = getTrainingDataFromFeatures(data_ras, selectedLayer, withSelected=False,
                                                    samplingRate=samplingRate, maxPerPoly=maxPixPoly)

        bands = rasterBandDescAslist(data_ras.source())

        if self.parent.UseBandSelectionBox.isChecked():
            train_dat, bands = dropSelectedBandsforSupClass(train_dat, bandSelToList(self.labels_tab.stats_table),
                                                            bands)

        if self.lowestSample_CheckBox.isChecked():
            train_dat = balancedSamples(train_dat, take_min=True, n=maxClassPix)
        else:
            train_dat = balancedSamples(train_dat, take_min=False, n=maxClassPix)

        bool_arr = np.any(train_dat == ras_dict['NoData'], axis=1)

        labels, km, pca, fitdat = doPCA_kmeans(train_dat, bool_arr, nclust, varexp, pca_bool)
        k_dict = {'labels': labels, 'km': km, 'pca': pca, 'fitdat': fitdat,
                      'bool_arr': bool_arr, 'rasBands': rasBands, 'nclust': nclust}
        self.trainingK = k_dict
        print('added to gvars')

        return None
