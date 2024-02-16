

from statmagic_backend.dev.aws_cli import *

from .TabBase import TabBase
from ..gui_helpers import *


class AWSTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "AWS")
        self.parent = parent
        self.iface = self.parent.iface

        ##### ENDPOINT FRAME #####
        endpointFrame, endpointLayout = addFrame(self, "VBox", "NoFrame", "Plain", 3)

        # topFrameLabel = addLabel(endpointLayout, "SPECIFY ENDPOINT")
        # makeLabelBig(topFrameLabel)

        self.endpointURL = addLineEdit(endpointFrame, "Endpoint URL:")
        self.endpointURL.setText("https://s3.macrostrat.chtc.io")

        addToParentLayout(endpointFrame)

        ##### SEARCH BUCKET FRAME #####

        searchFrame, searchLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)

        searchFrameLabel = addLabel(searchLayout, "SEARCH FOR FILES")
        makeLabelBig(searchFrameLabel)

        searchFormLayout = QtWidgets.QFormLayout()

        self.filePattern = addLineEditToForm(searchFormLayout, "File Pattern:")

        buckets = ["ta4-shared", "map-inbox"]
        self.bucket = addComboBoxToForm(searchFormLayout, "Bucket to Search:", buckets)
        self.subFolder = addLineEditToForm(searchFormLayout, "Limit to Subdirectory:")
        self.recursive = addCheckboxToForm(searchFormLayout, "Recursive")

        self.lsButton = addButtonToForm(searchFormLayout, "Search AWS Bucket", self.run_ls)

        addWidgetFromLayoutAndAddToParent(searchFormLayout, searchFrame)

        addToParentLayout(searchFrame)

        ##### LAYER LIST FRAME #####

        layerListFrame, layerListLayout = addFrame(self, "VBox", "NoFrame", "Plain", 3)

        self.addLayerList = addListWidget(layerListFrame)
        self.addLayerList.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.downloadLayersButton = addButton(layerListFrame, "Download Layers From Bucket", self.download_layers)

        addToParentLayout(layerListFrame)

    def run_ls(self):
        self.addLayerList.clear()
        # TODO: sanitize user input before passing to shell!!!
        endpoint = self.endpointURL.text()
        bucket = self.bucket.currentText()
        path = self.subFolder.text()
        pattern = self.filePattern.text()
        recursive = self.recursive.isChecked()
        files = ls(endpoint, bucket, path, pattern, recursive)
        for file in files:
            self.addLayerList.addItem(file)

    def download_layers(self):
        layers = extractListWidgetItems(self.addLayerList)
        pass