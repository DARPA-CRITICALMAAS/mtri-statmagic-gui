
import os
from statmagic_backend.dev.aws_cli import *

from .TabBase import TabBase
from ..gui_helpers import *

import logging
logger = logging.getLogger("statmagic_gui")

from PyQt5.QtWidgets import QPushButton, QFileDialog

class AWSTab(TabBase):
    def __init__(self, parent, tabWidget, isEnabled=True):
        super().__init__(parent, tabWidget, "AWS", isEnabled)
        self.parent = parent
        self.iface = self.parent.iface

        buckets = ["ta4-shared", "map-inbox", "statmagic"]
        self.profiles = {"ta4-shared": "macrostrat", "map-inbox": "macrostrat", "statmagic": "mtri"}
        self.endpoints = {"macrostrat": "https://s3.macrostrat.chtc.io", "mtri": ""}

        ##### ENDPOINT FRAME #####
        #endpointFrame, endpointLayout = addFrame(self, "VBox", "NoFrame", "Plain", 3)

        # topFrameLabel = addLabel(endpointLayout, "SPECIFY ENDPOINT")
        # makeLabelBig(topFrameLabel)

        #self.endpointURL = addLineEdit(endpointFrame, "Endpoint URL:")
        #self.endpointURL.setText("https://s3.macrostrat.chtc.io")

        #addToParentLayout(endpointFrame)

        ##### SEARCH BUCKET FRAME #####

        searchFrame, searchLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)

        searchFrameLabel = addLabel(searchLayout, "SEARCH FOR FILES")
        makeLabelBig(searchFrameLabel)

        searchFormLayout = QtWidgets.QFormLayout()

        self.bucket = addComboBoxToForm(searchFormLayout, "Bucket to Search:", buckets)

        self.filePattern = addLineEditToForm(searchFormLayout, "File Pattern:")
        self.subFolder = addLineEditToForm(searchFormLayout, "Limit to Subdirectory:")
        self.recursive = addCheckboxToForm(searchFormLayout, "Recursive")

        self.lsButton = addButtonToForm(searchFormLayout, "Search AWS Bucket", self.run_ls)

        addWidgetFromLayoutAndAddToParent(searchFormLayout, searchFrame)

        addToParentLayout(searchFrame)

        ##### LAYER LIST FRAME #####

        layerListFrame, layerListLayout = addFrame(self, "VBox", "NoFrame", "Plain", 3)

        self.addLayerList = addListWidget(layerListFrame)
        self.addLayerList.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.selectDirButton = QPushButton()
        self.selectDirButton.setText('Select Download Destination')
        self.selectDirButton.clicked.connect(self.chooseFolder)
        self.selectDirButton.setToolTip(
            'Opens up a new window to select download destination')
        layerListLayout.addWidget(self.selectDirButton)

        self.downloadLayersButton = addButton(layerListFrame, "Download Layers From Bucket", self.download_layers)

        addToParentLayout(layerListFrame)

        ##### UPLOAD FRAME #####
        uploadFrame, uploadLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)

        uploadFrameLabel = addLabel(uploadLayout, "UPLOAD FILES")
        makeLabelBig(uploadFrameLabel)

        uploadFormLayout = QtWidgets.QFormLayout()

        self.uploadBucket = addComboBoxToForm(uploadFormLayout, "Bucket:", buckets)
        self.uploadFolder = addLineEditToForm(uploadFormLayout, "Subdirectory:")

        self.selectFileButton = QPushButton()
        self.selectFileButton.setText('Select File')
        self.selectFileButton.clicked.connect(self.chooseFiles)
        self.selectFileButton.setToolTip(
            'Opens up a new window with options to select files to upload')
        uploadFormLayout.addWidget(self.selectFileButton)

        addWidgetFromLayoutAndAddToParent(uploadFormLayout, uploadFrame)

        self.uploadButton = addButton(uploadFrame, "Upload Files to Bucket", self.upload_files)

        addToParentLayout(uploadFrame)

    def run_ls(self):
        self.addLayerList.clear()
        # TODO: sanitize user input before passing to shell!!!
        bucket = self.bucket.currentText()
        profile = self.profiles[bucket]
        endpoint = self.endpoints[profile]
        path = self.subFolder.text()
        pattern = self.filePattern.text()
        recursive = self.recursive.isChecked()
        files = ls(profile, endpoint, bucket, path, pattern, recursive)
        for file in files:
            self.addLayerList.addItem(file)

    def chooseFolder(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setViewMode(QFileDialog.Detail)
        if dialog.exec_():
            self.downloadFolder = dialog.selectedFiles()[0]

    def chooseFiles(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setViewMode(QFileDialog.Detail)
        if dialog.exec_():
            self.filesToUpload = dialog.selectedFiles()

    def upload_files(self):
        bucket = self.uploadBucket.currentText()
        profile = self.profiles[bucket]
        endpoint = self.endpoints[profile]
        path = self.uploadFolder.text()
        for filename in self.filesToUpload:
            if path:
                obj_name = path + '/' + Path(filename).name
                upload_successful = upload(profile, endpoint, filename, bucket, object_name=obj_name)
            else:
                upload_successful = upload(profile, endpoint, filename, bucket)
        pass

    def download_layers(self):
        layers = extractListWidgetItems(self.addLayerList)
        bucket = self.bucket.currentText()
        profile = self.profiles[bucket]
        endpoint = self.endpoints[profile]
        for layer in layers:
            filename = self.downloadFolder + '/' + Path(layer).name
            download_successful = download(profile, endpoint, bucket, layer, filename)
        pass