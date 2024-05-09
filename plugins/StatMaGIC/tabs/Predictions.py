import tempfile

from osgeo import gdal

from PyQt5 import QtWidgets
from qgis.core import QgsProject, QgsRasterLayer
from PyQt5.QtWidgets import QFileDialog, QPushButton, QFormLayout, QLabel, QVBoxLayout, QGridLayout, QHBoxLayout
from statmagic_backend.dev.threshold_inference import threshold_inference
from statmagic_backend.dev.restack_feature_attribution_layers import restack_matched_layers

from .TabBase import TabBase
from ..fileops import gdalSave1
from ..gui_helpers import *
from ..widgets.collapsible_box import CollapsibleBox
from ..layerops import addGreyScaleLayer, addVectorLayer
from ..popups.plotting.feature_attribution_point_plot import featAttPlot


import logging
logger = logging.getLogger("statmagic_gui")


class PredictionsTab(TabBase):
    def __init__(self, parent, tabWidget, isEnabled=True):
        super().__init__(parent, tabWidget, "Predictions", isEnabled)

        self.parent = parent

        # self.mainLayout = QVBoxLayout()

        # self.compile_layout = QHBoxLayout()
        # self.compile_box = CollapsibleBox("Compile Attribute Layers")
        # self.choose_files_button = QPushButton(self)
        # self.choose_files_button.setText('Compile Feature Attribution Layers')
        # self.choose_files_button.clicked.connect(self.choose_files)
        # self.choose_files_button.setToolTip('Opens dialog to choose layers to combine to facilitate plotting')
        #
        #
        # self.tabLayout.addWidget(self.compile_box)
        #

        topFrame, topLayout = addFrame(self, "HBox", "NoFrame", "Plain", 3)

        self.prob_layer_box = addQgsMapLayerComboBox(topFrame, "Probability Layer")
        self.uncert_layer_box = addQgsMapLayerComboBox(topFrame, "Uncertainty Layer")

        addToParentLayout(topFrame)

        formLayout = QtWidgets.QFormLayout()


        self.probability_thresh_box = addSpinBoxToForm(formLayout, "Probability Threshold",
                                                       dtype=float, value=0.5, max=1, step=0.05)
        self.uncert_thresh_box = addSpinBoxToForm(formLayout, "Uncertainty Threshold",
                                                  dtype=float, value=0.5, max=1, step=0.05)
        self.remove_hanging_check = addCheckboxToForm(formLayout, "Remove Hanging Pixels", isChecked=True)
        self.to_poly_check = addCheckboxToForm(formLayout, "Convert to Polygon Layer", isChecked=True)
        self.threshold_inference_button = addButtonToForm(formLayout, "Generate Filtered Layer", self.threshold_inference)


        self.choose_files_button = QPushButton(self)
        self.choose_files_button.setText('Compile Feature Attribution Layers')
        self.choose_files_button.clicked.connect(self.choose_files)
        self.choose_files_button.setToolTip('Opens dialog to choose layers to combine to facilitate plotting')

        self.inspect_attributions_button = QPushButton(self)
        self.inspect_attributions_button.setText('Inspect/Plot Feature Attribution Scores')
        self.inspect_attributions_button.clicked.connect(self.launch_attribution_plot)
        self.inspect_attributions_button.setToolTip('Opens Plotting GUI. Click on points to generate plot')


        alignLayoutAndAddToParent(formLayout, self, "Left")

        topLayout.addWidget(self.choose_files_button)

    def choose_files(self):
        rasterFilePaths, _ = QFileDialog.getOpenFileNames(self, "Select Raster Files", "", "GeoTIFFs (*.tif *.tiff)")
        output_path, _ = QFileDialog.getSaveFileName(self, "Select Output File", "", "GeoTIFFs (*.tif)")
        # Force the extension to be .tif
        if output_path[-4:] != '.tif':
            output_path += '.tif'

        self.stack_files(rasterFilePaths, output_path)

    def stack_files(self, file_list, output_path):
        restack_matched_layers(file_list, output_path)
        # Then add output_path to the project
        message = f"File saved to: {output_path}"
        qgs_data_raster = QgsRasterLayer(output_path, 'Feature Attributions')
        QgsProject.instance().addMapLayer(qgs_data_raster)
        self.iface.messageBar().pushMessage(message)

    def launch_attribution_plot(self):
        popup = featAttPlot(self.parent)
        self.featAttplot = popup.show()


    def threshold_inference(self):
        # Get inputs from GUI
        prob_path = self.prob_layer_box.currentLayer().source()
        uncert_path = self.uncert_layer_box.currentLayer().source()
        prob_cut = self.probability_thresh_box.value()
        cert_cut = self.uncert_thresh_box.value()
        remove_hanging = self.remove_hanging_check.isChecked()
        to_polys = self.to_poly_check.isChecked()

        # run function
        output = threshold_inference(prob_path, uncert_path, prob_cut, cert_cut, remove_hanging, to_polys)

        # Set up for saving and adding to TOC
        root = QgsProject.instance().layerTreeRoot()
        if root.findGroup('Inference') is None:
            inference_group = root.insertGroup(0, 'Inference')
        else:
            inference_group = root.findGroup('Inference')
        r_ds = gdal.Open(prob_path)
        geot = r_ds.GetGeoTransform()
        r_proj = r_ds.GetProjection()
        savedLayer = gdalSave1('Threshold', output[0], gdal.GDT_Byte, geot, r_proj, 0)
        addGreyScaleLayer(savedLayer,
                          f"Inference_Cutoff_prob_{format(prob_cut, '.2f')}_uncert_{format(cert_cut, '.2f')}",
                          inference_group)

        if to_polys:
            logger.debug('raster and vector')
            tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
            outpath = tfol + '/Threshold_Inference.shp'
            output[1].to_file(outpath)
            addVectorLayer(outpath, f"Inference Polys_prob_{format(prob_cut, '.2f')}_uncert_{format(cert_cut, '.2f')}", inference_group)

        self.iface.messageBar().pushMessage('Files Added')

