from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QPushButton, QLabel, QMessageBox, QTextEdit, QComboBox, QTableView, QCheckBox, QVBoxLayout, QHBoxLayout, QFrame, QFormLayout, QSpacerItem
from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5.QtGui import QPalette, QColor
from qgis.core import QgsVectorLayer, QgsProject, QgsRasterLayer, QgsMapLayerProxyModel, QgsPoint, QgsCoordinateTransform

from .TabBase import TabBase
from ..gui_helpers import *
from ..widgets.collapsible_box import CollapsibleBox


class CollapsibleTab(TabBase):
    def __init__(self, parent, tabWidget):
        super().__init__(parent, tabWidget, "Collapsible")

        self.parent = parent
        self.iface = self.parent.iface

        frame = QtWidgets.QFrame(self)
        frame.setFrameShape(getattr(QtWidgets.QFrame, "Panel"))
        frame.setFrameShadow(getattr(QtWidgets.QFrame, "Sunken"))
        frame.setContentsMargins(0,0,0,0)
        frame.setLineWidth(5)

        layout = QFormLayout()
        layout.setVerticalSpacing(0)
        layout.setHorizontalSpacing(0)
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)
        layout.setAlignment(Qt.AlignTop)
        layout.setFormAlignment(Qt.AlignTop)
        layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)

        self.test_btn = QPushButton()
        self.test_btn.setText("Test")
        self.test_btn.clicked.connect(self.pushed_btn)

        text_label1 = QLabel('Query Input')
        text_label2 = QLabel('Query Input')

        self.text_box = QTextEdit(self)
        self.text_box.setReadOnly(False)
        self.text_box.setMaximumHeight(100)


        layout.addRow(text_label1, self.test_btn)
        layout.addRow(text_label2, self.text_box)

        frame.setLayout(layout)

        self.box = CollapsibleBox("Test Box")

        self.tabLayout.addWidget(frame)
        self.tabLayout.addWidget(self.box)
        self.tabLayout.addStretch()

        lay = QVBoxLayout()
        lay.addWidget(QLabel("One"))
        lay.addWidget(QLabel("Two"))
        lay.addWidget(QTextEdit())

        frame2 = QtWidgets.QFrame()
        frame2.setFrameShape(getattr(QtWidgets.QFrame, "Panel"))
        frame2.setFrameShadow(getattr(QtWidgets.QFrame, "Sunken"))
        frame2.setContentsMargins(0, 0, 0, 0)
        frame2.setLineWidth(5)

        lay2 = QVBoxLayout()
        self.text_edit2 = QTextEdit()
        lay2.addWidget(self.text_edit2)
        frame2.setLayout(lay2)

        #lay.addWidget(frame2)

        self.box.setContentLayout(lay)


    def pushed_btn(self):
        print("You pushed the button!")
