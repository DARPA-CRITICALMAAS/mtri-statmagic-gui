from statmagic_backend.dev.aws_cli import *

from .TabBase import TabBase
from ..gui_helpers import *
from statmagic_backend.extract.sciencebasetools import fetch_sciencebase_files, recursive_download

import logging
logger = logging.getLogger("statmagic_gui")


class SciencebaseTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Sciencebase")
        self.parent = parent
        self.iface = self.parent.iface

        ##### IDENTIFIER FRAME #####
        IdentifierFrame, endpointLayout = addFrame(self, "VBox", "NoFrame", "Plain", 3)
        self.itemID = addLineEdit(IdentifierFrame, "Item ID:")
        self.itemID.setText("6193e9f3d34eb622f68f13a5")
        addToParentLayout(IdentifierFrame)

        ##### SEARCH FRAME #####
        searchFrame, searchLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)
        searchFormLayout = QtWidgets.QFormLayout()
        self.searchButton = addButtonToForm(searchFormLayout, "See available items", self.search_sciencebase)
        addWidgetFromLayoutAndAddToParent(searchFormLayout, searchFrame)
        addToParentLayout(searchFrame)

        ##### ITEM FRAME #####
        itemFrame, itemFrameLayout = addFrame(self, "VBox", "NoFrame", "Plain", 3)

        self.itemList = addListWidget(itemFrame)
        self.itemList.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        # self.downloadLayersButton = addButton(itemFrame, "Download Layers From Bucket", self.download_layers)

        addToParentLayout(itemFrame)


    def search_sciencebase(self):
        itemID = self.itemID.text()
        file_registry = fetch_sciencebase_files(itemID)
        items = recursive_download(file_registry, print_only=True)

        for item in items:
            self.itemList.addItem(item)
        pass