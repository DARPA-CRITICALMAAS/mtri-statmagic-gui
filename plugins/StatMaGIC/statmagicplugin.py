from pathlib import Path
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
import time
from pydevd import settrace

settrace(host='localhost', port=5678, stdoutToServer=True, stderrToServer=True)
pass

class StatMaGICPlugin:

    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        icon = str(Path(__file__) / 'barChart.png')
        self.add_action()

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self):
        self.iface.messageBar().pushMessage('Magic executed successfully.')