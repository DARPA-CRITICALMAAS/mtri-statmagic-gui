from qgis.gui import QgsMapTool, QgsMapToolEmitPoint
from PyQt5.QtCore import pyqtSignal


class PointTool(QgsMapToolEmitPoint):
    canvasClicked = pyqtSignal('QgsPointXY')

    def __init__(self, canvas):
        super(QgsMapTool, self).__init__(canvas)

    def canvasReleaseEvent(self, event):
        point_canvas_crs = event.mapPoint()

        self.canvasClicked.emit(point_canvas_crs)



class pointTool(QgsMapToolEmitPoint):
    canvasClicked = pyqtSignal('QgsPointXY')
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.point = None

    def canvasPressEvent(self, e, QgsMapMouseEvent=None):
        self.point = self.toMapCoordinates(e.pos())
        self.canvasClicked.emit(self.point)

    def deactivate(self) -> None:
        QgsMapTool.deactivate(self)
        self.deactivated.emit()

    def get_point(self):
        return self.point


