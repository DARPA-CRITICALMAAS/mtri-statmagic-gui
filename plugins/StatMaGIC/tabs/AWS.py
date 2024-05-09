
import os
from statmagic_backend.dev.aws_cli import *

from qgis.core import Qgis

from .TabBase import TabBase
from ..gui_helpers import *
from ..popups.AWSconfig_dialog import AWS_PopUp_Menu

import logging
logger = logging.getLogger("statmagic_gui")

from PyQt5.QtWidgets import QPushButton, QMessageBox, QListWidget

class AWSTab(TabBase):
    def __init__(self, parent, tabWidget, isEnabled=True):
        super().__init__(parent, tabWidget, "AWS", isEnabled)
        self.parent = parent
        self.iface = self.parent.iface

        buckets = ["ta4-shared", "map-inbox", "statmagic"]
        self.profiles = {"ta4-shared": "macrostrat", "map-inbox": "macrostrat", "statmagic": "mtri"}
        self.endpoints = {"macrostrat": "https://s3.macrostrat.chtc.io", "mtri": ""}

        ##### CONFIGURE AWS CREDENTIALS FRAME #####
        cfgFrame, cfgLayout = addFrame(self, "HBox", "NoFrame", "Plain", 3)

        cfgFrameLabel = addLabel(cfgLayout, "Enter AWS Credentials:  ")

        self.cfgButtonMacrostrat = QPushButton()
        self.cfgButtonMacrostrat.setText("Macrostrat")
        self.cfgButtonMacrostrat.clicked.connect(self.cfgMacrostrat)
        self.cfgButtonMacrostrat.setToolTip(
            'Opens a popup window to enter AWS credentials for Macrostrat (to access ta4-shared and map-inbox buckets)')

        self.cfgButtonMTRI = QPushButton()
        self.cfgButtonMTRI.setText("MTRI")
        self.cfgButtonMTRI.clicked.connect(self.cfgMTRI)
        self.cfgButtonMTRI.setToolTip(
            'Opens a popup window to enter AWS credentials for MTRI (to access statmagic bucket)')

        cfgLayout.addWidget(self.cfgButtonMacrostrat)
        cfgLayout.addWidget(self.cfgButtonMTRI)
        
        addToParentLayout(cfgFrame)

        ##### SEARCH BUCKET FRAME #####

        searchFrame, searchLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)

        searchFrameLabel = addLabel(searchLayout, "SEARCH FOR FILES")
        makeLabelBig(searchFrameLabel)

        searchFormLayout = QtWidgets.QFormLayout()

        self.bucket = addComboBoxToForm(searchFormLayout, "Bucket to Search:", buckets)
        self.subFolder = addLineEditToForm(searchFormLayout, "Limit to Subdirectory:")
        self.filePattern = addLineEditToForm(searchFormLayout, "File Pattern:")
        self.filePattern.setToolTip(
            'Search for files containing the entered text (case-sensitive, does not accept wildcards)')
        #self.recursive = addCheckboxToForm(searchFormLayout, "Recursive", isChecked=True) # this parameter was not being used at all

        self.lsButton = addButtonToForm(searchFormLayout, "Search AWS Bucket", self.run_ls)

        addWidgetFromLayoutAndAddToParent(searchFormLayout, searchFrame)

        addToParentLayout(searchFrame)

        ##### LAYER LIST FRAME #####

        layerListFrame, layerListLayout = addFrame(self, "VBox", "NoFrame", "Plain", 3)

        self.addLayerList = addListWidget(layerListFrame)
        self.addLayerList.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.addLayerList.setSelectionMode(QListWidget.ExtendedSelection)
        self.addLayerList.setToolTip("Select files to download")

        downloadFormLayout = QtWidgets.QFormLayout()
        self.folder = QgsFileWidget()
        self.folder.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
        addFormItem(downloadFormLayout, "Download Destination:", self.folder)
        self.make_subdirs = addCheckboxToForm(downloadFormLayout, "Make Subdirectories")
        addWidgetFromLayoutAndAddToParent(downloadFormLayout, layerListFrame)

        self.downloadLayersButton = addButton(layerListFrame, "Download Layers From Bucket", self.download_layers)
        self.downloadLayersButton.setToolTip(
            'Download selected files')

        addToParentLayout(layerListFrame)

        ##### UPLOAD FRAME #####
        uploadFrame, uploadLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)

        uploadFrameLabel = addLabel(uploadLayout, "UPLOAD FILES")
        makeLabelBig(uploadFrameLabel)

        uploadFormLayout = QtWidgets.QFormLayout()

        self.uploadBucket = addComboBoxToForm(uploadFormLayout, "Bucket:", buckets)
        self.uploadFolder = addLineEditToForm(uploadFormLayout, "Subdirectory:")

        self.uploadFile = QgsFileWidget()
        addFormItem(uploadFormLayout, "File to Upload:", self.uploadFile)

        addWidgetFromLayoutAndAddToParent(uploadFormLayout, uploadFrame)

        self.uploadButton = addButton(uploadFrame, "Upload File to Bucket", self.upload_file)

        addToParentLayout(uploadFrame)

    def run_ls(self):
        self.addLayerList.clear()
        # TODO: sanitize user input before passing to shell!!!
        bucket = self.bucket.currentText()
        profile = self.profiles[bucket]
        endpoint = self.endpoints[profile]
        path = self.subFolder.text()
        pattern = self.filePattern.text()
        #recursive = self.recursive.isChecked()
        self.updateKeyVars(profile)
        files = ls(profile, endpoint, bucket, path, pattern)#, recursive)
        if files is None:
            self.noCredentialsMessage(profile)
        elif len(files)==0:
            msgBox = QMessageBox()
            msgBox.setText("No files found for this search")
            msgBox.exec()
        else:
            for file in files:
                self.addLayerList.addItem(file)

    def upload_file(self):
        filename = self.uploadFile.filePath()
        bucket = self.uploadBucket.currentText()
        profile = self.profiles[bucket]
        endpoint = self.endpoints[profile]
        path = self.uploadFolder.text()
        if path:
            obj_name = str(Path(path).joinpath(Path(filename).name))
        else:
            obj_name = Path(filename).name
        self.updateKeyVars(profile)
        upload_successful = upload(profile, endpoint, filename, bucket, object_name=obj_name)
        if upload_successful is None:
            self.noCredentialsMessage(profile)
        elif upload_successful:
            self.iface.messageBar().pushMessage(f"Uploaded {obj_name}", level=Qgis.Info)
        pass

    def download_layers(self):
        layers = extractListWidgetItems(self.addLayerList)
        items = []
        for x in range(self.addLayerList.count()):
            items.append(self.addLayerList.item(x))
        download_folder = self.folder.filePath()
        subdirs = self.make_subdirs.isChecked()
        bucket = self.bucket.currentText()
        profile = self.profiles[bucket]
        endpoint = self.endpoints[profile]
        self.updateKeyVars(profile)
        for i, layer in enumerate(layers):
            if not items[i].isSelected():
                continue
            if subdirs:
                filepath = Path(download_folder).joinpath(Path(layer))
                filepath.parent.mkdir(parents=True, exist_ok=True)
            else:
                filepath = Path(download_folder).joinpath(Path(layer).name)
            download_successful = download(profile, endpoint, bucket, layer, str(filepath))
            if download_successful:
                self.iface.messageBar().pushMessage(f"Downloaded {layer}", level=Qgis.Info)
        pass

    def cfgMTRI(self):
        popup = AWS_PopUp_Menu(self.parent, "MTRI")
        self.cfg_menu = popup.show()

    def cfgMacrostrat(self):
        popup = AWS_PopUp_Menu(self.parent, "Macrostrat")
        self.cfg_menu = popup.show()

    def updateKeyVars(self, profile):
        profile_access = os.getenv('AWS_ACCESS_KEY_ID_' + profile.upper())
        profile_secret = os.getenv('AWS_SECRET_ACCESS_KEY_' + profile.upper())
        if profile_access and profile_secret:
            os.environ['AWS_ACCESS_KEY_ID'] = profile_access
            os.environ['AWS_SECRET_ACCESS_KEY'] = profile_secret
        else:
            os.environ['AWS_ACCESS_KEY_ID'] = ''
            os.environ['AWS_SECRET_ACCESS_KEY'] = ''
        pass

    def noCredentialsMessage(self, profile):
        msgBox = QMessageBox()
        msgBox.setText("Unable to find AWS credentials for " + profile)
        msgBox.exec()