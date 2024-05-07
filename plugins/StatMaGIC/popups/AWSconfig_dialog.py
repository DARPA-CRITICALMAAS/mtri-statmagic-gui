import os
from qgis.PyQt.QtWidgets import QDialog

from ..gui_helpers import *

import logging
logger = logging.getLogger("statmagic_gui")

class AWS_PopUp_Menu(QDialog):

    def __init__(self, parent, profile):
        self.parent = parent
        self.iface = parent.iface
        super(AWS_PopUp_Menu, self).__init__(parent)
        QDialog.setWindowTitle(self, "Credentials for " + profile)
        self.profile = profile.upper()
        self.setLayout(QtWidgets.QVBoxLayout())

        ##### KEY FRAME #####
        keyFrame, keyLayout = addFrame(self, "VBox", "Panel", "Sunken", 3)

        keyFormLayout = QtWidgets.QFormLayout()

        self.accessKey = addLineEditToForm(keyFormLayout, "Access Key:")
        self.secretKey = addLineEditToForm(keyFormLayout, "Secret Key:")

        addWidgetFromLayoutAndAddToParent(keyFormLayout, keyFrame)

        self.button = addButton(keyFrame, "Update Credentials", self.set_vars)

        addToParentLayout(keyFrame)

    def set_vars(self):
        access_key = self.accessKey.text()
        secret_key = self.secretKey.text()
        os.environ['AWS_ACCESS_KEY_ID_'+self.profile] = access_key
        os.environ['AWS_SECRET_ACCESS_KEY_'+self.profile] = secret_key
        self.reject()
        pass