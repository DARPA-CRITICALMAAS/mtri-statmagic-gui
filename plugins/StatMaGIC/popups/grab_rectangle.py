from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand, QgsMapTool
from qgis.core import QgsWkbTypes, QgsPoint, QgsGeometry, QgsFeature, Qgis, QgsRectangle, QgsPointXY
# from PyQt5 import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal

# From:
# https://gis.stackexchange.com/questions/407389/rectanglemaptool-for-defining-polygon-using-mouse-click-does-not-work-in-qgis-3

import logging
logger = logging.getLogger("statmagic_gui")

class RectangleMapTool(QgsMapToolEmitPoint):
    rect_created = pyqtSignal(QgsRectangle)
    def __init__(self, canvas):
        logger.debug('tool init')
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.msg = QMessageBox()
        self.rubberBand = QgsRubberBand(self.canvas, Qgis.GeometryType.Polygon)
        self.rubberBand.setColor(Qt.red)
        self.rubberBand.setWidth(1)
        self.reset()
        # self.rect_created.connect(self.rectangle_created)

    def rectangle_created(self, r):
        self.msg.setText(str(r))
        self.msg.show()

    def reset(self):
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.rubberBand.reset(Qgis.GeometryType.Polygon)

    def canvasPressEvent(self, e):
        logger.debug('canvas pressed')
        self.startPoint = self.toMapCoordinates(e.pos())
        self.endPoint = self.startPoint
        self.isEmittingPoint = True
        self.showRect(self.startPoint, self.endPoint)

    def canvasReleaseEvent(self, e):
        self.isEmittingPoint = False
        r = self.rectangle()
        if r is not None:
            self.rect_created.emit(r)

    def canvasMoveEvent(self, e):
        if not self.isEmittingPoint:
            return
        self.endPoint = self.toMapCoordinates(e.pos())
        self.showRect(self.startPoint, self.endPoint)

    def showRect(self, startPoint, endPoint):
        self.rubberBand.reset()
        if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
            return
        point1 = QgsPointXY(startPoint.x(), startPoint.y())
        point2 = QgsPointXY(startPoint.x(), endPoint.y())
        point3 = QgsPointXY(endPoint.x(), endPoint.y())
        point4 = QgsPointXY(endPoint.x(), startPoint.y())
        point5 = point1
        self.rubberBand.addPoint(point1, False)
        self.rubberBand.addPoint(point2, False)
        self.rubberBand.addPoint(point3, False)
        self.rubberBand.addPoint(point4, False)
        self.rubberBand.addPoint(point5, True)
        # true to update canvas
        self.rubberBand.show()

    def rectangle(self):
        if self.startPoint is None or self.endPoint is None:
            return None
        elif (self.startPoint.x() == self.endPoint.x() or \
              self.startPoint.y() == self.endPoint.y()):
            return None
        return QgsRectangle(self.startPoint, self.endPoint)


    def geometry(self):
        rb = self.rubberBand
        return self.rubberBand.asGeometry()

    def deactivate(self):
        self.rubberBand.reset()
        QgsMapTool.deactivate(self)
        self.deactivated.emit()
