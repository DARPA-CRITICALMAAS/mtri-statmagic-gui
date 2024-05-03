
import builtins

import numpy as np
from qgis.PyQt import QtGui, QtWidgets, QtCore
from qgis.gui import QgsFieldComboBox, QgsMapLayerComboBox, QgsFileWidget


def getLayoutFromString(layout_str):
    match layout_str:
        case "HBox" | "HBoxLayout" | "QHBoxLayout":
            layout = QtWidgets.QHBoxLayout()
        case "VBox" | "VBoxLayout" | "QVBoxLayout":
            layout = QtWidgets.QVBoxLayout()
        case "Form" | "FormLayout" | "QFormLayout":
            # only use this if the parent widget needs ONLY a form layout
            layout = QtWidgets.QFormLayout()
        case "Grid" | "GridLayout" | "QGridLayout":
            layout = QtWidgets.QGridLayout()
        case "Stacked" | "StackedLayout" | "QStackedLayout":
            layout = QtWidgets.QStackedLayout()
        case _:
            layout = QtWidgets.QBoxLayout()

    return layout


def addLabel(layout, text, frameShape=None, gridPos=()):
    label = QtWidgets.QLabel()
    label.setText(text)

    if "\n" in text:
        # if there are multiple lines, set width according to the longest line
        labelLines = text.split("\n")
        longestIndex = np.argmax(map(lambda x: len(x), labelLines))
        longestLine = labelLines[longestIndex]
        label.setMinimumWidth(label.fontMetrics().width(longestLine))
    else:
        label.setMinimumWidth(label.fontMetrics().width(label.text()))

    if frameShape is not None:
        if isinstance(frameShape, str):
            frameShape = getattr(QtWidgets.QFrame, frameShape)
        label.setFrameShape(frameShape)
    layout.addWidget(label, *gridPos)
    return label


def getAlignmentFromString(align_str):
    if not align_str.startswith("Align"):
        align_str = f"Align{align_str}"
    alignment = getattr(QtCore.Qt, align_str)
    return alignment


def alignLayoutAndAddToParent(layout, parent, alignment):
    outerLayout = QtWidgets.QHBoxLayout()

    match alignment:
        case "Center" | "Middle":
            addEmptyFrame(outerLayout)
            outerLayout.addLayout(layout)
            addEmptyFrame(outerLayout)
        case "Right" | "Bottom":
            addEmptyFrame(outerLayout)
            outerLayout.addLayout(layout)
        case "Left" | "Top":
            outerLayout.addLayout(layout)
            addEmptyFrame(outerLayout)
        case _:
            raise Exception("Invalid Alignment")

    addWidgetFromLayoutAndAddToParent(outerLayout, parent)


def addBigLabel(layout, text, frameShape=None, align="Center", gridPos=()):
    label = addLabel(layout, text, frameShape, gridPos)

    font = QtGui.QFont()
    font.setFamily("Ubuntu Mono")
    font.setPointSize(12)
    font.setBold(True)
    font.setWeight(75)

    label.setFont(font)
    alignment = getAlignmentFromString(align)
    label.setAlignment(alignment)

    return label


def addWidgetFromLayout(layout, parent):
    widget = QtWidgets.QWidget(parent)
    widget.setLayout(layout)
    return widget


def addToParentLayout(widget, gridPos=()):
    widget.parent().layout().addWidget(widget, *gridPos)


def addWidgetFromLayoutAndAddToParent(layout, parent, gridPos=()):
    widget = QtWidgets.QWidget(parent)
    widget.setLayout(layout)
    parent.layout().addWidget(widget, *gridPos)
    return widget


def addListWidget(parent):
    widget = QtWidgets.QListWidget(parent)
    addToParentLayout(widget)
    return widget


