from osgeo import gdal
import tempfile


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
        gtr_ds = gdal.GetDriverByName("GTiff").Create(tfile[1], sizeX, sizeY, sizeZ, bittype)
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

