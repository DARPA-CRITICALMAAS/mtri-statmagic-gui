from pathlib import Path
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
import time
from pydevd import settrace

pass

class StatMaGICPlugin:

    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        iconPath = Path(__file__).parent / "icon.png"
        icon = QIcon(str(iconPath))
        self.action = QAction(icon, 'StatMaGIC', self.iface.mainWindow())
        self.iface.addToolBarIcon(self.action)
        self.action.triggered.connect(self.run)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self):
        self.iface.messageBar().pushMessage('Magic executed successfully.')
        settrace(host='localhost', port=5678, stdoutToServer=True, stderrToServer=True)
        pass