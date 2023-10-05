from PyQt5 import QtCore, QtGui, QtWidgets
class Ui_test2DockWidgetBase(object):
    def setupUi(self, test2DockWidgetBase):
        test2DockWidgetBase.setObjectName("test2DockWidgetBase")
        test2DockWidgetBase.resize(232, 141)
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.gridLayout = QtWidgets.QGridLayout(self.dockWidgetContents)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(self.dockWidgetContents)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        test2DockWidgetBase.setWidget(self.dockWidgetContents)
        self.retranslateUi(test2DockWidgetBase)
        QtCore.QMetaObject.connectSlotsByName(test2DockWidgetBase)
    def retranslateUi(self, test2DockWidgetBase):
        _translate = QtCore.QCoreApplication.translate
        test2DockWidgetBase.setWindowTitle(_translate("test2DockWidgetBase", "test2"))
        self.label.setText(_translate("test2DockWidgetBase", "Replace this QLabel\n"
"with the desired\n"
"plugin content."))
