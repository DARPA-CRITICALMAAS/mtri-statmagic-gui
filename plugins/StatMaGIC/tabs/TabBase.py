from PyQt5 import QtCore, QtWidgets


class TabBase(QtWidgets.QWidget):
    def __init__(self, parent, tabWidget, tabName, isEnabled=True):
        # create tab
        super().__init__(parent)
        self.setObjectName(tabName)

        # copy these pointers for convenience
        self.iface = parent.iface
        self.canvas = self.iface.mapCanvas()

        # set layout such that each subcomponent is arranged vertically
        self.tabLayout = QtWidgets.QVBoxLayout()
        self.tabLayout.setSpacing(0)
        self.tabLayout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(self.tabLayout)

        # add tab to reference objects
        self.tabWidget = tabWidget
        self.tabWidget.addTab(self, "")
        self.tabWidget.setTabText(tabWidget.indexOf(self), tabName)
        self.tabWidget.setTabEnabled(tabWidget.indexOf(self), isEnabled)

    def enable(self):
        self.tabWidget.setTabEnabled(self.tabWidget.indexOf(self), True)

    def disable(self):
        self.tabWidget.setTabEnabled(self.tabWidget.indexOf(self), False)
