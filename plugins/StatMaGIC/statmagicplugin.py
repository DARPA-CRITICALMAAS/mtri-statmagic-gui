from pathlib import Path
from PyQt5.QtWidgets import QAction, QWidget
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
import time
import numpy as np
from osgeo import gdal



from .dockwidget import StatMaGICDockWidget

try:
    from pydevd import settrace
    settrace(host='localhost', port=5678, stdoutToServer=True, stderrToServer=True)
except ConnectionRefusedError:
    pass


class StatMaGICPlugin(QWidget):

    def __init__(self, iface):
        super(StatMaGICPlugin, self).__init__(None)
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        # Declare instance attributes
        self.actions = []
        self.menu = "StatMaGIC"
        self.toolbar = self.iface.addToolBar("StatMaGIC")
        self.toolbar.setObjectName("StatMaGIC")

        self.pluginIsActive = False
        self.dockWidget = None

    def add_action(self, icon_path, text, callback,
                   enabled_flag=True, add_to_menu=True, add_to_toolbar=True,
                   status_tip=None, whats_this=None, parent=None):
        """
        Creates a QAction object (usually a button) with the given icon,
        adds it to the list of actions, registers it with the given callback,
        and populates all the UI elements that should trigger the callback.

        Parameters
        ----------
        icon_path : str
            Path to the icon for this action. Can be a resource path
            (e.g. ':/plugins/foo/bar.png') or a normal file system path.
            Note that ``pathlib.Path`` objects are not yet supported by QT.
        text : str
            Text that should be shown in menu items for this action.
        callback : callable
            Function to be called when the action is triggered.
        enabled_flag : bool, optional
            A flag indicating if the action should be enabled by default.
        add_to_menu : bool, optional
            Flag indicating whether the action should be added to the menu.
        add_to_toolbar : bool, optional
            Flag indicating whether the action should be added to the toolbar.
        status_tip : str, optional
            Text to show in a popup when mouse pointer hovers over the action.
        whats_this : str, optional
            Text to show in the status bar when the mouse pointer
            hovers over the action.
        parent : QWidget, optional
            Parent widget for the new action.

        Returns
        -------
        action : QAction
            The action that was created. Note that the action is also added to
            the ``self.actions`` list.
        """
        # Create the button and register the callback
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        # Add descriptive text
        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)

        # Add other gui elements that trigger the callback
        if add_to_toolbar:
            self.toolbar.addAction(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        iconPath = str(Path(__file__).parent / "icon.png")
        self.add_action(iconPath,
                        text="StatMaGIC",
                        callback=self.run,
                        parent=self.iface)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu("StatMaGIC", action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def getSelectedLayer(self):
        selectedLayer = self.iface.layerTreeView().selectedLayers()[0]
        return selectedLayer

    def run(self):
        if not self.pluginIsActive:
            self.pluginIsActive = True
            if self.dockWidget is None:
                self.dockWidget = StatMaGICDockWidget(self)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockWidget)
            self.dockWidget.closingPlugin.connect(self.onClosePlugin)
            self.dockWidget.show()

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockWidget is closed"""
        self.dockWidget.closingPlugin.disconnect(self.onClosePlugin)

        self.pluginIsActive = False