"""
Credit where credit is due: https://stackoverflow.com/questions/52615115/how-to-create-collapsible-box-in-pyqt
"""
import logging

from PyQt5 import QtCore, QtGui, QtWidgets


logger = logging.getLogger("statmagic_gui")


class CollapsibleBox(QtWidgets.QWidget):
    def __init__(self, title="", parent=None):
        super(CollapsibleBox, self).__init__(parent)
        logger.debug("Creating collapse box")

        self.toggle_button = QtWidgets.QToolButton(
            text=title, checkable=True, checked=False
        )

        self.open_flag = False
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon
        )
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.pressed.connect(self.on_pressed)

        self.toggle_animation = QtCore.QParallelAnimationGroup(self)

        self.content_area = QtWidgets.QScrollArea(
            maximumHeight=0, minimumHeight=0
        )
        self.content_area.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        self.content_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggle_button)
        lay.addWidget(self.content_area)

        self.toggle_animation.addAnimation(
            QtCore.QPropertyAnimation(self, b"minimumHeight")
        )
        self.toggle_animation.addAnimation(
            QtCore.QPropertyAnimation(self, b"maximumHeight")
        )
        self.toggle_animation.addAnimation(
            QtCore.QPropertyAnimation(self.content_area, b"maximumHeight")
        )

    @QtCore.pyqtSlot()
    def on_pressed(self):
        # Joe: This business with the open_flag should not be necessary, but I saw behavior where it seemed like this callback
        # was reached before the 'isChecked' method on the toggle would return the new state, so the widget would get stuck open or closed
        # Manually tracking how many times this callback is reached is a work around
        self.open_flag = not self.open_flag
        self.toggle_button.setChecked(self.open_flag)
        checked = self.toggle_button.isChecked()

        self.toggle_button.setArrowType(
            QtCore.Qt.RightArrow if not checked else QtCore.Qt.DownArrow
        )
        self.toggle_animation.setDirection(
            QtCore.QAbstractAnimation.Backward
            if not checked
            else QtCore.QAbstractAnimation.Forward
        )
        self.toggle_animation.start()

    def setContentLayout(self, layout):
        lay = self.content_area.layout()
        del lay
        self.content_area.setLayout(layout)
        collapsed_height = (
            self.sizeHint().height() - self.content_area.maximumHeight()
        )
        content_height = layout.sizeHint().height()
        for i in range(self.toggle_animation.animationCount()):
            animation = self.toggle_animation.animationAt(i)
            animation.setDuration(500)
            animation.setStartValue(collapsed_height)
            animation.setEndValue(collapsed_height + content_height)

        content_animation = self.toggle_animation.animationAt(
            self.toggle_animation.animationCount() - 1
        )
        content_animation.setDuration(500)
        content_animation.setStartValue(0)
        content_animation.setEndValue(content_height)
