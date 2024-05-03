import traceback

# try:
#     from sri_maper.src.models.cma_module import CMALitModule
#     PYTORCH_FAILED = False
# except (ValueError, AttributeError):
#     PYTORCH_FAILED = True
#     error = traceback.format_exc()
#     # split stack trace into a list and slice it
#     stack_trace = error.split('\n')

import sys
if sys.version_info < (3, 9):
    from importlib_resources import files
else:
    from importlib.resources import files

from qgis.PyQt.QtWidgets import QDialog
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QPushButton, QLabel, QMessageBox, QSizePolicy
from qgis.core import QgsVectorLayer, QgsProject, QgsRasterLayer, QgsMapLayerProxyModel, QgsPoint, QgsCoordinateTransform

from statmagic_backend.dev.sri_workflow import *
from ..gui_helpers import *

import logging
logger = logging.getLogger("statmagic_gui")

class SRI_PopUp_Menu(QDialog):

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        super(SRI_PopUp_Menu, self).__init__(parent)
        QDialog.setWindowTitle(self, "SRI Modelling Menu")
        self.setLayout(QtWidgets.QVBoxLayout())

        ## Top Frame - Select data source and AOI to
        topFrame, topLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        topFrameLabel = addLabel(topLayout, "SRI Classifier Inputs")
        makeLabelBig(topFrameLabel)
        topFormLayout = QtWidgets.QFormLayout()

        experiments = get_experiment_list()
        preprocess = get_preprocess_list()
        trainers = get_trainer_list()

        self.experiment_comboBox = addComboBoxToForm(topFormLayout, "experiment", experiments)
        self.preprocess_comboBox = addComboBoxToForm(topFormLayout, "preprocess", preprocess)
        self.trainer_comboBox = addComboBoxToForm(topFormLayout, "trainer", trainers)

        self.tif_dir_widget = addQgsFileWidgetToForm(topFormLayout, "output directory", directory=True)
        self.ckpt_path_widget = addQgsFileWidgetToForm(topFormLayout, "checkpoint file", filter="*.ckpt")

        # TODO: make this button greyed out until all fields above are filled
        self.run_sri_button = addButtonToForm(topFormLayout, "Run SRI Classifier", self.run_sri_classifier)

        addWidgetFromLayoutAndAddToParent(topFormLayout, topFrame)
        addToParentLayout(topFrame)

    def run_sri_classifier(self):
        # if PYTORCH_FAILED:
        #     msgBox = QMessageBox()
        #     # msgBox.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
        #     msgBox.setText(f"The package <pre>pytorch</pre> threw the following error:\n"
        #                    f"<br /><br /><code>{stack_trace[-2]}</code><br /><br />\n"
        #                    f"Please install it before running the SRI classifier.")
        #     msgBox.exec()
        #     return
        experiment = self.experiment_comboBox.currentText()
        preprocess = self.preprocess_comboBox.currentText()
        trainer = self.trainer_comboBox.currentText()
        tif_dir = self.tif_dir_widget.filePath()
        ckpt_path = self.ckpt_path_widget.filePath()

        run_experiment(experiment, trainer, preprocess, tif_dir, ckpt_path)


