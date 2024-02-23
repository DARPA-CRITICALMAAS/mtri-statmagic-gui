from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand
from qgis.core import QgsWkbTypes, QgsPoint, QgsGeometry, QgsFeature, Qgis
from PyQt5 import Qt
from PyQt5.QtGui import QColor

# Taken from
# https://gis.stackexchange.com/questions/422891/drawing-virtual-dotted-line-using-pyqgis
class SamplingPolygon(QgsMapToolEmitPoint):
    points = []

    def __init__(self, canvas):
        # call the parent constructor
        QgsMapToolEmitPoint.__init__(self, canvas)
        # store the passed canvas
        self.canvas = canvas
        # iface = self.parent.parent.iface

        # flag to know whether the tool is performing a drawing operation
        self.isDrawing = False
        # self.dlg = CurveToolDialog()
        # create and setup the rubber band to display the line
        self.rubberBand = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        color = QColor(78, 97, 114)
        color.setAlpha(190)
        self.rubberBand.setColor(color)
        self.rubberBand.setWidth(1)
        # self.dlg.setFocusPolicy(Qt.StrongFocus)

    def clear(self):
        self.rubberBand.reset(True)

    def delete(self):
        self.canvas.scene().removeItem(self.rubberBand)

    def canvasPressEvent(self, e):
        # which the mouse button?
        if e.button() == Qt.LeftButton:
            print('clicked left')
            # left click
            # if it's the first left click, clear the rubberband
            if not self.isDrawing:
                self.clear()
                self.points = []
            # we are drawing now
            self.isDrawing = True
            point = self.toMapCoordinates(e.pos())
            # add a new point to the rubber band
            self.rubberBand.addPoint(point, True)  # True = display updates on the canvas
            self.points.append(QgsPoint(point))
            # polygon = QgsGeometry.fromPolyline(self.points)
            polygon = QgsGeometry.fromQPolygonF(self.points)
            feat = QgsFeature()
            feat.setGeometry(polygon)
            self.rubberBand.setToGeometry(polygon)
            self.rubberBand.movePoint(point)
            self.rubberBand.show()
            # and finally show the rubber band
            self.rubberBand.show()

        if e.button() == Qt.RightButton:
            # right click, stop drawing
            self.isDrawing = False
            # emit a signal
            # polygon = QgsGeometry.fromPolyline(self.points)
            polygon = QgsGeometry.fromQPolygonF(self.points)
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
            self.dlg.open()

    def geometry(self):
        return self.rubberBand.asGeometry()