def addFrame(parent, layout_str, shape, shadow, linewidth, spacing=(0,0), margins=0):
    frame = QtWidgets.QFrame(parent)

    # If all margins are the same, allow the user to just specify one number
    if isinstance(margins, int):
        margins = (margins, margins, margins, margins)

    frameLayout = getLayoutFromString(layout_str)
    match frameLayout:
        case QtWidgets.QFormLayout() | QtWidgets.QGridLayout():
            frameLayout.setVerticalSpacing(spacing[0])
            frameLayout.setHorizontalSpacing(spacing[1])
        case QtWidgets.QHBoxLayout():
            frameLayout.setSpacing(spacing[1])
        case _:
            frameLayout.setSpacing(spacing[0])

    frame.setLayout(frameLayout)
    frame.setContentsMargins(*margins)

    if isinstance(shape, str):
        shape = getattr(QtWidgets.QFrame, shape)
    if isinstance(shadow, str):
        shadow = getattr(QtWidgets.QFrame, shadow)
    frame.setFrameShape(shape)
    frame.setFrameShadow(shadow)

    # TODO: maybe we could just use the default line width?
    frame.setLineWidth(linewidth)

    addToParentLayout(frame)

    return frame, frameLayout


def addEmptyFrame(layout):
    emptyFrame = QtWidgets.QFrame(None)
    emptyFrame.setFrameShape(QtWidgets.QFrame.NoFrame)
    emptyFrame.setFrameShadow(QtWidgets.QFrame.Plain)
    # TODO: margins?
    layout.addWidget(emptyFrame)


def _createButton(parent, text, callback):
    button = QtWidgets.QPushButton(parent)
    button.setText(text)
    button.clicked.connect(callback)
    return button


def addButton(parent, text, callback, gridPos=(), align=None):
    button = _createButton(parent, text, callback)

    if align is not None:
        buttonFrame, buttonLayout = addFrame(parent, "HBox", "NoFrame", "Plain", 3)

        if align == "Center" or align == "Right":
            addEmptyFrame(buttonLayout)

        buttonLayout.addWidget(button)

        if align == "Center" or align == "Left":
            addEmptyFrame(buttonLayout)

        addToParentLayout(buttonFrame)
    else:
        addToParentLayout(button, gridPos)

    return button


def addButtonToForm(formLayout, text, callback):
    button = _createButton(None, text, callback)
    addFormItem(formLayout, "", button)
    return button


def _createSpinBox(parent, dtype, value, min, max, step):
    match dtype:
        case builtins.int:
            spinBox = QtWidgets.QSpinBox(parent)
        case builtins.float:
            spinBox = QtWidgets.QDoubleSpinBox(parent)
            value = float(value)
            max = float(max)
            step = float(step)
        case _:
            raise Exception("Unknown spin box type")

    spinBox.setMinimum(min)
    spinBox.setMaximum(max)

    # verify that the initial value is in a valid range
    if value < min:
        value = min
    elif value > max:
        value = max

    spinBox.setValue(value)
    spinBox.setSingleStep(step)
    return spinBox


def addSpinBox(parent, name, layout_str="HBox", dtype=int, value=0, min=0, max=10, step=1):
    layout = getLayoutFromString(layout_str)

    addLabel(layout, name)

    spinBox = _createSpinBox(parent, dtype, value, min, max, step)

    layout.addWidget(spinBox)

    addWidgetFromLayoutAndAddToParent(layout, parent)

    return spinBox


def addSpinBoxToGrid(parent, name, dtype=int, value=0, min=0, max=10, step=1, gridPos=()):
    # NOTE: do not call this function if parent does not have a grid layout
    gridLayout = parent.layout()
    hboxLayout = QtWidgets.QHBoxLayout()

    addLabel(hboxLayout, name)
    spinBox = _createSpinBox(None, dtype, value, min, max, step)
    hboxLayout.addWidget(spinBox)

    hboxWidget = addWidgetFromLayout(hboxLayout, parent)

    gridLayout.addWidget(hboxWidget, *gridPos)
    return spinBox


def addSpinBoxToForm(formLayout, text, dtype=int, value=0, min=0, max=10, step=1):
    spinBox = _createSpinBox(None, dtype, value, min, max, step)
    addFormItem(formLayout, text, spinBox)
    return spinBox


