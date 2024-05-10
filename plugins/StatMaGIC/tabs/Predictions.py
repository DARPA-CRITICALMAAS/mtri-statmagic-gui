import tempfile

from osgeo import gdal

from qgis.core import QgsProject, QgsRasterLayer, QgsMapLayerProxyModel
from PyQt5.QtWidgets import QFileDialog, QPushButton, QFormLayout, QLabel, QVBoxLayout, QGridLayout, QHBoxLayout,  QDoubleSpinBox, QCheckBox
from qgis.gui import QgsFieldComboBox, QgsMapLayerComboBox, QgsFileWidget


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

        self.compile_box = CollapsibleBox("Compile Output Layers")
        self.compile_layout = QHBoxLayout()

        self.choose_attr_files = QPushButton()
        self.choose_attr_files.setText('Compile Feature Attribution Layers')
        self.choose_attr_files.clicked.connect(self.choose_files)
        self.choose_attr_files.setToolTip('Opens dialog to choose layers to combine to facilitate plotting')

        self.choose_pred_unc_files = QPushButton()
        self.choose_pred_unc_files.setText('Compile Feature Attribution Layers')
        self.choose_pred_unc_files.clicked.connect(self.choose_files)
        self.choose_pred_unc_files.setToolTip('Opens dialog to choose layers to combine to facilitate plotting')
        self.choose_pred_unc_files.setEnabled(False)

        self.compile_layout.addWidget(self.choose_attr_files)
        self.compile_layout.addWidget(self.choose_pred_unc_files)

        self.compile_box.setContentLayout(self.compile_layout)
        self.tabLayout.addWidget(self.compile_box)


        self.threshold_outputs_box = CollapsibleBox("Threshold Outputs")
        self.threshold_grouping_layout = QVBoxLayout()

        self.layer_selection_layout = QGridLayout()

        prob_layer_label = QLabel('Prediction Likelihood Layer')
        self.prob_layer_select = QgsMapLayerComboBox()
        self.prob_layer_select.setFilters(QgsMapLayerProxyModel.RasterLayer)

        uncert_layer_label = QLabel('Prediction Uncertainty Layer')
        self.uncert_layer_select = QgsMapLayerComboBox()
        self.uncert_layer_select.setFilters(QgsMapLayerProxyModel.RasterLayer)

        self.probability_thresh_box = QDoubleSpinBox()
        self.probability_thresh_box.setValue(0.50)
        self.probability_thresh_box.setRange(0.00, 1.00)
        self.probability_thresh_box.setSingleStep(0.05)

        self.uncert_thresh_box = QDoubleSpinBox
        self.uncert_thresh_box = QDoubleSpinBox()
        self.uncert_thresh_box.setValue(0.50)
        self.uncert_thresh_box.setRange(0.00, 1.00)
        self.uncert_thresh_box.setSingleStep(0.05)

        self.layer_selection_layout.addWidget(prob_layer_label, 0, 0)
        self.layer_selection_layout.addWidget(uncert_layer_label, 0, 1)
        self.layer_selection_layout.addWidget(self.prob_layer_select, 1, 0)
        self.layer_selection_layout.addWidget(self.uncert_layer_select, 1, 1)
        self.layer_selection_layout.addWidget(self.probability_thresh_box, 2, 0)
        self.layer_selection_layout.addWidget(self.uncert_thresh_box, 2, 1)

        self.threshold_grouping_layout.addLayout(self.layer_selection_layout)

        self.remove_hanging_check = QCheckBox()
        self.remove_hanging_check.setText('Remove Hanging Pixels')
        self.remove_hanging_check.setChecked(True)

        self.to_poly_check = QCheckBox()
        self.to_poly_check.setText('Convert to Polygon Layer')
        self.to_poly_check.setChecked(True)

        self.threshold_inference_button = QPushButton()
        self.threshold_inference_button.setText('Generate Thresholded Layer')
        self.threshold_inference_button.clicked.connect(self.threshold_inference)

        self.threshold_grouping_layout.addWidget(self.remove_hanging_check)
        self.threshold_grouping_layout.addWidget(self.to_poly_check)
        self.threshold_grouping_layout.addWidget(self.threshold_inference_button)

        self.threshold_outputs_box.setContentLayout(self.threshold_grouping_layout)
        self.tabLayout.addWidget(self.threshold_outputs_box)

        self.plotting_box = CollapsibleBox('Plotting Tools')
        self.plotting_layout = QVBoxLayout()

        self.inspect_attributions_button = QPushButton()
        self.inspect_attributions_button.setText('Inspect/Plot Feature Attribution Scores')
        self.inspect_attributions_button.clicked.connect(self.launch_attribution_plot)
        self.inspect_attributions_button.setToolTip('Opens Plotting GUI. Click on points to generate plot')

        self.plotting_layout.addWidget(self.inspect_attributions_button)
        self.plotting_box.setContentLayout(self.plotting_layout)
        self.tabLayout.addWidget(self.plotting_box)

    def choose_files(self):
        rasterFilePaths, _ = QFileDialog.getOpenFileNames(self, "Select Raster Files", "", "GeoTIFFs (*.tif *.tiff)")
        if len(rasterFilePaths) == 0:
            return
        output_path, _ = QFileDialog.getSaveFileName(self, "Select Output File", "", "GeoTIFFs (*.tif)")
        if len(output_path) == 0:
            return

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
        prob_path = self.prob_layer_select.currentLayer().source()
        uncert_path = self.uncert_layer_select.currentLayer().source()
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

