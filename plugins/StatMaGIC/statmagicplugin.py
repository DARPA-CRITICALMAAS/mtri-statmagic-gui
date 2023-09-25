from pathlib import Path
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
import time
import tempfile
import numpy as np
from osgeo import gdal
from pydevd import settrace

pass


def boundingBoxToOffsets(bbox, geot):
    col1 = int((bbox[0] - geot[0]) / geot[1])
    col2 = int((bbox[1] - geot[0]) / geot[1]) + 1
    row1 = int((bbox[3] - geot[3]) / geot[5])
    row2 = int((bbox[2] - geot[3]) / geot[5]) + 1
    return [row1, row2, col1, col2]

def geotFromOffsets(row_offset, col_offset, geot):
    new_geot = [geot[0] + (col_offset * geot[1]),
                geot[1],
                0.0,
                geot[3] + (row_offset * geot[5]),
                0.0,
                geot[5]]
    return new_geot


def gdalSave(prefix, array2write, bittype, geotransform, projection, descs=()):
    tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
    tfile = tempfile.mkstemp(dir=tfol, suffix='.tif', prefix=prefix)
    if array2write.ndim == 2:
        sizeX, sizeY = array2write.shape[1], array2write.shape[0]
        gtr_ds = gdal.GetDriverByName("GTiff").Create(tfile[1], sizeX, sizeY, 1, bittype)
        gtr_ds.SetGeoTransform(geotransform)
        gtr_ds.SetProjection(projection)
        gtr_ds.GetRasterBand(1).WriteArray(array2write)
        gtr_ds.GetRasterBand(1).SetNoDataValue(0)

    else:
        sizeX, sizeY, sizeZ = array2write.shape[2], array2write.shape[1], array2write.shape[0]
        print(f"sizeX, sizeY, sizeZ = {sizeX}, {sizeY}, {sizeZ}")
        gtr_ds = gdal.GetDriverByName("GTiff").Create("/home/ajmuelle/statmagic/test.tif", sizeX, sizeY, sizeZ, bittype)
        gtr_ds.SetGeoTransform(geotransform)
        gtr_ds.SetProjection(projection)
        print(descs)
        for b, desc in zip(range(0, sizeZ), descs):
            print(b)
            name = f"Probability type_id: {desc}"
            data2d = array2write[b, :, :]
            gtr_ds.GetRasterBand(b+1).WriteArray(data2d)
            gtr_ds.GetRasterBand(b+1).SetNoDataValue(255)
            gtr_ds.GetRasterBand(b+1).SetDescription(name)
    gtr_ds = None
    return tfile[1]



class StatMaGICPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

    def initGui(self):
        iconPath = Path(__file__).parent / "icon.png"
        icon = QIcon(str(iconPath))
        self.action = QAction(icon, 'StatMaGIC', self.iface.mainWindow())
        self.iface.addToolBarIcon(self.action)
        self.action.triggered.connect(self.run)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self):
        selectedLayer = self.iface.layerTreeView().selectedLayers()[0]
        r_ds = gdal.Open(selectedLayer.source())
        geot = r_ds.GetGeoTransform()
        cellres = geot[1]
        nodata = r_ds.GetRasterBand(1).GetNoDataValue()
        r_proj = r_ds.GetProjection()
        rsizeX, rsizeY = r_ds.RasterXSize, r_ds.RasterYSize

        bb = self.canvas.extent()
        bb.asWktCoordinates()
        bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]

        offsets = boundingBoxToOffsets(bbc, geot)
        new_geot = geotFromOffsets(offsets[0], offsets[2], geot)
        geot = new_geot

        sizeX = int(((bbc[2] - bbc[0]) / cellres) + 1)
        sizeY = int(((bbc[3] - bbc[1]) / cellres) + 1)

        dat = r_ds.ReadAsArray(offsets[2], offsets[0], sizeX, sizeY)

        mean = np.expand_dims(((dat[0, :, :] + dat[1, :, :] + dat[2, :, :]) / 3).astype("uint8"), axis=0)
        # grey = np.vstack([mean, mean, mean])

        # settrace(host='localhost', port=5678, stdoutToServer=True, stderrToServer=True)
        savedFilename = gdalSave("grey", mean, gdal.GDT_Byte, geot, r_proj)
        message = f"temp file saved to {savedFilename}"
        self.iface.messageBar().pushMessage(message)
        print(message)



        # print(selectedLayer)