def addTwoSpinBoxes(parent, name1, name2, x, y, layout_str="HBox", dtype=int,
                    minX=0, minY=0, maxX=1920, maxY=1080, stepX=1, stepY=1):
    layout = getLayoutFromString(layout_str)

    addLabel(layout, name1)

    xSpinBox = _createSpinBox(parent, dtype, x, minX, maxX, stepX)
    ySpinBox = _createSpinBox(parent, dtype, y, minY, maxY, stepY)

    layout.addWidget(xSpinBox)
    addLabel(layout, name2)
    layout.addWidget(ySpinBox)

    addWidgetFromLayoutAndAddToParent(layout, parent)

    return xSpinBox, ySpinBox


def addTwoSpinBoxesToForm(formLayout, text, name1, name2, x, y, dtype=int,
                          minX=0, minY=0, maxX=1920, maxY=1080, stepX=1, stepY=1):
    gridLayout = QtWidgets.QGridLayout()

    xSpinBox = _createSpinBox(None, dtype, x, minX, maxX, stepX)
    ySpinBox = _createSpinBox(None, dtype, y, minY, maxY, stepY)

    addLabel(gridLayout, name1, gridPos=(0,0))
    addLabel(gridLayout, name2, gridPos=(0,1))

    gridLayout.addWidget(xSpinBox, 1, 0)
    gridLayout.addWidget(ySpinBox, 1, 1)

    gridWidget = addWidgetFromLayout(gridLayout, None)

    addFormItem(formLayout, text, gridWidget)

    return xSpinBox, ySpinBox


def addFormItem(layout, text, item):
    # NOTE: this only works if layout is an instance of QFormLayout()
    label = QtWidgets.QLabel(text)
    layout.addRow(label, item)


def addLineEdit(parent, text):
    layout = QtWidgets.QHBoxLayout()

    addLabel(layout, text)

    # TODO: make the QLineEdit object expand width to fill parent
    inputBox = QtWidgets.QLineEdit()
    layout.addWidget(inputBox)

    addWidgetFromLayoutAndAddToParent(layout, parent)

    return inputBox


def addLineEditToGrid(parent, text, gridPos=()):
    gridLayout = parent.layout()
    hboxLayout = QtWidgets.QHBoxLayout()

    addLabel(hboxLayout, text)

    # TODO: make the QLineEdit object expand width to fill parent
    inputBox = QtWidgets.QLineEdit()
    hboxLayout.addWidget(inputBox)

    addWidgetFromLayout(hboxLayout, parent)

    hboxWidget = addWidgetFromLayout(hboxLayout, parent)
    gridLayout.addWidget(hboxWidget, *gridPos)

    return inputBox


def addLineEditToForm(formLayout, label, value=""):
    lineEdit = QtWidgets.QLineEdit()
    lineEdit.setText(str(value))
    addFormItem(formLayout, label, lineEdit)
    return lineEdit


def addTextEdit(parent, text):
    layout = QtWidgets.QHBoxLayout()

    addLabel(layout, text)

    # TODO: make the QTextEdit object expand width to fill parent
    inputBox = QtWidgets.QTextEdit()
    layout.addWidget(inputBox)

    addWidgetFromLayoutAndAddToParent(layout, parent)

    return inputBox


def addComboBox(parent, text, items, layout_str="HBox", default=None):
    layout = getLayoutFromString(layout_str)

    addLabel(layout, text)

    # TODO: make the QComboBox object expand width to fill parent
    comboBox = QtWidgets.QComboBox()
    comboBox.addItems(items)
    # TODO: figure out how to set default selection
    layout.addWidget(comboBox)

    addWidgetFromLayoutAndAddToParent(layout, parent)

    return comboBox


def addComboBoxToForm(formLayout, text, items):
    comboBox = QtWidgets.QComboBox()
    comboBox.addItems(items)
    addFormItem(formLayout, text, comboBox)

    return comboBox


def addComboBoxToGrid(parent, text, items, gridPos=()):
    gridLayout = parent.layout()
    hboxLayout = QtWidgets.QHBoxLayout()

    addLabel(hboxLayout, text)

    comboBox = QtWidgets.QComboBox()
    comboBox.addItems(items)
    hboxLayout.addWidget(comboBox)

    hboxWidget = addWidgetFromLayout(hboxLayout, parent)

    gridLayout.addWidget(hboxWidget, *gridPos)

    return comboBox


