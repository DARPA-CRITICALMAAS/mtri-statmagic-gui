from qgis.gui import QgsMapTool, QgsMapToolEmitPoint, QgsRubberBand
from qgis.core import QgsWkbTypes, QgsPoint, QgsGeometry, QgsFeature, Qgis

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMessageBox

import logging
logger = logging.getLogger("statmagic_gui")

class PolygonMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        logger.debug('tool init')
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.msg = QMessageBox()
        self.rubberBand = QgsRubberBand(self.canvas, Qgis.GeometryType.Polygon)
        self.rubberBand.setColor(Qt.red)
        self.rubberBand.setFillColor(QColor(100, 200, 165, 140))
        self.rubberBand.setWidth(3)

        self.rubberBandPoints = QgsRubberBand(self.canvas, Qgis.GeometryType.Point)
        self.rubberBandPoints.setIcon(QgsRubberBand.ICON_CIRCLE)
        self.rubberBandPoints.setColor(QColor(255, 200, 150, 100))
        self.rubberBandPoints.setIconSize(10)

        self.isDrawing = False
        self.points = []
        self.reset()

    def reset(self):
        self.points.clear()
        self.isDrawing = False
        self.rubberBand.reset(Qgis.GeometryType.Polygon)
        self.rubberBandPoints.reset(Qgis.GeometryType.Point)

    def canvasReleaseEvent(self, e):
        # which the mouse button?
        if e.button() == Qt.LeftButton:
            logger.debug('clicked left')
            # left click
            # if it's the first left click, clear the rubberband
            if not self.isDrawing:
                self.reset()
                self.points = []
            # we are drawing now
            self.isDrawing = True
            point = self.toMapCoordinates(e.pos())
            # add a new point to the rubber band
            self.rubberBand.addPoint(point, True)  # True = display updates on the canvas
            self.points.append(QgsPoint(point))
            self.rubberBand.show()
            self.rubberBandPoints.addPoint(point, True)
            self.rubberBandPoints.show()

        if e.button() == Qt.RightButton:
            # right click, stop drawing
            self.isDrawing = False
            # emit a signal
            polygon = self.rubberBand.asGeometry()
            feat = QgsFeature()
            feat.setGeometry(polygon)
            self.rubberBand.setToGeometry(polygon)
            self.rubberBand.show()
            # layer = iface.activeLayer()
            # f = layer.getFeature(0)
            # prov1 = layer.dataProvider()
            # layer.startEditing()
            # prov1.addFeatures([feat])
            # feat.setAttributes(f.attributes())
            # layer.commitChanges()
            # layer.updateExtents()
            # iface.mapCanvas().refresh()

    def deactivate(self):
        self.rubberBand.reset()
        self.rubberBandPoints.reset()
        QgsMapTool.deactivate(self)
        self.deactivated.emit()

    def geometry(self):
        return self.rubberBand.asGeometry()

    def points(self):
        return self.points
