from time import sleep

import pandas as pd
from osgeo import gdal
from scipy.stats import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split, StratifiedKFold

from PyQt5 import QtCore
from PyQt5.QtWidgets import QFileDialog
from qgis import processing
from qgis.core import QgsProject

from statmagic_backend.math.ai import make_fullConfMat
from statmagic_backend.math.sampling import balancedSamples,dropSelectedBandsforSupClass, randomSample
from statmagic_backend.extract.raster import extractBands, extractBandsInBounds, calc_array_mode
from statmagic_backend.geo.transform import boundingBoxToOffsets, geotFromOffsets

from .TabBase import TabBase
from ..fileops import gdalSave
from ..gui_helpers import *
from ..layerops import addLayerSymbolMutliClassGroup, addRFconfLayer, rasterBandDescAslist, bandSelToList, \
    getTrainingDataFromFeatures


class SupervisedTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Supervised")

        self.parent = parent

        ##### MODEL VALIDATION FRAME #####
        modelFrame, modelLayout = addFrame(self, "Grid", "Box", "Plain", 2, margins=5)
        modelLayout.setVerticalSpacing(0)
        # six rows, two columns
        addBigLabel(modelLayout, "Model Validation", align="Left", gridPos=(0,0))

        self.TestHoldPct_spinBox = addSpinBoxToGrid(modelFrame, "Withhold %", dtype=int,
                                                    value=20, min=0, max=100, gridPos=(1,0,3,1))

        self.Conf_Checkbox = addCheckbox(modelFrame, "Print Confusion Matrix", gridPos=(1,1))
        self.errors_CheckBox = addCheckbox(modelFrame, "Print Classification Report", gridPos=(2,1))
        self.BandImportance_CheckBox = addCheckbox(modelFrame, "Print Band Importance", gridPos=(3,1))

        self.samplingRatespinBox = addSpinBoxToGrid(modelFrame, "Sampling Rate",
                                                    dtype=int, value=50, min=1, max=100, gridPos=(4,0))
        self.max_pix_poly_spinBox = addSpinBoxToGrid(modelFrame, "Max Pixels / Polygon", dtype=int,
                                                     value=100, min=10, max=500, step=10, gridPos=(5,0))
        self.max_sample_spinBox = addSpinBoxToGrid(modelFrame, "Max Samples / Class",
                                                   dtype=int, value=250, min=50, max=10000, gridPos=(4,1))

        self.lowestSample_CheckBox = addCheckbox(modelFrame, "Use Smallest Class n", gridPos=(5,1))
        self.lowestSample_CheckBox.setLayoutDirection(QtCore.Qt.RightToLeft)

        addToParentLayout(modelFrame)

        ##### OPTIONAL MAP OUTPUTS FRAME #####
        optionalFrame, optionalLayout = addFrame(self, "Grid", "Box", "Plain", 2, margins=5)

        addBigLabel(optionalLayout, "Optional Map Outputs", align="Left", gridPos=(0,0))

        self.classProbsCheckBox = addCheckbox(optionalFrame, "Class Probabilities", gridPos=(1,0))
        self.confidenceCheckBox = addCheckbox(optionalFrame, "Confidence", gridPos=(1,1))

        addToParentLayout(optionalFrame)

        ##### INVISIBLE FRAME TO CONTAIN RESERVE FRAMES #####
        reserveFrame, reserveLayout = addFrame(self, "HBox", "NoFrame", "Plain", 3, margins=0)

        ##### RESERVE PIXELS FRAME #####
        pixelsFrame, pixelsLayout = addFrame(reserveFrame, "VBox", "Box", "Plain", 2, margins=5)

        addBigLabel(pixelsLayout, "Reserve Pixels Only")

        self.trainRFmodButton = addButton(pixelsFrame, "Train/Val RF Model", self.selectRFtrainPixel)
        self.withSelectedcheckBox = addCheckbox(pixelsFrame, "With Selected Polygons Only")

        pixelsBottomFrame, pixelsBottomLayout = addFrame(pixelsFrame, "HBox", "NoFrame", "Plain", 3)

        self.mapPredsButton = addButton(pixelsBottomFrame, "Map \n Predictions", self.selectRFapplyPixel)
        self.numKfoldsBox = addSpinBox(pixelsBottomFrame, "# KFolds", "VBox", dtype=int, value=1, min=1, step=2)

        addToParentLayout(pixelsBottomFrame)
        addToParentLayout(pixelsFrame)

        ##### RESERVE POLYGONS FRAME #####
        polygonsFrame, polygonsLayout = addFrame(reserveFrame, "VBox", "Box", "Plain", 2, margins=5)

        addBigLabel(polygonsLayout, "Reserve Polygons")

        self.randSelButton = addButton(polygonsFrame, "Train/Val RF Model", self.selectRFtrainPoly)
        self.numRFitersBox = addSpinBox(polygonsFrame, "Number of Random \n Polygon Iterations",
                                        dtype=int, value=1, min=1, step=2)

        self.mapMultiModelMode = addButton(polygonsFrame, "Map Predictions \n (mode if >1)", self.selectRFapplyPoly)

        addToParentLayout(polygonsFrame)
        addToParentLayout(reserveFrame)

        ##### PARAMETERS FRAME #####
        paramsFrame, paramsLayout = addFrame(self, "Grid", "Box", "Plain", 2, margins=(5,5,5,5))

        self.custom_RF_checkBox = addCheckbox(paramsFrame, "Use Custom Parameters", gridPos=(0,0))
        self.n_estimators_spinBox = addSpinBoxToGrid(paramsFrame, "n_estimators", dtype=int,
                                                     value=100, min=50, max=1000, step=50, gridPos=(1,0))

        self.max_features_comboBox = addComboBoxToGrid(paramsFrame, "max_features",
                                                       ["sqrt", "auto", "log2", "None"], gridPos=(2,0))
        self.max_features_comboBox.setEditable(True)
        self.max_features_comboBox.setMaxVisibleItems(5)

        self.max_depth_spinBox = addSpinBoxToGrid(paramsFrame, "max_depth",
                                                  dtype=int, min=2, max=100, gridPos=(1,1))

        self.min_sample_spinBox_2 = addSpinBoxToGrid(paramsFrame, "min_samp_split",
                                                     dtype=int, min=2, gridPos=(2,1))

        addToParentLayout(paramsFrame)

        ##### BOTTOM STUFF #####
        bottomFrame, bottomLayout = addFrame(self, "HBox", "NoFrame", "Plain", 3, margins=5)

        self.export_errMat_button = addButton(bottomFrame, "Export Validation Error Matrix", self.export_conf_mat)

        self.njob_box = addSpinBoxToGrid(bottomFrame, "n-jobs", dtype=int, min=1, max=16)

        addToParentLayout(bottomFrame)

        ##### VARIABLES SPECIFIC TO THIS TAB #####
        self.valset = {}
        self.pixel_rfmodel_list = []
        self.pixel_rfmodel = None
        self.poly_rfmodel_list = []
        self.poly_rfmodel = None

    def selectRFtrainPixel(self):
        num_folds = self.numKfoldsBox.value()
        if num_folds > 1:
            print(f"doing {num_folds} folds")
            self.buildRFmodelPixel_Kfolds()
        else:
            print("Doing one off validation")
            self.buildRFmodelPixelNoFold()

    def selectRFapplyPixel(self):
        num_iters = self.numKfoldsBox.value()
        if num_iters > 1:
            self.applyRFpreds_PixelFolded()
        else:
            self.applyRFpreds_PixelNoFold()

    def selectRFtrainPoly(self):
        num_iters = self.numRFitersBox.value()
        if num_iters > 1:
            print(f"doing {num_iters} iterations")
            self.buildRFmodelPolyMultiIter()
        else:
            print("Doing one off validation")
            self.buildRFmodelPolysOneOff()

    def selectRFapplyPoly(self):
        num_iters = self.numRFitersBox.value()
        if num_iters > 1:
            self.applyRFpredsPolyMultiple()
        else:
            self.applyRFpredsPolySingle()

    def export_conf_mat(self):
        filename = QFileDialog.getSaveFileName(self, "Select output file", "", '*.csv')[0] + '.csv'
        valdict = self.valset

        # target_names = 'find way'
        # label_dict = json.loads(self.labels_tab.PrintBox.text())
        target_names = self.labels_tab.PrintBox.text().split(",")   # TODO: not this

        conf_mat = make_fullConfMat(valdict['actual'], valdict['predicted'], target_names)
        conf_mat.to_csv(filename, index=False)
    
    def buildRFmodelPixelNoFold(self):
        selectedLayer = self.parent.comboBox_vector.currentLayer()
        selectedRas = self.parent.comboBox_raster.currentLayer()
        retain_pct = float(self.TestHoldPct_spinBox.value()) / 100

        samplingRate = self.samplingRatespinBox.value()
        maxPixPoly = self.max_pix_poly_spinBox.value()
        maxClassPix = self.max_sample_spinBox.value()
        njobs = self.njob_box.value()

        trainingstarting = 'Training Model'
        print(trainingstarting)
        self.labels_tab.PrintBox.setText(trainingstarting)

        if self.withSelectedcheckBox.isChecked():
            train_dat = getTrainingDataFromFeatures(selectedRas, selectedLayer, withSelected=True, samplingRate=samplingRate, maxPerPoly=maxPixPoly)
        else:
            train_dat = getTrainingDataFromFeatures(selectedRas, selectedLayer, withSelected=False, samplingRate=samplingRate, maxPerPoly=maxPixPoly)

        bands = rasterBandDescAslist(selectedRas.source())

        if self.parent.UseBandSelectionBox.isChecked():
            train_dat, bands = dropSelectedBandsforSupClass(train_dat, bandSelToList(self.labels_tab.stats_table), bands)

        if self.lowestSample_CheckBox.isChecked():
            train_dat = balancedSamples(train_dat, take_min=True, n=maxClassPix)
        else:
            train_dat = balancedSamples(train_dat, take_min=False, n=maxClassPix)

        labels = train_dat[:, 0]
        features = train_dat[:, 1:train_dat.shape[0]]
        train_features, test_features, train_labels, test_labels = \
            train_test_split(features, labels, test_size=retain_pct)
        if self.custom_RF_checkBox.isChecked():
            print("using custom parameters")
            n_estimates = self.n_estimators_spinBox.value()
            maxfeatures = self.max_features_comboBox.currentText()
            max_dpth = self.max_depth_spinBox.value()
            min_samp_split = self.min_sample_spinBox_2.value()
            rfmod = RandomForestClassifier(n_estimators=n_estimates, max_depth=max_dpth, max_features=maxfeatures,
                                           min_samples_split=min_samp_split, n_jobs=njobs)
        else:
            rfmod = RandomForestClassifier(n_jobs=njobs)

        rfmod.fit(train_features, train_labels)

        self.pixel_rfmodel = rfmod

        trainingdone = 'Model Training Finished'
        print(trainingdone)
        self.labels_tab.PrintBox.setText(trainingdone)

        if self.errors_CheckBox.isChecked() or self.Conf_CheckBox.isChecked() or \
                self.Conf_CheckBox.isChecked():
            y_pred = rfmod.predict(test_features)

        if self.errors_CheckBox.isChecked():
            print(' -------------- Classification Report ------------------')
            print('                                            ')
            print(classification_report(test_labels, y_pred, labels=list(np.unique((train_labels).astype('uint8')))))
            print('                                            ')

        if self.Conf_CheckBox.isChecked():
            print(' ---------- Confusion Matrix -------------')
            print('                                            ')
            cm = confusion_matrix(test_labels, y_pred)
            self.valset = {'actual': test_labels, 'predicted': y_pred}
            cmdf = pd.DataFrame(cm, columns=list(np.unique((train_labels).astype('uint8'))))
            cmdf.index = list(np.unique((train_labels).astype('uint8')))
            print(cmdf)

            print('                                                            ')

        if self.BandImportance_CheckBox.isChecked():
            print(' --------- Band Importance -----------------')
            print('                                            ')
            importances = list(rfmod.feature_importances_)  # List of tuples with variable and importance
            feature_importances = [(feature, round(importance, 2)) for feature, importance in
                                   zip(bands, importances)]  # Sort the feature importances by most important first
            feature_importances = sorted(feature_importances, key=lambda x: x[1],
                                         reverse=True)  # Print out the feature and importances
            for fi in feature_importances:
                print('{:15} Importance: {}'.format(*fi))

    def buildRFmodelPixel_Kfolds(self):
        selectedLayer = self.parent.comboBox_vector.currentLayer()
        selectedRas = self.parent.comboBox_raster.currentLayer()
        num_folds = self.numKfoldsBox.value()
        samplingRate = self.samplingRatespinBox.value()
        maxPixPoly = self.max_pix_poly_spinBox.value()
        retain_pct = self.TestHoldPct_spinBox.value()
        maxClassPix = self.max_sample_spinBox.value()
        njobs = self.njob_box.value()

        trainingstarting = 'Training Model'
        print(trainingstarting)
        self.labels_tab.PrintBox.setText(trainingstarting)

        if self.withSelectedcheckBox.isChecked():
            train_dat = getTrainingDataFromFeatures(selectedRas, selectedLayer, withSelected=True,
                                                    samplingRate=samplingRate, maxPerPoly=maxPixPoly)
        else:
            train_dat = getTrainingDataFromFeatures(selectedRas, selectedLayer, withSelected=False,
                                                    samplingRate=samplingRate, maxPerPoly=maxPixPoly)

        bands = rasterBandDescAslist(selectedRas.source())

        if self.parent.UseBandSelectionBox.isChecked():
            train_dat, bands = dropSelectedBandsforSupClass(train_dat, bandSelToList(self.labels_tab.stats_table), bands)

        if self.lowestSample_CheckBox.isChecked():
            train_dat = balancedSamples(train_dat, take_min=True, n=maxClassPix)
        else:
            train_dat = balancedSamples(train_dat, take_min=False, n=maxClassPix)

        train_dat, valdat = randomSample(train_dat, retain_pct)

        y = train_dat[:, 0]
        X = train_dat[:, 1:]

        skf = StratifiedKFold(n_splits=num_folds)
        skf.get_n_splits(X, y)

        band_imp_list = []
        # could append the test_labels and y_preds instead, then calculate error mat and class report on those
        test_label_list = []
        y_pred_list = []
        rfmod_list = []

        fold_count = 1
        for train_index, test_index in skf.split(X, y):
            print(f"Fold # {fold_count}")
            fold_count += 1
            x_train_fold, x_test_fold = X[train_index], X[test_index]
            y_train_fold, y_test_fold = y[train_index], y[test_index]

            if self.custom_RF_checkBox.isChecked():
                print("using custom parameters")
                n_estimates = self.n_estimators_spinBox.value()
                maxfeatures = self.max_features_comboBox.currentText()
                max_dpth = self.max_depth_spinBox.value()
                min_samp_split = self.min_sample_spinBox_2.value()
                rfmod = RandomForestClassifier(n_estimators=n_estimates, max_depth=max_dpth, max_features=maxfeatures,
                                               min_samples_split=min_samp_split, n_jobs=njobs)
            else:
                rfmod = RandomForestClassifier(n_jobs=njobs)

            rfmod.fit(x_train_fold, y_train_fold)
            y_pred = rfmod.predict(x_test_fold)

            band_imp_list.append(rfmod.feature_importances_)
            test_label_list.append(y_test_fold)
            y_pred_list.append(y_pred)
            rfmod_list.append(rfmod)

            if self.errors_CheckBox.isChecked():
                print(' -------------- Classification Report ------------------')
                print('                                            ')
                print(
                    classification_report(y_test_fold, y_pred, labels=list(np.unique((y_train_fold).astype('uint8')))))
                print('                                            ')

            if self.Conf_CheckBox.isChecked():
                print(' ---------- Confusion Matrix -------------')
                print('                                            ')
                cm = confusion_matrix(y_test_fold, y_pred)
                cmdf = pd.DataFrame(cm, columns=list(np.unique((y_train_fold).astype('uint8'))))
                cmdf.index = list(np.unique((y_train_fold).astype('uint8')))
                print(cmdf)
                print('                                                            ')
                # error_mat_list.append(cm)

            if self.BandImportance_CheckBox.isChecked():
                print(' --------- Band Importance -----------------')
                print('                                            ')
                importances = list(rfmod.feature_importances_)  # List of tuples with variable and importance
                feature_importances = [(feature, round(importance, 2)) for feature, importance in
                                       zip(bands, importances)]  # Sort the feature importances by most important first
                feature_importances = sorted(feature_importances, key=lambda x: x[1],
                                             reverse=True)  # Print out the feature and importances
                for fi in feature_importances:
                    print('{:15} Importance: {}'.format(*fi))

            print(f"############# END FOLD {fold_count}  ################################")

        folded_y_preds = np.concatenate(y_pred_list)
        folded_test_labels = np.concatenate(test_label_list)

        cm = (confusion_matrix(folded_test_labels, folded_y_preds) / num_folds).astype('uint16')

        cmdf = pd.DataFrame(cm, columns=list(np.unique((y).astype('uint8'))))
        cmdf.index = list(np.unique((y).astype('uint8')))
        print("########################################################################")
        print(f"############### AVERAGED ERROR MATRIX FROM {num_folds} FOLDS ################")
        print("########################################################################")
        print(cmdf)
        print('___________________________________________________')

        print(f"############### AVERAGED CLASSIFICATION REPORT FROM {num_folds} FOLDS ################")
        print(classification_report(folded_test_labels, folded_y_preds,
                                    labels=list(np.unique((y).astype('uint8')))))
        print('___________________________________________________')
        print(f"############### TOP BAND IMPORTANCES FROM AVERAGED  {num_folds} FOLDS ################")
        imps = np.vstack(band_imp_list).T
        ave_imp = np.mean(imps, axis=1)

        feature_importances = [(feature, round(importance, 2)) for feature, importance in
                               zip(bands, ave_imp)]  # Sort the feature importances by most important first
        feature_importances = sorted(feature_importances, key=lambda x: x[1],
                                     reverse=True)  # Print out the feature and importances

        for fi in feature_importances:
            print('{:15} Importance: {}'.format(*fi))

        self.pixel_rfmodel_list = rfmod_list

        print("------------------------------------------------------------------------------")
        print(f"############### VALIDATION FROM WITHHELD SAMPLES ################")
        print("-------------------------------------------------------------------------------")

        val_y, val_x = valdat[:, 0], valdat[:, 1:]
        pred_list = []
        for rfmodel in rfmod_list:
            val_pred = rfmodel.predict(val_x)
            pred_list.append(val_pred)

        predarr = np.stack(pred_list)
        mode = stats.mode(predarr)
        mode_pred = mode[0][0, :]
        cm = confusion_matrix(val_y, mode_pred)
        self.valset = {'actual': val_y, 'predicted': mode_pred}
        cmdf = pd.DataFrame(cm, columns=list(np.unique((val_y).astype('uint8'))))
        cmdf.index = list(np.unique((val_y).astype('uint8')))
        print(cmdf)

        print('---------')

        print(classification_report(val_y, mode_pred, labels=list(np.unique(val_y).astype('uint8'))))

    def applyRFpreds_PixelNoFold(self):
        selectedRas = self.parent.comboBox_raster.currentLayer()

        root = QgsProject.instance().layerTreeRoot()
        if root.findGroup('RF_predicts') == None:
            RFgroup = root.insertGroup(0, 'RF_predicts')
        else:
            RFgroup = root.findGroup('RF_predicts')

        r_ds = gdal.Open(selectedRas.source())
        geot = r_ds.GetGeoTransform()
        r_proj = r_ds.GetProjection()
        nodata = r_ds.GetRasterBand(1).GetNoDataValue()
        cellres = geot[1]
        rsizeX, rsizeY = r_ds.RasterXSize, r_ds.RasterYSize

        rfmod = self.pixel_rfmodel

        class_labels = list(rfmod.classes_)
        class_idxs = list(range(len(class_labels)))
        class_map_dict = dict(zip(class_idxs, class_labels))

        predstarting = 'Making Predictions'
        print(predstarting)
        self.labels_tab.PrintBox.setText(predstarting)

        if self.parent.ClusterWholeExtentBox.isChecked():
            layerName = 'Full_Extent_' + 'RF'

            if self.parent.UseBandSelectionBox.isChecked():
                bandList = bandSelToList(self.labels_tab.stats_table)
                dat = extractBands(bandList, r_ds)
            else:
                dat = r_ds.ReadAsArray()

            data_array = np.transpose(dat, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
            twoDshape = (data_array.shape[0] * data_array.shape[1], data_array.shape[2])
            pred_data = data_array.reshape(twoDshape)
            bool_arr = np.all(pred_data == nodata, axis=1)
            if np.count_nonzero(bool_arr == 1) < 1:
                print('not over no data values')
                probs = rfmod.predict_proba(pred_data) * 100  # Get the probabilities

                ## Getting the class from the prediction
                idx = np.argmax(probs, axis=1)  # find the column/index of the high prob
                labels = np.zeros(idx.shape, dtype='uint8')  # Initial array to put predictions in
                for k, v in class_map_dict.items():
                    labels[idx == k] = v  # Map values to the array
            else:
                idxr = bool_arr.reshape(pred_data.shape[0])
                pstack = pred_data[idxr == 0, :]
                probs = rfmod.predict_proba(pstack) * 100  # Get the probabilities
                idx = np.argmax(probs, axis=1)  # find the column/index of the high prob
                preds = np.zeros(idx.shape, dtype='uint8')  # Initial array to put predictions in
                for k, v in class_map_dict.items():
                    preds[idx == k] = v  # Map values to the array
                labels = np.zeros_like(bool_arr).astype('uint8')
                labels[~bool_arr] = preds
                labels[bool_arr] = 0

            preds = labels.reshape(rsizeY, rsizeX, 1)
            classout = np.transpose(preds, (0, 1, 2))[:, :, 0]

            if self.confidenceCheckBox.isChecked():
                conf = np.max(probs, axis=1)  # conf is good to go
                emConfs = np.zeros_like(bool_arr).astype('uint8')
                emConfs[~bool_arr] = conf
                emConfs[bool_arr] = 0
                confs = emConfs.reshape(rsizeY, rsizeX, 1)
                confout = np.transpose(confs, (0, 1, 2))[:, :, 0].astype('uint8')

            if self.classProbsCheckBox.isChecked():
                probholds = []
                numclass = probs.shape[1]
                for x in range(numclass):
                    emProbs = np.zeros_like(bool_arr).astype('uint8')
                    emProbs[~bool_arr] = probs[:, x]
                    emProbs[bool_arr] = 255
                    class_prob_arr2d = emProbs.reshape(rsizeY, rsizeX)
                    probholds.append(class_prob_arr2d)
                probstack = np.stack(probholds)

        else:
            layerName = 'Window_Extent_' + 'RF'

            bb = self.canvas.extent()
            bb.asWktCoordinates()
            bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
            offsets = boundingBoxToOffsets(bbc, geot)
            new_geot = geotFromOffsets(offsets[0], offsets[2], geot)
            geot = new_geot

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

            probs = rfmod.predict_proba(pred_data) * 100  # Get the probabilites

            ## Getting the class from the prediction
            idx = np.argmax(probs, axis=1)  # find the column/index of the high prob
            labels = np.zeros(idx.shape, dtype='uint8')  # Initial array to put predictions in
            for k, v in class_map_dict.items():
                labels[idx == k] = v  # Map values to the array

            preds = labels.reshape(sizeY, sizeX, 1)
            classout = np.transpose(preds, (0, 1, 2))[:, :, 0].astype('uint8')

            if self.confidenceCheckBox.isChecked():
                conf = np.max(probs, axis=1)  # conf is good to go
                confs = conf.reshape(sizeY, sizeX, 1)
                confout = np.transpose(confs, (0, 1, 2))[:, :, 0].astype('uint8')

            if self.classProbsCheckBox.isChecked():
                probholds = []
                numclass = probs.shape[1]
                for x in range(numclass):
                    class_prob_arr1d = probs[:, x]
                    class_prob_arr2d = class_prob_arr1d.reshape(sizeY, sizeX)
                    probholds.append(class_prob_arr2d)

                probstack = np.stack(probholds)

        savedLayer = gdalSave('RFpredict_', classout, gdal.GDT_Byte, geot, r_proj, 0)
        addLayerSymbolMutliClassGroup(savedLayer, layerName, RFgroup, np.unique(classout).tolist(), "Classes")

        if self.confidenceCheckBox.isChecked():
            confLayer = gdalSave("RFconf_", confout, gdal.GDT_Byte, geot, r_proj, 0)
            addRFconfLayer(confLayer, "RF_Conf", RFgroup)

        if self.classProbsCheckBox.isChecked():
            # Right here to update the band Descriptions
            classProbLayer = gdalSave("RFconf_", probstack, gdal.GDT_Byte, geot, r_proj, class_labels, 0)
            addRFconfLayer(classProbLayer, "RF_Prob_", RFgroup)

        predfinished = 'Predictions Mapped'
        print(predfinished)
        self.labels_tab.PrintBox.setText(predfinished)

    def applyRFpreds_PixelFolded(self):
        selectedRas = self.parent.comboBox_raster.currentLayer()

        root = QgsProject.instance().layerTreeRoot()
        if root.findGroup('RF_predicts') == None:
            RFgroup = root.insertGroup(0, 'RF_predicts')
        else:
            RFgroup = root.findGroup('RF_predicts')

        r_ds = gdal.Open(selectedRas.source())
        geot = r_ds.GetGeoTransform()
        r_proj = r_ds.GetProjection()
        nodata = r_ds.GetRasterBand(1).GetNoDataValue()
        cellres = geot[1]
        rsizeX, rsizeY = r_ds.RasterXSize, r_ds.RasterYSize

        rfmod_list = self.pixel_rfmodel_list

        class_labels = list(rfmod_list[0].classes_)
        class_idxs = list(range(len(class_labels)))
        class_map_dict = dict(zip(class_idxs, class_labels))

        predstarting = 'Making Predictions'
        print(predstarting)
        self.labels_tab.PrintBox.setText(predstarting)

        if self.parent.ClusterWholeExtentBox.isChecked():
            print("Trying Full")
            layerName = 'Full_Extent_' + 'RF'

            if self.parent.UseBandSelectionBox.isChecked():
                bandList = bandSelToList(self.labels_tab.stats_table)
                dat = extractBands(bandList, r_ds)
            else:
                dat = r_ds.ReadAsArray()

            pred_list = []
            conf_list = []
            prob_list = []

            for rfmod in rfmod_list:

                data_array = np.transpose(dat, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
                twoDshape = (data_array.shape[0] * data_array.shape[1], data_array.shape[2])
                pred_data = data_array.reshape(twoDshape)
                bool_arr = np.all(pred_data == nodata, axis=1)
                if np.count_nonzero(bool_arr == 1) < 1:
                    print('not over no data values')
                    probs = rfmod.predict_proba(pred_data) * 100  # Get the probabilities

                    ## Getting the class from the prediction
                    idx = np.argmax(probs, axis=1)  # find the column/index of the high prob
                    labels = np.zeros(idx.shape, dtype='uint8')  # Initial array to put predictions in
                    for k, v in class_map_dict.items():
                        labels[idx == k] = v  # Map values to the array
                else:
                    idxr = bool_arr.reshape(pred_data.shape[0])
                    pstack = pred_data[idxr == 0, :]
                    probs = rfmod.predict_proba(pstack) * 100  # Get the probabilities
                    idx = np.argmax(probs, axis=1)  # find the column/index of the high prob
                    preds = np.zeros(idx.shape, dtype='uint8')  # Initial array to put predictions in
                    for k, v in class_map_dict.items():
                        preds[idx == k] = v  # Map values to the array
                    labels = np.zeros_like(bool_arr).astype('uint8')
                    labels[~bool_arr] = preds
                    labels[bool_arr] = 0

                preds = labels.reshape(rsizeY, rsizeX, 1)
                classout = np.transpose(preds, (0, 1, 2))[:, :, 0].astype('uint8')
                pred_list.append(classout)

                if self.confidenceCheckBox.isChecked():
                    conf = np.max(probs, axis=1)  # conf is good to go
                    emConfs = np.zeros_like(bool_arr).astype('uint8')
                    emConfs[~bool_arr] = conf
                    emConfs[bool_arr] = 0
                    confs = emConfs.reshape(rsizeY, rsizeX, 1)
                    confout = np.transpose(confs, (0, 1, 2))[:, :, 0].astype('uint8')
                    conf_list.append(confout)

                if self.classProbsCheckBox.isChecked():
                    probholds = []
                    numclass = probs.shape[1]
                    for x in range(numclass):
                        emProbs = np.zeros_like(bool_arr).astype('uint8')
                        emProbs[~bool_arr] = probs[:, x]
                        emProbs[bool_arr] = 255

                        # class_prob_arr1d = probs[:, x]
                        class_prob_arr2d = emProbs.reshape(rsizeY, rsizeX)
                        probholds.append(class_prob_arr2d)

                    probstack = np.stack(probholds)
                    prob_list.append(probstack)

        else:
            layerName = 'Window_Extent_' + 'RF'

            bb = self.canvas.extent()
            bb.asWktCoordinates()
            bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
            offsets = boundingBoxToOffsets(bbc, geot)
            new_geot = geotFromOffsets(offsets[0], offsets[2], geot)
            geot = new_geot

            sizeX = int(((bbc[2] - bbc[0]) / cellres) + 1)
            sizeY = int(((bbc[3] - bbc[1]) / cellres) + 1)

            if self.parent.UseBandSelectionBox.isChecked():
                bandList = bandSelToList(self.labels_tab.stats_table)
                dat = extractBandsInBounds(bandList, r_ds, offsets[2], offsets[0], sizeX, sizeY)
            else:
                dat = r_ds.ReadAsArray(offsets[2], offsets[0], sizeX, sizeY)

            pred_list = []
            conf_list = []
            prob_list = []

            for rfmod in rfmod_list:

                data_array = np.transpose(dat, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
                twoDshape = (data_array.shape[0] * data_array.shape[1], data_array.shape[2])
                pred_data = data_array.reshape(twoDshape)

                probs = rfmod.predict_proba(pred_data) * 100  # Get the probabilities

                ## Getting the class from the prediction
                idx = np.argmax(probs, axis=1)  # find the column/index of the high prob
                labels = np.zeros(idx.shape, dtype='uint8')  # Initial array to put predictions in
                for k, v in class_map_dict.items():
                    labels[idx == k] = v  # Map values to the array

                preds = labels.reshape(sizeY, sizeX, 1)
                classout = np.transpose(preds, (0, 1, 2))[:, :, 0].astype('uint8')
                pred_list.append(classout)

                if self.confidenceCheckBox.isChecked():
                    conf = np.max(probs, axis=1)  # conf is good to go
                    confs = conf.reshape(sizeY, sizeX, 1)
                    confout = np.transpose(confs, (0, 1, 2))[:, :, 0].astype('uint8')
                    conf_list.append(confout)

                if self.classProbsCheckBox.isChecked():
                    probholds = []
                    numclass = probs.shape[1]
                    for x in range(numclass):
                        class_prob_arr1d = probs[:, x]
                        class_prob_arr2d = class_prob_arr1d.reshape(sizeY, sizeX)
                        probholds.append(class_prob_arr2d)

                    probstack = np.stack(probholds)
                    prob_list.append(probstack)

        mode_arr = calc_array_mode(pred_list)
        mode_layer = gdalSave('RFpredict_', mode_arr, gdal.GDT_Byte, geot, r_proj, 0)
        addLayerSymbolMutliClassGroup(mode_layer, 'Prediction_Mode', RFgroup, np.unique(classout).tolist(), "Classes")

        if self.confidenceCheckBox.isChecked():
            ave_conf_arr = np.mean(conf_list, axis=0).astype(np.int8)
            confLayer = gdalSave("RFconf_", ave_conf_arr, gdal.GDT_Byte, geot, r_proj, 0)
            addRFconfLayer(confLayer, "Ave_RF_Conf", RFgroup)

        if self.classProbsCheckBox.isChecked():
            # Right here to update the band Descriptions
            ave_prob_arr = np.mean(prob_list, axis=0).astype(np.int8)
            classProbLayer = gdalSave("RFconf_", ave_prob_arr, gdal.GDT_Byte, geot, r_proj, class_labels, 0)
            addRFconfLayer(classProbLayer, "Ave_RF_Prob_", RFgroup)

        predfinished = 'Predictions Mapped'
        print(predfinished)
        self.labels_tab.PrintBox.setText(predfinished)

    def buildRFmodelPolyMultiIter(self):
        selectedLayer = self.parent.comboBox_vector.currentLayer()
        selectedRas = self.parent.comboBox_raster.currentLayer()
        bands = rasterBandDescAslist(selectedRas.source())
        num_iters = self.numRFitersBox.value()
        val_pct = self.TestHoldPct_spinBox.value()
        train_pct = 100 - val_pct
        samplingRate = self.samplingRatespinBox.value()
        maxPixPoly = self.max_pix_poly_spinBox.value()
        maxClassPix = self.max_sample_spinBox.value()
        njobs = self.njob_box.value()
        params = {'FIELD': 'type_id', 'INPUT': selectedLayer, 'METHOD': 1, 'NUMBER': train_pct}

        band_imp_list = []
        test_label_list = []
        y_pred_list = []
        rfmod_list = []
        for iter_ in range(1, num_iters+1):
            print("---------------------------------------------------")
            print(f"Iteration # {iter_}")
            # Take random selection within each class type
            processing.run("qgis:randomselectionwithinsubsets", params)

            # Gather Training data from Selected % of Polygons per class
            train_dat = getTrainingDataFromFeatures(selectedRas, selectedLayer, withSelected=True, samplingRate=samplingRate, maxPerPoly=maxPixPoly)

            if self.parent.UseBandSelectionBox.isChecked():
                train_dat, bands = dropSelectedBandsforSupClass(train_dat, bandSelToList(self.labels_tab.stats_table), bands)

            if self.lowestSample_CheckBox.isChecked():
                train_dat = balancedSamples(train_dat, take_min=True, n=maxClassPix)
            else:
                train_dat = balancedSamples(train_dat, take_min=False, n=maxClassPix)

            train_labels = train_dat[:, 0]
            train_features = train_dat[:, 1:train_dat.shape[0]]

            if self.custom_RF_checkBox.isChecked():
                print("using custom parameters")
                n_estimates = self.n_estimators_spinBox.value()
                maxfeatures = self.max_features_comboBox.currentText()
                max_dpth = self.max_depth_spinBox.value()
                min_samp_split = self.min_sample_spinBox_2.value()
                rfmod = RandomForestClassifier(n_estimators=n_estimates, max_depth=max_dpth, max_features=maxfeatures,
                                               min_samples_split=min_samp_split, n_jobs=njobs)
            else:
                rfmod = RandomForestClassifier(n_jobs=njobs)

            rfmod.fit(train_features, train_labels)
            rfmod_list.append(rfmod)

            band_imp_list.append(rfmod.feature_importances_)

            # Gather Test data from inverted selection of features for validation
            selectedLayer.invertSelection()
            test_dat = getTrainingDataFromFeatures(selectedRas, selectedLayer, withSelected=True, samplingRate=samplingRate, maxPerPoly=maxPixPoly)
            if self.parent.UseBandSelectionBox.isChecked():
                test_dat, dontUsebands = dropSelectedBandsforSupClass(test_dat, bandSelToList(self.labels_tab.stats_table), bands)
            test_labels = test_dat[:, 0]
            test_features = test_dat[:, 1:test_dat.shape[0]]
            y_pred = rfmod.predict(test_features)
            test_label_list.append(test_labels)
            y_pred_list.append(y_pred)

            if self.errors_CheckBox.isChecked():
                print(' -------------- Classification Report ------------------')
                print('                                            ')
                print(classification_report(test_labels, y_pred, labels=list(np.unique((train_labels).astype('uint8')))))
                print('                                            ')

            if self.Conf_CheckBox.isChecked():
                print(' ---------- Confusion Matrix -------------')
                print('                                            ')
                cm = confusion_matrix(test_labels, y_pred)
                cmdf = pd.DataFrame(cm, columns=list(np.unique((train_labels).astype('uint8'))))
                cmdf.index = list(np.unique((train_labels).astype('uint8')))
                print(cmdf)
                print('                                                            ')
                # error_mat_list.append(cm)

            if self.BandImportance_CheckBox.isChecked():
                print(' --------- Band Importance -----------------')
                print('                                            ')
                importances = list(rfmod.feature_importances_)  # List of tuples with variable and importance
                feature_importances = [(feature, round(importance, 2)) for feature, importance in
                                       zip(bands, importances)]  # Sort the feature importances by most important first
                feature_importances = sorted(feature_importances, key=lambda x: x[1],
                                             reverse=True)  # Print out the feature and importances
                for fi in feature_importances:
                    print('{:15} Importance: {}'.format(*fi))

            print(f"############# END SHUFFLE {iter_}  ################################")

        folded_y_preds = np.concatenate(y_pred_list)
        folded_test_labels = np.concatenate(test_label_list)

        cm = (confusion_matrix(folded_test_labels, folded_y_preds)/num_iters).astype('uint16')
        self.valset = {'actual': folded_test_labels, 'predicted': folded_y_preds}
        cmdf = pd.DataFrame(cm, columns=list(np.unique((train_labels).astype('uint8'))))
        cmdf.index = list(np.unique((train_labels).astype('uint8')))
        print("########################################################################")
        print(f"############### AVERAGED ERROR MATRIX FROM {num_iters} RANDOM POLYGON SHUFFLES ################")
        print("########################################################################")
        print(cmdf)
        print('___________________________________________________')

        print(f"############### AVERAGED CLASSIFICATION REPORT FROM {num_iters} RANDOM POLYGON SHUFFLES ################")
        print(classification_report(folded_test_labels, folded_y_preds, labels=list(np.unique((train_labels).astype('uint8')))))
        print('___________________________________________________')
        print(f"############### TOP BAND IMPORTANCES FROM AVERAGED  {num_iters} RANDOM POLYGON SHUFFLES ################")
        imps = np.vstack(band_imp_list).T
        ave_imp = np.mean(imps, axis=1)

        feature_importances = [(feature, round(importance, 2)) for feature, importance in
                               zip(bands, ave_imp)]  # Sort the feature importances by most important first
        feature_importances = sorted(feature_importances, key=lambda x: x[1],
                                     reverse=True)  # Print out the feature and importances

        for fi in feature_importances:
            print('{:15} Importance: {}'.format(*fi))

        self.poly_rfmodel_list = rfmod_list

    def buildRFmodelPolysOneOff(self):
        selectedLayer = self.parent.comboBox_vector.currentLayer()
        selectedRas = self.parent.comboBox_raster.currentLayer()
        samplingRate = self.samplingRatespinBox.value()
        maxPixPoly = self.max_pix_poly_spinBox.value()
        maxClassPix = self.max_sample_spinBox.value()
        bands = rasterBandDescAslist(selectedRas.source())
        val_pct = self.TestHoldPct_spinBox.value()
        train_pct = 100 - val_pct
        njobs = self.njob_box.value()
        params = {'FIELD': 'type_id', 'INPUT': selectedLayer, 'METHOD': 1, 'NUMBER': train_pct}
        processing.run("qgis:randomselectionwithinsubsets", params)

        trainingstarting = f'Training Model with now selected polygons. One off test'
        print(trainingstarting)
        self.labels_tab.PrintBox.setText(trainingstarting)

        # Gather Training data from Selected % of Polygons per class
        train_dat = getTrainingDataFromFeatures(selectedRas, selectedLayer, withSelected=True, samplingRate=samplingRate, maxPerPoly=maxPixPoly)

        if self.parent.UseBandSelectionBox.isChecked():
            train_dat, bands = dropSelectedBandsforSupClass(train_dat, bandSelToList(self.labels_tab.stats_table), bands)

        if self.lowestSample_CheckBox.isChecked():
            train_dat = balancedSamples(train_dat, take_min=True, n=maxClassPix)
        else:
            train_dat = balancedSamples(train_dat, take_min=False, n=maxClassPix)
        train_labels = train_dat[:, 0]
        train_features = train_dat[:, 1:train_dat.shape[0]]
        if self.custom_RF_checkBox.isChecked():
            print("using custom parameters")
            n_estimates = self.n_estimators_spinBox.value()
            maxfeatures = self.max_features_comboBox.currentText()
            max_dpth = self.max_depth_spinBox.value()
            min_samp_split = self.min_sample_spinBox_2.value()
            rfmod = RandomForestClassifier(n_estimators=n_estimates, max_depth=max_dpth, max_features=maxfeatures,
                                           min_samples_split=min_samp_split, n_jobs=njobs)
        else:
            rfmod = RandomForestClassifier(n_jobs=njobs)

        rfmod.fit(train_features, train_labels)

        # self.['rfmodel'] = rfmod
        self.poly_rfmodel = rfmod

        trainingdone = 'Model Training Finished'
        print(trainingdone)
        self.labels_tab.PrintBox.setText(trainingdone)

        if self.errors_CheckBox.isChecked() or self.Conf_CheckBox.isChecked():
            validatingstring = 'Validating pixels in the now selected polygons'
            print(validatingstring)
            self.labels_tab.PrintBox.setText(validatingstring)
            # Gather Test data from inverted selection of features
            selectedLayer.invertSelection()
            sleep(1)
            test_dat = getTrainingDataFromFeatures(selectedRas, selectedLayer, withSelected=True, samplingRate=samplingRate, maxPerPoly=maxPixPoly)
            if self.parent.UseBandSelectionBox.isChecked():
                test_dat, dontUsebands = dropSelectedBandsforSupClass(test_dat, bandSelToList(self.labels_tab.stats_table),
                                                                bands)
            test_labels = test_dat[:, 0]
            test_features = test_dat[:, 1:test_dat.shape[0]]
            y_pred = rfmod.predict(test_features)

        if self.errors_CheckBox.isChecked():
            print(' -------------- Classification Report ------------------')
            print('                                            ')
            print(classification_report(test_labels, y_pred, labels=list(np.unique((train_labels).astype('uint8')))))
            print('                                            ')

        if self.Conf_CheckBox.isChecked():
            print(' ---------- Confusion Matrix -------------')
            print('                                            ')
            cm = confusion_matrix(test_labels, y_pred)
            self.valset = {'actual': test_labels, 'predicted': y_pred}
            cmdf = pd.DataFrame(cm, columns=list(np.unique((train_labels).astype('uint8'))))
            cmdf.index = list(np.unique((train_labels).astype('uint8')))
            print(cmdf)

            print('                                                            ')

        if self.BandImportance_CheckBox.isChecked():
            print(' --------- Band Importance -----------------')
            print('                                            ')
            importances = list(rfmod.feature_importances_)  # List of tuples with variable and importance
            feature_importances = [(feature, round(importance, 2)) for feature, importance in
                                   zip(bands, importances)]  # Sort the feature importances by most important first
            feature_importances = sorted(feature_importances, key=lambda x: x[1],
                                         reverse=True)  # Print out the feature and importances
            for fi in feature_importances:
                print('{:15} Importance: {}'.format(*fi))

    def applyRFpredsPolyMultiple(self):
        selectedRas = self.parent.comboBox_raster.currentLayer()

        root = QgsProject.instance().layerTreeRoot()
        if root.findGroup('RF_predicts') == None:
            RFgroup = root.insertGroup(0, 'RF_predicts')
        else:
            RFgroup = root.findGroup('RF_predicts')

        r_ds = gdal.Open(selectedRas.source())
        geot = r_ds.GetGeoTransform()
        r_proj = r_ds.GetProjection()
        nodata = r_ds.GetRasterBand(1).GetNoDataValue()
        cellres = geot[1]
        rsizeX, rsizeY = r_ds.RasterXSize, r_ds.RasterYSize

        rfmod_list = self.poly_rfmodel_list

        class_labels = list(rfmod_list[0].classes_)
        class_idxs = list(range(len(class_labels)))
        class_map_dict = dict(zip(class_idxs, class_labels))

        predstarting = 'Making Predictions'
        print(predstarting)
        self.labels_tab.PrintBox.setText(predstarting)

        if self.parent.ClusterWholeExtentBox.isChecked():
            print("Trying Full")
            layerName = 'Full_Extent_' + 'RF'

            if self.parent.UseBandSelectionBox.isChecked():
                bandList = bandSelToList(self.labels_tab.stats_table)
                dat = extractBands(bandList, r_ds)
            else:
                dat = r_ds.ReadAsArray()

            pred_list = []
            conf_list = []
            prob_list = []

            for rfmod in rfmod_list:

                data_array = np.transpose(dat, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
                twoDshape = (data_array.shape[0] * data_array.shape[1], data_array.shape[2])
                pred_data = data_array.reshape(twoDshape)
                bool_arr = np.all(pred_data == nodata, axis=1)
                if np.count_nonzero(bool_arr == 1) < 1:
                    print('not over no data values')
                    probs = rfmod.predict_proba(pred_data) * 100  # Get the probabilities

                    ## Getting the class from the prediction
                    idx = np.argmax(probs, axis=1)  # find the column/index of the high prob
                    labels = np.zeros(idx.shape, dtype='uint8')  # Initial array to put predictions in
                    for k, v in class_map_dict.items():
                        labels[idx == k] = v  # Map values to the array
                else:
                    idxr = bool_arr.reshape(pred_data.shape[0])
                    pstack = pred_data[idxr == 0, :]
                    probs = rfmod.predict_proba(pstack) * 100  # Get the probabilities
                    idx = np.argmax(probs, axis=1)  # find the column/index of the high prob
                    preds = np.zeros(idx.shape, dtype='uint8')  # Initial array to put predictions in
                    for k, v in class_map_dict.items():
                        preds[idx == k] = v  # Map values to the array
                    labels = np.zeros_like(bool_arr).astype('uint8')
                    labels[~bool_arr] = preds
                    labels[bool_arr] = 0

                preds = labels.reshape(rsizeY, rsizeX, 1)
                classout = np.transpose(preds, (0, 1, 2))[:, :, 0].astype('uint8')
                pred_list.append(classout)

                if self.confidenceCheckBox.isChecked():
                    conf = np.max(probs, axis=1)  # conf is good to go
                    emConfs = np.zeros_like(bool_arr).astype('uint8')
                    emConfs[~bool_arr] = conf
                    emConfs[bool_arr] = 0
                    confs = emConfs.reshape(rsizeY, rsizeX, 1)
                    confout = np.transpose(confs, (0, 1, 2))[:, :, 0].astype('uint8')
                    conf_list.append(confout)

                if self.classProbsCheckBox.isChecked():
                    probholds = []
                    numclass = probs.shape[1]
                    for x in range(numclass):
                        emProbs = np.zeros_like(bool_arr).astype('uint8')
                        emProbs[~bool_arr] = probs[:, x]
                        emProbs[bool_arr] = 255

                        # class_prob_arr1d = probs[:, x]
                        class_prob_arr2d = emProbs.reshape(rsizeY, rsizeX)
                        probholds.append(class_prob_arr2d)

                    probstack = np.stack(probholds)
                    prob_list.append(probstack)

        else:
            layerName = 'Window_Extent_' + 'RF'

            bb = self.canvas.extent()
            bb.asWktCoordinates()
            bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
            offsets = boundingBoxToOffsets(bbc, geot)
            new_geot = geotFromOffsets(offsets[0], offsets[2], geot)
            geot = new_geot

            sizeX = int(((bbc[2] - bbc[0]) / cellres) + 1)
            sizeY = int(((bbc[3] - bbc[1]) / cellres) + 1)

            if self.parent.UseBandSelectionBox.isChecked():
                bandList = bandSelToList(self.labels_tab.stats_table)
                dat = extractBandsInBounds(bandList, r_ds, offsets[2], offsets[0], sizeX, sizeY)
            else:
                dat = r_ds.ReadAsArray(offsets[2], offsets[0], sizeX, sizeY)

            pred_list = []
            conf_list = []
            prob_list = []

            for rfmod in rfmod_list:

                data_array = np.transpose(dat, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
                twoDshape = (data_array.shape[0] * data_array.shape[1], data_array.shape[2])
                pred_data = data_array.reshape(twoDshape)

                probs = rfmod.predict_proba(pred_data) * 100  # Get the probabilities

                ## Getting the class from the prediction
                idx = np.argmax(probs, axis=1)  # find the column/index of the high prob
                labels = np.zeros(idx.shape, dtype='uint8')  # Initial array to put predictions in
                for k, v in class_map_dict.items():
                    labels[idx == k] = v  # Map values to the array

                preds = labels.reshape(sizeY, sizeX, 1)
                classout = np.transpose(preds, (0, 1, 2))[:, :, 0].astype('uint8')
                pred_list.append(classout)


                if self.confidenceCheckBox.isChecked():
                    conf = np.max(probs, axis=1)  # conf is good to go
                    confs = conf.reshape(sizeY, sizeX, 1)
                    confout = np.transpose(confs, (0, 1, 2))[:, :, 0].astype('uint8')
                    conf_list.append(confout)

                if self.classProbsCheckBox.isChecked():
                    probholds = []
                    numclass = probs.shape[1]
                    for x in range(numclass):
                        class_prob_arr1d = probs[:, x]
                        class_prob_arr2d = class_prob_arr1d.reshape(sizeY, sizeX)
                        probholds.append(class_prob_arr2d)

                    probstack = np.stack(probholds)
                    prob_list.append(probstack)

        mode_arr = calc_array_mode(pred_list)
        mode_layer = gdalSave('RFpredict_', mode_arr, gdal.GDT_Byte, geot, r_proj, 0)
        addLayerSymbolMutliClassGroup(mode_layer, 'Prediction_Mode', RFgroup, np.unique(classout).tolist(), "Classes")

        if self.confidenceCheckBox.isChecked():
            ave_conf_arr = np.mean(conf_list, axis=0).astype(np.int8)
            confLayer = gdalSave("RFconf_", ave_conf_arr, gdal.GDT_Byte, geot, r_proj, 0)
            addRFconfLayer(confLayer, "Ave_RF_Conf", RFgroup)

        if self.classProbsCheckBox.isChecked():
            # Right here to update the band Descriptions
            ave_prob_arr = np.mean(prob_list, axis=0).astype(np.int8)
            classProbLayer = gdalSave("RFconf_", ave_prob_arr, gdal.GDT_Byte, geot, r_proj, class_labels, 0)
            addRFconfLayer(classProbLayer, "Ave_RF_Prob_", RFgroup)

        predfinished = 'Predictions Mapped'
        print(predfinished)
        self.labels_tab.PrintBox.setText(predfinished)

    def applyRFpredsPolySingle(self):
        selectedRas = self.parent.comboBox_raster.currentLayer()

        root = QgsProject.instance().layerTreeRoot()
        if root.findGroup('RF_predicts') == None:
            RFgroup = root.insertGroup(0, 'RF_predicts')
        else:
            RFgroup = root.findGroup('RF_predicts')

        r_ds = gdal.Open(selectedRas.source())
        geot = r_ds.GetGeoTransform()
        r_proj = r_ds.GetProjection()
        nodata = r_ds.GetRasterBand(1).GetNoDataValue()
        cellres = geot[1]
        rsizeX, rsizeY = r_ds.RasterXSize, r_ds.RasterYSize

        rfmod = self.poly_rfmodel

        class_labels = list(rfmod.classes_)
        class_idxs = list(range(len(class_labels)))
        class_map_dict = dict(zip(class_idxs, class_labels))

        predstarting = 'Making Predictions'
        print(predstarting)
        self.labels_tab.PrintBox.setText(predstarting)

        if self.parent.ClusterWholeExtentBox.isChecked():
            layerName = 'Full_Extent_' + 'RF'

            if self.parent.UseBandSelectionBox.isChecked():
                bandList = bandSelToList(self.labels_tab.stats_table)
                dat = extractBands(bandList, r_ds)
            else:
                dat = r_ds.ReadAsArray()

            data_array = np.transpose(dat, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
            twoDshape = (data_array.shape[0] * data_array.shape[1], data_array.shape[2])
            pred_data = data_array.reshape(twoDshape)
            bool_arr = np.all(pred_data == nodata, axis=1)
            if np.count_nonzero(bool_arr == 1) < 1:
                print('not over no data values')
                probs = rfmod.predict_proba(pred_data) * 100  # Get the probabilities

                ## Getting the class from the prediction
                idx = np.argmax(probs, axis=1)  # find the column/index of the high prob
                labels = np.zeros(idx.shape, dtype='uint8')  # Initial array to put predictions in
                for k, v in class_map_dict.items():
                    labels[idx == k] = v  # Map values to the array
            else:
                idxr = bool_arr.reshape(pred_data.shape[0])
                pstack = pred_data[idxr == 0, :]
                probs = rfmod.predict_proba(pstack) * 100  # Get the probabilities
                idx = np.argmax(probs, axis=1)  # find the column/index of the high prob
                preds = np.zeros(idx.shape, dtype='uint8')  # Initial array to put predictions in
                for k, v in class_map_dict.items():
                    preds[idx == k] = v  # Map values to the array
                labels = np.zeros_like(bool_arr).astype('uint8')
                labels[~bool_arr] = preds
                labels[bool_arr] = 0

            preds = labels.reshape(rsizeY, rsizeX, 1)
            classout = np.transpose(preds, (0, 1, 2))[:, :, 0]

            if self.confidenceCheckBox.isChecked():
                conf = np.max(probs, axis=1)  # conf is good to go
                emConfs = np.zeros_like(bool_arr).astype('uint8')
                emConfs[~bool_arr] = conf
                emConfs[bool_arr] = 0
                confs = emConfs.reshape(rsizeY, rsizeX, 1)
                confout = np.transpose(confs, (0, 1, 2))[:, :, 0].astype('uint8')

            if self.classProbsCheckBox.isChecked():
                probholds = []
                numclass = probs.shape[1]
                for x in range(numclass):
                    emProbs = np.zeros_like(bool_arr).astype('uint8')
                    emProbs[~bool_arr] = probs[:, x]
                    emProbs[bool_arr] = 255
                    class_prob_arr2d = emProbs.reshape(rsizeY, rsizeX)
                    probholds.append(class_prob_arr2d)
                probstack = np.stack(probholds)

        else:
            layerName = 'Window_Extent_' + 'RF'

            bb = self.canvas.extent()
            bb.asWktCoordinates()
            bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
            offsets = boundingBoxToOffsets(bbc, geot)
            new_geot = geotFromOffsets(offsets[0], offsets[2], geot)
            geot = new_geot

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

            probs = rfmod.predict_proba(pred_data) * 100  # Get the probabilites

            ## Getting the class from the prediction
            idx = np.argmax(probs, axis=1)  # find the column/index of the high prob
            labels = np.zeros(idx.shape, dtype='uint8')  # Initial array to put predictions in
            for k, v in class_map_dict.items():
                labels[idx == k] = v  # Map values to the array

            preds = labels.reshape(sizeY, sizeX, 1)
            classout = np.transpose(preds, (0, 1, 2))[:, :, 0].astype('uint8')

            if self.confidenceCheckBox.isChecked():
                conf = np.max(probs, axis=1)  # conf is good to go
                confs = conf.reshape(sizeY, sizeX, 1)
                confout = np.transpose(confs, (0, 1, 2))[:, :, 0].astype('uint8')

            if self.classProbsCheckBox.isChecked():
                probholds = []
                numclass = probs.shape[1]
                for x in range(numclass):
                    class_prob_arr1d = probs[:, x]
                    class_prob_arr2d = class_prob_arr1d.reshape(sizeY, sizeX)
                    probholds.append(class_prob_arr2d)

                probstack = np.stack(probholds)

        savedLayer = gdalSave('RFpredict_', classout, gdal.GDT_Byte, geot, r_proj, 0)
        addLayerSymbolMutliClassGroup(savedLayer, layerName, RFgroup, np.unique(classout).tolist(), "Classes")

        if self.confidenceCheckBox.isChecked():
            confLayer = gdalSave("RFconf_", confout, gdal.GDT_Byte, geot, r_proj, 0)
            addRFconfLayer(confLayer, "RF_Conf", RFgroup)

        if self.classProbsCheckBox.isChecked():
            # Right here to update the band Descriptions
            classProbLayer = gdalSave("RFconf_", probstack, gdal.GDT_Byte, geot, r_proj, class_labels, 0)
            addRFconfLayer(classProbLayer, "RF_Prob_", RFgroup)

        predfinished = 'Predictions Mapped'
        print(predfinished)
        self.labels_tab.PrintBox.setText(predfinished)