def _addQgsWidget(QgsClass, parent, text, layout_str, align, surround=False):
    layout = getLayoutFromString(layout_str)

    if align == "Center" or align == "Right":
        addEmptyFrame(layout)

    addLabel(layout, text)

    if surround:
        outerWidget = addWidgetFromLayout(layout, parent)
        widget = QgsClass(outerWidget)
        layout.addWidget(widget)
        addToParentLayout(outerWidget)
    else:
        widget = QgsClass(parent)
        layout.addWidget(widget)
        addToParentLayout(widget)

    if align == "Center" or align == "Left":
        addEmptyFrame(layout)

    return widget


def addQgsFieldComboBox(parent, text, layout_str="HBox", align=None):
    return _addQgsWidget(QgsFieldComboBox, parent, text, layout_str, align, surround=True)


def addQgsFileWidget(parent, text, layout_str="HBox", align=None):
    return _addQgsWidget(QgsFileWidget, parent, text, layout_str, align)


def addQgsMapLayerComboBox(parent, text, layout_str="VBox", align=None):
    return _addQgsWidget(QgsMapLayerComboBox, parent, text, layout_str, align, surround=True)


def addQgsMapLayerComboBoxToForm(formLayout, text):
    comboBox = QgsMapLayerComboBox()
    addFormItem(formLayout, text, comboBox)
    return comboBox


def addQgsFieldComboBoxToForm(formLayout, text):
    comboBox = QgsFieldComboBox()
    addFormItem(formLayout, text, comboBox)
    return comboBox


def addQgsFileWidgetToForm(formLayout, text, directory=False, filter=None):
    fileWidget = QgsFileWidget()
    if directory:
        fileWidget.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
    if filter is not None:
        fileWidget.setFilter(filter)
    addFormItem(formLayout, text, fileWidget)
    return fileWidget


def _createCheckBox(parent, text, isChecked):
    checkBoxWidget = QtWidgets.QCheckBox(parent)
    checkBoxWidget.setText(text)
    checkBoxWidget.setChecked(isChecked)
    return checkBoxWidget


def addCheckboxToForm(formLayout, text, isChecked=False):
    checkBoxWidget = _createCheckBox(None, text, isChecked)
    addFormItem(formLayout, "", checkBoxWidget)
    return checkBoxWidget


def addCheckbox(parent, label, isChecked=False, gridPos=()):
    checkBoxWidget = _createCheckBox(parent, label, isChecked)
    addToParentLayout(checkBoxWidget, gridPos)
    return checkBoxWidget


def addTwoCheckboxes(parent, label1, label2, firstChecked=False, secondChecked=False):
    checkboxLayout = QtWidgets.QVBoxLayout()
    checkboxWidget = addWidgetFromLayout(checkboxLayout, parent)

    selectionBox1 = _createCheckBox(checkboxWidget, label1, firstChecked)
    selectionBox2 = _createCheckBox(checkboxWidget, label2, secondChecked)

    checkboxLayout.addWidget(selectionBox1)
    checkboxLayout.addWidget(selectionBox2)

    addToParentLayout(checkboxWidget)

    return selectionBox1, selectionBox2


def addTable(parent, frameShape, frameShadow, cols=0, rows=0, gridPos=()):
    tableWidget = QtWidgets.QTableWidget(parent)
    tableWidget.setFrameShape(getattr(QtWidgets.QFrame, frameShape))
    tableWidget.setFrameShadow(getattr(QtWidgets.QFrame, frameShadow))
    tableWidget.setColumnCount(cols)
    tableWidget.setRowCount(rows)
    addToParentLayout(tableWidget, gridPos)
    return tableWidget


def makeLabelBig(label):
    font = QtGui.QFont()
    font.setPointSize(12)
    font.setBold(True)
    font.setWeight(75)

    label.setFont(font)
    label.setAlignment(QtCore.Qt.AlignCenter)


def extractListWidgetItems(listWidget):
    items = []
    for x in range(listWidget.count()):
        items.append(listWidget.item(x).text())
    return items

