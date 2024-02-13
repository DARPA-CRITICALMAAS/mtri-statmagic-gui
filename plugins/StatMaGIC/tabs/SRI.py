import traceback

import torch
from torchinfo import summary

try:
    from sri_maper.src.models.cma_module import CMALitModule
    PYTORCH_FAILED = False
except ValueError:
    PYTORCH_FAILED = True
    error = traceback.format_exc()
    # split stack trace into a list and slice it
    stack_trace = error.split('\n')

import sys
if sys.version_info < (3, 9):
    from importlib_resources import files
else:
    from importlib.resources import files

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QPushButton, QLabel, QMessageBox, QSizePolicy
from qgis.core import QgsVectorLayer, QgsProject, QgsRasterLayer, QgsMapLayerProxyModel, QgsPoint, QgsCoordinateTransform


from .TabBase import TabBase
from ..gui_helpers import *
import rasterio as rio
from rasterio.windows import Window


class SRITab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "SRI")

        self.parent = parent
        self.iface = self.parent.iface

        print("Creating sri tab")
        ## Top Frame - Select data source and AOI to
        topFrame, topLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        topFrameLabel = addLabel(topLayout, "SRI Classifier Inputs")
        makeLabelBig(topFrameLabel)
        topFormLayout = QtWidgets.QFormLayout()

        print("Create input raster combobox")
        raster_label = QLabel('Input Datacube')
        self.raster_selection_box = QgsMapLayerComboBox(self)
        self.raster_selection_box.setShowCrs(True)
        self.raster_selection_box.setFilters(QgsMapLayerProxyModel.RasterLayer)

        print("Create target raster combobox")
        target_raster_label = QLabel('Target Layer')
        self.target_raster_selection_box = QgsMapLayerComboBox(self)
        self.target_raster_selection_box.setShowCrs(True)
        self.target_raster_selection_box.setFilters(QgsMapLayerProxyModel.RasterLayer)

        print("Create AOI box")
        aoi_label = QLabel('AOI')
        self.aoi_selection_box = QgsMapLayerComboBox()
        self.aoi_selection_box.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.aoi_selection_box.setAllowEmptyLayer(True)
        self.aoi_selection_box.setCurrentIndex(0)

        print("Create button")
        self.run_sri_classifier_btn = QPushButton()
        self.run_sri_classifier_btn.setText('Run SRI Classifier')
        self.run_sri_classifier_btn.clicked.connect(self.run_sri_classifier)

        print("Create layout")
        topFormLayout.addRow(raster_label, self.raster_selection_box)
        topFormLayout.addRow(target_raster_label, self.target_raster_selection_box)
        topFormLayout.addRow(aoi_label, self.aoi_selection_box)
        topFormLayout.addWidget(self.run_sri_classifier_btn)
        addWidgetFromLayoutAndAddToParent(topFormLayout, topFrame)
        addToParentLayout(topFrame)

    def run_sri_classifier(self):
        if PYTORCH_FAILED:
            msgBox = QMessageBox()
            # msgBox.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
            msgBox.setText(f"The package <pre>pytorch</pre> threw the following error:\n"
                           f"<code>{stack_trace[-2]}</code>\n"
                           f"Please install it before running the SRI tab.")
            msgBox.exec()
            return
        # loads the pretrained checkpoint
        ckpt_path = str(files("sri_maper.ckpts") / "epoch_007.ckpt")
        model = CMALitModule.load_from_checkpoint(ckpt_path)
        # device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        device = torch.device("cpu")
        raster_layer: QgsRasterLayer = self.raster_selection_box.currentLayer()
        target_raster_layer: QgsRasterLayer = self.target_raster_selection_box.currentLayer()
        aoi_layer: QgsVectorLayer = self.aoi_selection_box.currentLayer()
        # print(raster_layer.name(), aoi_layer.name())

        # Check that the user has selected valid inputs
        if raster_layer is None:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid raster layer for the histogram")
            msgBox.exec()
            return
        # Todo: pull bounds from canvas if not set
        if aoi_layer is None:
            msgBox = QMessageBox()
            msgBox.setText("You must select a valid vector / polygon layer to provide an AOI for the histogram")
            msgBox.exec()
            return
        if not raster_layer.name() == "north-america-alldata-inputs":
            msgBox = QMessageBox()
            msgBox.setText("The input raster layer must be the `north-america-alldata-inputs` datacube created by SRI")
            msgBox.exec()
            return
        if not target_raster_layer.name() == "north-america-alldata-target":
            msgBox = QMessageBox()
            msgBox.setText("The target raster layer must be the `north-america-alldata-target` layer created by SRI")
            msgBox.exec()
            return

        # Assume the bounding box of the first feature of the AOI layer is the AOI
        # I had to change this from 0 to 1. Using gpkg as input seems to always have 0 return null geometry
        extents_feature = aoi_layer.getFeature(1)
        extents_rect = extents_feature.geometry().boundingBox()

        print("Constructing coordinate transform")
        min_corner = QgsPoint(extents_rect.xMinimum(), extents_rect.yMinimum())
        max_corner = QgsPoint(extents_rect.xMaximum(), extents_rect.yMaximum())
        raster_crs = raster_layer.crs()
        aoi_crs = aoi_layer.crs()
        tr = QgsCoordinateTransform(aoi_crs, raster_crs, QgsProject.instance())

        # Open the input datacube for window reads
        sri_input_tif = rio.open(raster_layer.source())

        print("Applying transform")
        min_corner.transform(tr)
        max_corner.transform(tr)
        min_row, min_col = sri_input_tif.index(min_corner.x(), min_corner.y())
        max_row, max_col = sri_input_tif.index(max_corner.x(), max_corner.y())
        print(min_row, min_col, max_row, max_col, max_col - min_col, max_row - min_row)

        # Figure out the AOI in pixel coordinates
        aoi_min_row = min(min_row, max_row)
        aoi_max_row = max(min_row, max_row)
        aoi_min_col = min(min_col, max_col)
        aoi_max_col = max(min_col, max_col)
        aoi_num_pixels_in_row = aoi_max_col - aoi_min_col
        aoi_num_pixels_in_col = aoi_max_row-aoi_min_row
        aoi_win = Window(aoi_min_col, aoi_min_row, aoi_num_pixels_in_col, aoi_num_pixels_in_row)

        # Get the target layer within the AOI
        sri_target_tif = rio.open(target_raster_layer.source())
        target_data = sri_target_tif.read(window=aoi_win)

        # Construct the batches required to classify each pixel within the AOI
        num_pixels = aoi_num_pixels_in_row * aoi_num_pixels_in_col
        print(f'num pixels row {aoi_num_pixels_in_row}')
        print(f'num pixels col {aoi_num_pixels_in_col}')
        input_data_cpu = np.zeros(shape=(num_pixels, 73, 33, 33), dtype=float)
        labels_cpu = np.zeros(shape=(num_pixels,), dtype=float)
        locs_cpu = np.zeros(shape=(2, num_pixels), dtype=float)
        for i, row in enumerate(range(aoi_min_row, aoi_max_row)):
            for j, col in enumerate(range(aoi_min_col, aoi_max_col)):
                input_data_cpu[i * aoi_num_pixels_in_row + j, :, :, :] = sri_input_tif.read(window=Window(col - 16, row - 16, 33, 33))
                labels_cpu[i * aoi_num_pixels_in_row + j] = target_data[0, i, j]
                pos = sri_input_tif.xy(row, col)
                if i == 0 and j == 0:
                    print(pos)
                locs_cpu[0, i * aoi_num_pixels_in_row + j] = pos[0]
                locs_cpu[1, i * aoi_num_pixels_in_row + j] = pos[1]

        # Copy data to device
        input_patch = torch.from_numpy(input_data_cpu).float().to(device)
        labels_patch = torch.from_numpy(labels_cpu).float().to(device)
        locs = torch.from_numpy(locs_cpu).float().to(device)

        # Predict step
        print(device)
        batch_idx = 0
        output_p = model.predict_step((input_patch, labels_patch, locs[0], locs[1]), batch_idx)
        print(f"Long, Lat: {output_p[0, :2]}")
        print(f"Likelihood, Uncertainty: {output_p[0, 2:4]}")
        print(f"Feature attributions: {output_p[0, 4:]}")

        # Transfer over to CPU
        output_p_cpu = output_p.cpu()

        # Transfer data into 2d array for plotting
        pred_p_data = np.zeros_like(target_data)
        for i in range(0, aoi_num_pixels_in_col):
            for j in range(0, aoi_num_pixels_in_row):
                pred_p_data[0, i, j] = output_p_cpu[i * aoi_num_pixels_in_row + j, 2]

        print(pred_p_data.shape)
        print(pred_p_data.dtype)
