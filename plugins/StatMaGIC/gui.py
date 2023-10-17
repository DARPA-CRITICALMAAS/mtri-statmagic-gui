
from qgis.PyQt import QtGui, QtWidgets, QtCore
from qgis.PyQt.QtCore import pyqtSignal, QRect


def addTab(tabWidget, tabName):
    # create tab
    newTab = QtWidgets.QWidget()
    newTab.setObjectName(tabName)

    # set layout such that each subcomponent is arranged vertically
    tabLayout = QtWidgets.QVBoxLayout()
    tabLayout.setSpacing(0)
    tabLayout.setAlignment(QtCore.Qt.AlignTop)
    newTab.setLayout(tabLayout)

    # add tab to reference objects and return
    tabWidget.addTab(newTab, "")
    tabWidget.setTabText(tabWidget.indexOf(newTab), tabName)
    return newTab

def addLabel(layout, text):
    label = QtWidgets.QLabel()
    label.setText(text)
    label.setMinimumWidth(label.fontMetrics().width(label.text()))
    layout.addWidget(label)

def addToParentLayout(layout, parent):
    widget = QtWidgets.QWidget(parent)
    widget.setLayout(layout)
    parent.layout().addWidget(widget)

def addSpinBox(parent, name, value, max):
    layout = QtWidgets.QHBoxLayout()

    addLabel(layout, name)

    match value:
        case int():
            spinBox = QtWidgets.QSpinBox()
        case float():
            spinBox = QtWidgets.QDoubleSpinBox()
        case _:
            raise Exception("Unknown spin box type")
    spinBox.setMaximum(max)
    spinBox.setValue(value)

    layout.addWidget(spinBox)

    addToParentLayout(layout, parent)

    return spinBox

def addTwoSpinBoxes(parent, name, x, y, maxResX=1920, maxResY=1080):
    layout = QtWidgets.QHBoxLayout()

    addLabel(layout, name)

    xSpinBox = QtWidgets.QSpinBox()
    ySpinBox = QtWidgets.QSpinBox()
    xSpinBox.setMaximum(maxResX)
    ySpinBox.setMaximum(maxResY)
    xSpinBox.setValue(x)
    ySpinBox.setValue(y)

    layout.addWidget(xSpinBox)
    layout.addWidget(ySpinBox)

    addToParentLayout(layout, parent)

    return xSpinBox, ySpinBox

def addTextInput(parent, text):
    layout = QtWidgets.QHBoxLayout()

    addLabel(layout, text)

    # TODO: make the QLineEdit object expand width to fill parent
    inputBox = QtWidgets.QLineEdit()
    layout.addWidget(inputBox)

    addToParentLayout(layout, parent)

    return inputBox

def addComboBox(parent, text, items, default=None):
    layout = QtWidgets.QHBoxLayout()

    addLabel(layout, text)

    # TODO: make the QComboBox object expand width to fill parent
    comboBox = QtWidgets.QComboBox()
    comboBox.addItems(items)
    # TODO: figure out how to set default selection
    layout.addWidget(comboBox)

    addToParentLayout(layout, parent)

    return comboBox