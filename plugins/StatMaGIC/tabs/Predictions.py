import tempfile

from osgeo import gdal

from PyQt5 import QtWidgets
from qgis.core import QgsProject

from statmagic_backend.dev.threshold_inference import threshold_inference

from .TabBase import TabBase
from ..fileops import gdalSave1
from ..gui_helpers import *
from ..layerops import addGreyScaleLayer, addVectorLayer


class PredictionsTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Predictions")

        self.parent = parent

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

        alignLayoutAndAddToParent(formLayout, self, "Left")

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
            print('raster and vector')
            tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
            outpath = tfol + '/Threshold_Inference.shp'
            output[1].to_file(outpath)
            addVectorLayer(outpath, f"Inference Polys_prob_{format(prob_cut, '.2f')}_uncert_{format(cert_cut, '.2f')}", inference_group)

        self.iface.messageBar().pushMessage('Files Added')

