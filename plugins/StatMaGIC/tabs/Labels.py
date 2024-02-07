# import tempfile
# from pathlib import Path
#
# import pandas as pd
# from PyQt5 import QtWidgets
# from PyQt5.QtWidgets import QTableWidgetItem, QFileDialog
# from osgeo import gdal
# from qgis._core import QgsProject
#
# from statmagic_backend.extract.raster import extractBands, extractBandsInBounds, RasMatcha, sdMatchSomeInStack, RasBoreMatch
# from statmagic_backend.geo.transform import boundingBoxToOffsets, geotFromOffsets
# from statmagic_backend.maths.sampling import label_count
#
# from .TabBase import TabBase
# from ..fileops import gdalSave
# from ..gui_helpers import *
# from ..layerops import ExtractRasterValuesFromSelectedFeature, rasterBandDescAslist, doClassIDfield, makeTempLayer, \
#     addLayerSymbol, getTrainingDataFromFeatures, bandSelToList, bands2indices, addLayerSymbolGroup, \
#     createClassCoverageList, createCrossClassList, addLayerSymbolMutliClassGroup
# from ..plotting import multispec_scatter
#
#
# class LabelsTab(TabBase):
#     def __init__(self, parent, tabWidget):
#         super().__init__(parent, tabWidget, "Labels")
#
#         self.parent = parent
#
#         ##### TOP BUTTONS #####
#         topFrame, topLayout = addFrame(self, "HBox", "NoFrame", "Plain", 3)
#         topLayout.setSpacing(5)
#
#         self.get_stats_button = addButton(topFrame, "Get Band Stats", self.fillStatBoxFromSelectedPoly)
#         self.Butrun_ZS = addButton(topFrame, "Get Matches", self.applyStdReturnMatchLayer)
#         self.MakeTempLayer = addButton(topFrame, "Make Train Layer", self.makeTempLayer)
#
#         addToParentLayout(topFrame)
#
#         ##### STATS TABLE AND RIGHT BUTTONS #####
#         tableFrame, tableLayout = addFrame(self, "Grid", "NoFrame", "Plain", 3)
#         tableLayout.setSpacing(5)
#
#         self.stats_table = addTable(tableFrame, "Box", "Raised", cols=0, rows=0, gridPos=(0,0,5,1))
#
#         self.refresh_col1_button = addButton(tableFrame, "Refresh Band \n Selection", self.RefreshBandSelection, gridPos=(0,1))
#         self.refreshTableButton = addButton(tableFrame, "Refresh Table", self.RefreshTable, gridPos=(1,1))
#         self.PlotData = addButton(tableFrame, "Spectral Plot \n With Selected", self.makeSpectralPlot, gridPos=(2,1))
#         self.summary_button = addButton(tableFrame, "Print Summary", self.summarize_training, gridPos=(3,1))
#         self.exportTrainingButton = addButton(tableFrame, "Export \n Training \n Data", self.saveTrainingDataOut, gridPos=(4,1))
#
#         addToParentLayout(tableFrame)
#
#         ##### IMMEDIATELY BELOW THE TABLE #####
#         stdevFrame, stdevLayout = addFrame(self, "HBox", "NoFrame", "Plain", 3)
#
#         self.ApplyStdevMatch = addButton(stdevFrame, "Return Stdev Matches", self.constantSTdevMatch)
#         self.StdevInputBox1 = addSpinBox(stdevFrame, "", dtype=float, value=2, min=0.25, max=10, step=0.25)
#         self.MinBandMatch = addSpinBox(stdevFrame, "Min # Bands \n to Match", "VBox")
#
#         addToParentLayout(stdevFrame)
#
#         ##### BOTTOM STUFF #####
#         bottomFrame, bottomLayout = addFrame(self, "Grid", "NoFrame", "Plain", 3)
#         bottomLayout.setSpacing(5)
#
#         self.evaluatePolygons = addButton(bottomFrame, "Evaluate Polygons", self.evaluteTrainingPolygons, gridPos=(0,0))
#         self.MinMaxMatch_button = addButton(bottomFrame, "Min/Max Match", self.returnBoreMatch, gridPos=(1,0))
#
#         self.PrintBox = QtWidgets.QTextEdit(bottomFrame)
#         bottomLayout.addWidget(self.PrintBox, 0, 1, 2, 1)
#
#         addToParentLayout(bottomFrame)
#
#     def fillStatBoxFromSelectedPoly(self):
#         selectedLayer = self.parent.comboBox_vector.currentLayer()
#         selectedRas = self.parent.comboBox_raster.currentLayer()
#         sel = selectedLayer.selectedFeatures()  # returns a list of selected features
#         feat = sel[0]  # Returns the first QgsFeature
#         dat = ExtractRasterValuesFromSelectedFeature(selectedRas, selectedLayer, feat)
#         means = dat.mean(axis=1)
#         stds = dat.std(axis=1)
#         l = [[x, y] for x, y in zip(means, stds)]
#
#         qTable = self.stats_table
#         bdescs = rasterBandDescAslist(selectedRas.source())
#         data = l
#         nb_row = len(data)
#         nb_col = 5
#         qTable.setColumnCount(nb_col)
#         qTable.setColumnWidth(0, 80)
#         qTable.setColumnWidth(1, 50)
#         qTable.setColumnWidth(2, 80)
#         qTable.setColumnWidth(3, 50)
#         qTable.setColumnWidth(4, 50)
#         qTable.setHorizontalHeaderLabels([u'Band Name', u'Select', u'Mean', u'SD', u'Factor'])
#
#         for (idx, dat), desc in zip(enumerate(data), bdescs):
#             qTable.setItem(idx, 0, QTableWidgetItem(desc))
#             qTable.setItem(idx, 1, QTableWidgetItem('1'))
#             qTable.setItem(idx, 2, QTableWidgetItem(str(dat[0])))
#             qTable.setItem(idx, 3, QTableWidgetItem(str(dat[1])))
#             qTable.setItem(idx, 4, QTableWidgetItem(''))
#
#     def applyStdReturnMatchLayer(self):
#         selectedLayer = self.parent.comboBox_vector.currentLayer()
#         doClassIDfield(selectedLayer)
#
#         sel = selectedLayer.selectedFeatures()
#         feat = sel[0]
#         classid = feat['type_id']
#         fid = feat['Class_ID']
#         layername = 'Class_' + str(classid) + '_CID_' + str(fid) + '_Manual_Matches'
#
#         qTable = self.stats_table
#         tabLen = qTable.rowCount()
#         vallist = []
#         # Here's where to Figure out what bands are selected
#         # Could turn this into a function that just returns the value list, or list of bands to use
#         for i in range(tabLen):
#             if qTable.item(i,4).text():
#                 mean = float(qTable.item(i,2).text())
#                 std = float(qTable.item(i,3).text())
#                 multiplier = float(qTable.item(i,4).text())
#                 blist = [i+1, mean, std, std * multiplier]
#                 vallist.append(blist)
#             else:
#                 print("Band not used")
#
#         selectedRas = self.parent.comboBox_raster.currentLayer()
#         r_ds = gdal.Open(selectedRas.source())
#         geot = r_ds.GetGeoTransform()
#         r_proj = r_ds.GetProjection()
#
#         ms = [RasMatcha(j, r_ds) for j in vallist]
#         boolstack = np.vstack([ms])
#         allmatch = np.all(boolstack, axis=0).astype(np.uint8)
#         matchout = np.where(allmatch, classid, 0)
#
#         savedLayer = gdalSave('bandStats_Match', matchout, gdal.GDT_Byte, geot, r_proj, 0)
#         addLayerSymbol(savedLayer, layername, classid, "Classes")
#
#     def makeTempLayer(self):
#         selectedRas = self.parent.comboBox_raster.currentLayer()
#         r_ds = gdal.Open(selectedRas.source())
#         r_proj = r_ds.GetProjection()
#         makeTempLayer(r_proj)
#
#     def RefreshBandSelection(self):
#         qTable = self.stats_table
#         selectedRas = self.parent.comboBox_raster.currentLayer()
#         bandcount = gdal.Open(selectedRas.source()).RasterCount
#         bdescs = rasterBandDescAslist(selectedRas.source())
#         nb_row = bandcount
#         qTable.setRowCount(nb_row)
#         nb_col = 5
#         qTable.setColumnCount(nb_col)
#         qTable.setColumnWidth(0, 80)
#         qTable.setColumnWidth(1, 50)
#         qTable.setColumnWidth(2, 80)
#         qTable.setColumnWidth(3, 50)
#         qTable.setColumnWidth(4, 50)
#         qTable.setHorizontalHeaderLabels([u'Band Name', u'Select', u'Mean', u'SD', u'Factor'])
#         for row, desc in zip(range(nb_row), bdescs):
#             qTable.setItem(row, 0, QTableWidgetItem(desc))
#             qTable.setItem(row, 1, QTableWidgetItem('1'))
#
#     def RefreshTable(self):
#         qTable = self.stats_table
#         selectedRas = self.parent.comboBox_raster.currentLayer()
#         bandcount = gdal.Open(selectedRas.source()).RasterCount
#         bdescs = rasterBandDescAslist(selectedRas.source())
#         nb_row = bandcount
#         qTable.setRowCount(nb_row)
#         nb_col = 5
#         qTable.setColumnCount(nb_col)
#         qTable.setColumnWidth(0, 80)
#         qTable.setColumnWidth(1, 50)
#         qTable.setColumnWidth(2, 80)
#         qTable.setColumnWidth(3, 50)
#         qTable.setColumnWidth(4, 50)
#         qTable.setHorizontalHeaderLabels([u'Band Name', u'Select', u'Mean', u'SD', u'Factor'])
#         for row, desc in zip(range(nb_row), bdescs):
#             qTable.setItem(row, 0, QTableWidgetItem(desc))
#             qTable.setItem(row, 1, QTableWidgetItem('1'))
#             qTable.setItem(row, 2, QTableWidgetItem(''))
#             qTable.setItem(row, 3, QTableWidgetItem(''))
#             qTable.setItem(row, 4, QTableWidgetItem(''))
#
#     def makeSpectralPlot(self):
#         selectedLayer = self.parent.comboBox_vector.currentLayer()
#         selectedRas = self.parent.comboBox_raster.currentLayer()
#
#         trainingList = []
#         sel = selectedLayer.selectedFeatures()
#         for feat in sel:
#             classLabel = feat['type_id']
#             fid = feat['fid']
#             plydat = ExtractRasterValuesFromSelectedFeature(selectedRas, selectedLayer, feat)
#             plydatT = plydat.T
#             cv = np.full((plydatT.shape[0], 1), classLabel)
#             fv = np.full((plydatT.shape[0], 1), fid)
#             ds = np.hstack([cv, fv, plydatT])
#             trainingList.append(ds)
#
#         cds = np.vstack(trainingList)
#         # Might need to add in a clause to use default names if this doesn't work
#         col_names = rasterBandDescAslist(selectedRas.source())
#         col_names.insert(0, 'type_id')
#         col_names.insert(1, 'fid')
#
#         df = pd.DataFrame(data=cds, columns=col_names)
#         df['type_id'] = df['type_id'].astype(int)
#         df['fid'] = df['fid'].astype(int)
#
#         # The balanced samples can be an option at some point
#         # Need to make a checkbox
#         # trimmed_df = balancedSamples(df, 'type_id', False, 1500)
#
#         inputbands = self.PrintBox.text()
#         try:
#             plot_cols = [(int(x) + 1) for x in inputbands.split(',')]  # +1 since fid is added in
#         except ValueError:
#             plot_cols = [2,3,4]
#         print(plot_cols)
#         plot_cols.insert(0, 0)
#         plot_cols.insert(1, 1)
#
#         # plot_df = trimmed_df.iloc[:, plot_cols]  # If trimmed
#         plot_df = df.iloc[:, plot_cols]
#
#         # print("Plot_DF =\n", plot_df.head())
#
#         ## Example in case want to do a class selection as well
#         # plot_classes = [2, 4, 5, 9]
#         # plot_df = df_colsub.loc[df_colsub.type_id.isin(plot_classes)]
#
#         tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
#         plotfile = Path(tempfile.mkstemp(dir=tfol, suffix='.png', prefix='specPlot_')[1])
#         # multispec_scatter_original(plot_df, plotfile)
#         multispec_scatter(plot_df, plotfile)
#
#     def summarize_training(self):
#         selectedLayer = self.parent.comboBox_vector.currentLayer()
#         selectedRas = self.parent.comboBox_raster.currentLayer()
#         samplingRate = self.parent.supervised_tab.samplingRatespinBox.value()   # TODO: not this
#         maxPixPoly = self.parent.supervised_tab.max_pix_poly_spinBox.value()    # TODO: not this
#         print("TRAINING SUMMARY")
#
#         train_dat = getTrainingDataFromFeatures(selectedRas, selectedLayer, withSelected=False, samplingRate=samplingRate, maxPerPoly=maxPixPoly)
#         labels = train_dat[:, 0]
#         summary = label_count(labels)
#         print(summary)
#
#     def saveTrainingDataOut(self):
#         filename = QFileDialog.getSaveFileName(self, "Select output file", "", '*.csv')[0] + '.csv'
#         self.iface.messageBar().pushMessage('Writing File')
#
#         selectedLayer = self.parent.comboBox_vector.currentLayer()
#         selectedRas = self.parent.comboBox_raster.currentLayer()
#
#         trainingList = []
#         if self.parent.withSelectedcheckBox.isChecked():
#             sel = selectedLayer.selectedFeatures()
#             for feat in sel:
#                 classLabel = feat['type_id']
#                 fid = feat['fid']
#                 plydat = ExtractRasterValuesFromSelectedFeature(selectedRas, selectedLayer, feat)
#                 plydatT = plydat.T
#                 cv = np.full((plydatT.shape[0], 1), classLabel)
#                 fv = np.full((plydatT.shape[0], 1), fid)
#                 ds = np.hstack([cv, fv, plydatT])
#                 trainingList.append(ds)
#         else:
#             features = selectedLayer.getFeatures()
#             for feat in features:
#                 classLabel = feat['type_id']
#                 fid = feat['fid']
#                 plydat = ExtractRasterValuesFromSelectedFeature(selectedRas, selectedLayer, feat)
#                 plydatT = plydat.T
#                 cv = np.full((plydatT.shape[0], 1), classLabel)
#                 fv = np.full((plydatT.shape[0], 1), fid)
#                 ds = np.hstack([cv, fv, plydatT])
#                 trainingList.append(ds)
#
#         cds = np.vstack(trainingList)
#         # np.savetxt(filename, cds, delimiter=",")
#         col_names = rasterBandDescAslist(selectedRas.source())
#         col_names.insert(0, 'type_id')
#         col_names.insert(1, 'fid')
#
#         df = pd.DataFrame(data=cds, columns=col_names)
#         df['type_id'] = df['type_id'].astype(int)
#         df['fid'] = df['fid'].astype(int)
#         df.to_csv(filename, index=False)
#
#         self.iface.messageBar().pushMessage(f'File Saved to {filename}')
#
#     def constantSTdevMatch(self):
#         selectedLayer = self.parent.comboBox_vector.currentLayer()
#         selectedRas = self.parent.comboBox_raster.currentLayer()
#         r_ds = gdal.Open(selectedRas.source())
#         geot = r_ds.GetGeoTransform()
#         r_proj = r_ds.GetProjection()
#         cellres = geot[1]
#
#         doClassIDfield(selectedLayer)
#         sel = selectedLayer.selectedFeatures()
#         # Maybe here is where can do multiple selection if len(sel >1 ...
#         feat = sel[0]  # Returns a QgsFeature
#         # For naming the layer in the contents
#         fid = feat['Class_ID']
#         classid = feat['type_id']
#
#         plydat = ExtractRasterValuesFromSelectedFeature(selectedRas, selectedLayer, feat)
#         means = plydat.mean(axis=1)
#         stds = plydat.std(axis=1)
#         meanSTDlist = [[x, y] for x, y in zip(means, stds)]
#         sdval = self.StdevInputBox1.value()
#         numberBands2match = self.MinBandMatch.value()
#
#         if self.parent.ClusterWholeExtentBox.isChecked():
#             layerName = 'Class_' + str(classid) + '_CID_' + str(fid) + '_' + str(sdval) + 'sdevs_Matches'
#
#             if self.parent.UseBandSelectionBox.isChecked():
#                 bandList = bandSelToList(self.dockwidget.stats_table)
#                 idxs2keep = bands2indices(bandList)
#                 newmeans = np.array(meanSTDlist)[idxs2keep]
#                 dat = extractBands(bandList, r_ds)   # This is the dataset of which to find matches from
#                 matches = sdMatchSomeInStack(dat, newmeans, sdval, numberBands2match)
#
#             else:
#                 dat = r_ds.ReadAsArray()
#                 matches = sdMatchSomeInStack(dat, meanSTDlist, sdval, numberBands2match)
#
#         else:
#             layerName = 'InWindow_Class_' + str(classid) + '_CID_' + str(fid) + '_' + str(sdval) + '_sdevs_Matches'
#
#             bb = self.canvas.extent()
#             bb.asWktCoordinates()
#             bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
#             offsets = boundingBoxToOffsets(bbc, geot)
#             new_geot = geotFromOffsets(offsets[0], offsets[2], geot)
#             geot = new_geot
#
#             sizeX = int(((bbc[2] - bbc[0]) / cellres) + 1)
#             sizeY = int(((bbc[3] - bbc[1]) / cellres) + 1)
#
#             if self.parent.UseBandSelectionBox.isChecked():
#                 bandList = bandSelToList(self.stats_table)
#                 dat = extractBandsInBounds(bandList, r_ds, offsets[2], offsets[0], sizeX, sizeY)
#                 idxs2keep = bands2indices(bandList)
#                 newmeans = np.array(meanSTDlist)[idxs2keep]
#                 matches = sdMatchSomeInStack(dat, newmeans, sdval, numberBands2match)
#             else:
#                 dat = r_ds.ReadAsArray(offsets[2], offsets[0], sizeX, sizeY)
#                 matches = sdMatchSomeInStack(dat, meanSTDlist, sdval, numberBands2match)
#
#         valued_to_typeVal = np.where(matches == 1, int(classid), 0)
#
#         value = np.count_nonzero(valued_to_typeVal == int(classid))
#         statement = f'Found {value} matches in Raster'
#         if value > 1:
#             self.iface.messageBar().pushMessage(statement)
#             savedLayer = gdalSave('stdevMatch_', valued_to_typeVal, gdal.GDT_Byte, geot, r_proj, 0)
#             addLayerSymbol(savedLayer, layerName, classid, "Classes")
#
#     def evaluteTrainingPolygons(self):
#         '''
#         Going to design this one to only work across the whole raster. This will be a slower more robust mat
#         :return:
#         '''
#         selectedLayer = self.parent.comboBox_vector.currentLayer()
#         selectedRas = self.parent.comboBox_raster.currentLayer()
#         r_ds = gdal.Open(selectedRas.source())
#         geot = r_ds.GetGeoTransform()
#         r_proj = r_ds.GetProjection()
#         sdval = self.StdevInputBox1.value()
#
#         evalstatement = 'Finding Matches for Polygons'
#         print(evalstatement)
#         self.iface.messageBar().pushMessage(evalstatement)
#
#         # Add and populate the classID column
#         doClassIDfield(selectedLayer)
#
#         sel = selectedLayer.selectedFeatures()
#         if len(sel) > 1:
#             vals = list(set([x['type_id'] for x in sel]))
#             groupNames = ['Class_' + str(v) for v in vals]
#             root = QgsProject.instance().layerTreeRoot()
#             # Add the groups to the ToC
#             for idx, group in enumerate(groupNames, 0):
#                 root.insertGroup(idx, group)
#             lols = [[] for x in vals]  # to hold all the finds
#
#             for feat in sel:
#                 # For naming the layer in the contents
#                 classID = feat['Class_ID']
#                 classLabel = feat['type_id']
#
#                 plydat = ExtractRasterValuesFromSelectedFeature(selectedRas, selectedLayer, feat)
#                 means = plydat.mean(axis=1)
#                 stds = plydat.std(axis=1)
#                 meanSTDlist = [[x, y] for x, y in zip(means, stds)]
#
#                 numberBands2match = self.MinBandMatch.value()
#
#                 layerName = 'Class_' + str(classLabel) + '_poly_' + str(classID) + '_sd_' + str(sdval) + '_Matches'
#
#                 if self.parent.UseBandSelectionBox.isChecked():
#                     bandList = bandSelToList(self.stats_table)
#                     idxs2keep = bands2indices(bandList)
#                     newmeans = np.array(meanSTDlist)[idxs2keep]
#                     dat = extractBands(bandList, r_ds)  # This is the dataset of which to find matches from
#                     matches = sdMatchSomeInStack(dat, newmeans, sdval, numberBands2match)
#
#                 else:
#                     dat = r_ds.ReadAsArray()
#                     matches = sdMatchSomeInStack(dat, meanSTDlist, sdval, numberBands2match)
#
#                 valued_to_typeVal = np.where(matches == 1, int(classLabel), 0)
#
#                 value = np.count_nonzero(valued_to_typeVal == int(classLabel))
#                 statement = f'Found {value} matches in Raster with Class {classLabel} and ID {classID}'
#                 if value > 1:
#                     # Update this statement to include which polygon it is
#                     self.iface.messageBar().pushMessage(statement)
#                     listIndex = vals.index(classLabel)
#                     lols[listIndex].append(valued_to_typeVal)
#                     savedLayer = gdalSave('stdevMatch_', valued_to_typeVal, gdal.GDT_Byte, geot, r_proj, 0)
#                     group = root.findGroup('Class_' + str(classLabel))
#                     addLayerSymbolGroup(savedLayer, layerName, classLabel, group, "Classes")
#         else:
#             vals = list(selectedLayer.uniqueValues(selectedLayer.fields().indexOf('type_id')))
#             groupNames = ['Class_' + str(v) for v in vals]
#             root = QgsProject.instance().layerTreeRoot()
#             # Add the groups to the ToC
#             for idx, group in enumerate(groupNames, 0):
#                 root.insertGroup(idx, group)
#             # Consider this part only for doing all
#
#             lols = [[] for x in vals]  # to hold all the finds
#
#             features = selectedLayer.getFeatures()
#             for feat in features:
#                 # For naming the layer in the contents
#                 classID = feat['Class_ID']
#                 classLabel = feat['type_id']
#
#                 plydat = ExtractRasterValuesFromSelectedFeature(selectedRas, selectedLayer, feat)
#                 means = plydat.mean(axis=1)
#                 stds = plydat.std(axis=1)
#                 meanSTDlist = [[x, y] for x, y in zip(means, stds)]
#
#                 numberBands2match = self.MinBandMatch.value()
#
#
#                 layerName = 'Class_' + str(classLabel) + '_poly_' + str(classID) + '_sd_' + str(sdval) + '_Matches'
#
#                 if self.parent.UseBandSelectionBox.isChecked():
#                     bandList = bandSelToList(self.stats_table)
#                     idxs2keep = bands2indices(bandList)
#                     newmeans = np.array(meanSTDlist)[idxs2keep]
#                     dat = extractBands(bandList, r_ds)   # This is the dataset of which to find matches from
#                     matches = sdMatchSomeInStack(dat, newmeans, sdval, numberBands2match)
#
#                 else:
#                     dat = r_ds.ReadAsArray()
#                     matches = sdMatchSomeInStack(dat, meanSTDlist, sdval, numberBands2match)
#
#                 valued_to_typeVal = np.where(matches == 1, int(classLabel), 0)
#
#                 value = np.count_nonzero(valued_to_typeVal == int(classLabel))
#                 statement = f'Found {value} matches in Raster with Class {classLabel} and ID {classID}'
#                 if value > 1:
#                     # Update this statement to include which polygon it is
#                     self.iface.messageBar().pushMessage(statement)
#                     listIndex = vals.index(classLabel)
#                     lols[listIndex].append(valued_to_typeVal)
#                     savedLayer = gdalSave('stdevMatch_', valued_to_typeVal, gdal.GDT_Byte, geot, r_proj, 0)
#                     group = root.findGroup('Class_' + str(classLabel))
#                     addLayerSymbolGroup(savedLayer, layerName, classLabel, group, "Classes")
#
#         evalstatement1 = 'Looking at class overlaps'
#         print(evalstatement1)
#         self.iface.messageBar().pushMessage(evalstatement1)
#
#         # In this part do the within and cross class matching
#         toCompareList, singClassList = createClassCoverageList(vals, lols)
#         crossList = createCrossClassList(toCompareList)
#         # crossList and singClassList have structure of: list of [the array, string of layerName, the Unique Value]
#         # Make a group for SingClassList
#         classCoverGroup = root.insertGroup(0, 'ClassCovers')
#         for layer in singClassList:
#             layerOut = gdalSave('InClassMatch', layer[0], gdal.GDT_UInt16, geot, r_proj, 0)
#             addLayerSymbolMutliClassGroup(layerOut, layer[1], classCoverGroup, np.unique(layer[0]).tolist(), "Coverage")
#
#         classIntersectGroup = root.insertGroup(0, 'ClassIntersections')
#         for layer in crossList:
#             layerOut = gdalSave('BetweenClass', layer[0], gdal.GDT_UInt16, geot, r_proj, 0)
#             addLayerSymbolMutliClassGroup(layerOut, layer[1], classIntersectGroup,  np.unique(layer[0]).tolist(), "Intersection")
#
#         evalstatement2 = 'Finished'
#         print(evalstatement2)
#         self.iface.messageBar().pushMessage(evalstatement2)
#
#     def returnBoreMatch(self):
#         selectedLayer = self.parent.comboBox_vector.currentLayer()
#         doClassIDfield(selectedLayer)
#         selectedRas = self.parent.comboBox_raster.currentLayer()
#         r_ds = gdal.Open(selectedRas.source())
#         geot = r_ds.GetGeoTransform()
#         r_proj = r_ds.GetProjection()
#
#         doingmatching = 'Finding Matches'
#         print(doingmatching)
#         self.iface.messageBar().pushMessage(doingmatching)
#
#         sel = selectedLayer.selectedFeatures()  # returns a list of selected features
#         feat = sel[0]  # Returns a QgsFeature
#         # For naming the layer in the contents
#         fid = feat['Class_ID']
#         classid = feat['type_id']
#         layerName = 'Class_' + str(classid) + '_CID_' + str(fid) + '_Matches'
#
#         dat = ExtractRasterValuesFromSelectedFeature(selectedRas, selectedLayer, feat)
#
#         # Go through each band and get the min and max after removing min and max
#         vallist = []
#         for b, d in enumerate(dat, 1):
#             band = b
#             # narr = MinMaxPop(d)
#             # olymax = np.max(narr)
#             # olymin = np.min(narr)
#             olymax = np.max(d)
#             olymin = np.min(d)
#
#             l = [band, olymin, olymax]
#             vallist.append(l)
#
#         ms = [RasBoreMatch(j, r_ds) for j in vallist]
#         boolstack = np.vstack([ms])
#         allmatch = np.all(boolstack, axis=0).astype(np.uint8)
#         valued_to_typeVal = np.where(allmatch == 1, int(classid), 0)
#
#
#         value = np.count_nonzero(valued_to_typeVal == int(classid))
#         statement = f'Found {value} matches in Raster'
#         self.iface.messageBar().pushMessage(statement)
#         savedLayer = gdalSave('rasbore_', valued_to_typeVal, gdal.GDT_Byte, geot, r_proj, 0)
#         addLayerSymbol(savedLayer, layerName, classid, "Classes")
#
