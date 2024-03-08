""" Functions that interact with the filesystem on disk. """
import pickle
import tempfile
import geopandas as gpd
from osgeo import gdal
import rasterio as rio
import numpy as np

def gdalTransform_to_rasterioAffine(gt):
    a = gt[0]
    b = gt[1]
    c = gt[2]
    d = gt[3]
    e = gt[4]
    f = gt[5]
    return rio.Affine(b, c, a, e, f, d)

def rasterio_write_raster_from_array(raster_array, raster_dict, output_path=None, description_list=None):
    if output_path is None:
        tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
        output_path = tempfile.mkstemp(dir=tfol, suffix='.tif')[1]

    if len(raster_array.shape) == 2:
        raster_array = np.expand_dims(raster_array, axis=0)

    # This will need to get dropped once the raster_dict methods are updated to rasterio
    if type(raster_dict['GeoTransform']) == list:
        transform = gdalTransform_to_rasterioAffine(raster_dict['GeoTransform'])
    else:
        transform = raster_dict['GeoTransform']

    new_dataset = rio.open(output_path, 'w', driver='Gtiff',
                           height=raster_array.shape[1], width=raster_array.shape[2],
                           count=raster_array.shape[0], dtype=raster_array.dtype,
                           crs=raster_dict['Projection'],
                           nodata=raster_dict['NoData'],
                           transform=transform)
    if description_list:
        for band, desc in enumerate(description_list, 1):
            new_dataset.set_band_description(band, desc)
    new_dataset.write(raster_array)
    new_dataset.close()
    return output_path

def gdalSave(prefix, array2write, bittype, geotransform, projection, nodataval, descs=()):
    tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
    tfile = tempfile.mkstemp(dir=tfol, suffix='.tif', prefix=prefix)
    if array2write.ndim == 2:
        sizeX, sizeY = array2write.shape[1], array2write.shape[0]
        gtr_ds = gdal.GetDriverByName("GTiff").Create(tfile[1], sizeX, sizeY, 1, bittype)
        gtr_ds.SetGeoTransform(geotransform)
        gtr_ds.SetProjection(projection)
        gtr_ds.GetRasterBand(1).WriteArray(array2write)
        gtr_ds.GetRasterBand(1).SetNoDataValue(nodataval)

    else:
        sizeX, sizeY, sizeZ = array2write.shape[2], array2write.shape[1], array2write.shape[0]
        # print(f"sizeX, sizeY, sizeZ = {sizeX}, {sizeY}, {sizeZ}")
        gtr_ds = gdal.GetDriverByName("GTiff").Create(tfile[1], sizeX, sizeY, sizeZ, bittype)
        gtr_ds.SetGeoTransform(geotransform)
        gtr_ds.SetProjection(projection)
        # print(descs)
        for b, desc in zip(range(0, sizeZ), descs):
            print(b)
            name = f"Probability type_id: {desc}"
            data2d = array2write[b, :, :]
            gtr_ds.GetRasterBand(b+1).WriteArray(data2d)
            gtr_ds.GetRasterBand(b+1).SetNoDataValue(255)
            gtr_ds.GetRasterBand(b+1).SetDescription(name)
    gtr_ds = None
    return tfile[1]


def gdalSave1(prefix, array2write, bittype, geotransform, projection, nodataval, descs=()):
    tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
    tfile = tempfile.mkstemp(dir=tfol, suffix='.tif', prefix=prefix)
    if array2write.ndim == 2:
        print('saving singleband 2d')
        sizeX, sizeY = array2write.shape[1], array2write.shape[0]
        gtr_ds = gdal.GetDriverByName("GTiff").Create(tfile[1], sizeX, sizeY, 1, bittype)
        gtr_ds.SetGeoTransform(geotransform)
        gtr_ds.SetProjection(projection)
        gtr_ds.GetRasterBand(1).WriteArray(array2write)
        gtr_ds.GetRasterBand(1).SetNoDataValue(nodataval)
    elif array2write.shape[0] == 1:
        print('saving singleband 3d')
        sizeX, sizeY, sizeZ = array2write.shape[2], array2write.shape[1], array2write.shape[0]
        gtr_ds = gdal.GetDriverByName("GTiff").Create(tfile[1], sizeX, sizeY, sizeZ, bittype)
        gtr_ds.SetGeoTransform(geotransform)
        gtr_ds.SetProjection(projection)
        data2d = array2write[0, :, :]
        gtr_ds.GetRasterBand(1).WriteArray(data2d)
        gtr_ds.GetRasterBand(1).SetNoDataValue(nodataval)
    else:
        print('saving multiband')
        sizeX, sizeY, sizeZ = array2write.shape[2], array2write.shape[1], array2write.shape[0]
        # print(f"sizeX, sizeY, sizeZ = {sizeX}, {sizeY}, {sizeZ}")
        gtr_ds = gdal.GetDriverByName("GTiff").Create(tfile[1], sizeX, sizeY, sizeZ, bittype)
        gtr_ds.SetGeoTransform(geotransform)
        gtr_ds.SetProjection(projection)
        # print(descs)
        for b, desc in zip(range(0, sizeZ), descs):
            print(b)
            name = f"Probability type_id: {desc}"
            data2d = array2write[b, :, :]
            gtr_ds.GetRasterBand(b+1).WriteArray(data2d)
            gtr_ds.GetRasterBand(b+1).SetNoDataValue(255)
            gtr_ds.GetRasterBand(b+1).SetDescription(name)
    gtr_ds = None
    return tfile[1]

def kosher(obj, path):
    outfile = open(path, 'wb')
    pickle.dump(obj, outfile)
    outfile.close()

def dill(pklpath):
    infile = open(pklpath, 'rb')
    obj = pickle.load(infile)
    infile.close()
    return obj


def path_mkdir(path):
    try:
        path.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print("Folder is already there")
    else:
        print("Folder was created")

def parse_vector_source(datastr):
    try:
        # This will be the case for geopackages, but not shapefile or geojson
        fp, layername = datastr.split('|')
        gdf = gpd.read_file(fp, layername=layername.split('=')[1])
    except ValueError:
        fp = datastr
        gdf = gpd.read_file(fp)
    return gdf