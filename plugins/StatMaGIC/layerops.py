""" Functions that handle raster/vector layers and depend on QGIS gui components. """

from pathlib import Path
from osgeo import gdal
import rasterio as rio
import pandas as pd
from rasterio.mask import mask
from rasterio.plot import reshape_as_image
from shapely.wkt import loads
import numpy as np
import geopandas as gpd
import tempfile


from statmagic_backend.utils import polytextreplace, loggingDecorator

from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, \
    QgsWkbTypes, QgsCoordinateTransformContext, QgsMapLayerFactory, \
    QgsDataSourceUri, QgsMapLayerType


def addGreyScaleLayer(rasterLayer, layerName, group):
    res = QgsRasterLayer(rasterLayer, layerName)
    QgsProject.instance().addMapLayer(res, False)
    group.addLayer(res)


def dataframeFromSampledPoints(gdf, raster_path):
    """
    Parameters
    ----------
    gdf
    raster_path

    Returns
    -------

    """
    """
    Create a dataframe from sampled points in a raster, aligning the coordinate reference systems if necessary.

    Args:
        gdf: geopandas.GeoDataFrame
            The geospatial data frame containing the points to be sampled.

        raster_path: str
            The file path to the raster from which the points will be sampled.

    Returns:
        pandas.DataFrame
            A dataframe containing the sampled points.
    """
    raster = rio.open(raster_path)
    raster_crs = raster.crs
    if gdf.crs != raster_crs:
        gdf.to_crs(raster_crs, inplace=True)
    nodata = raster.nodata
    bands = raster.descriptions
    coords = [(x, y) for x, y in zip(gdf.geometry.x, gdf.geometry.y)]  # list of gdf lat/longs
    samples = [x for x in raster.sample(coords, masked=True)]
    s = np.array(samples)
    # Drop rows with nodata value
    dat = s[~(s == nodata).any(1), :]
    # also with nan
    dat = dat[~np.isnan(dat).any(axis=1)]
    # Turn into dataframe for keeping
    df = pd.DataFrame(dat, columns=bands)

    # statement = (f"{dat.shape[0]} sample points collected. \n"
    #              f"{s.shape[0] - dat.shape[0]} "
    #              f"dropped from intersection with nodata values.")

    # return df, statement
    return df


def dataframFromSampledPolys(gdf, rasterpath):
    raster = rio.open(rasterpath)
    if gdf.crs != raster.crs:
        gdf.to_crs(raster.crs, inplace=True)
    column_names = raster.descriptions
    nodata = raster.nodata
    dflist = []
    for index, feature in gdf.iterrows():
        outdf = rasDF_fromPolyShape(rasterpath, feature, column_names, nodata)
        dflist.append(outdf)
    bigdf = pd.concat(dflist)
    return bigdf


def rasDF_fromPolyShape(rasterpath, feature, column_names, nodata):
    geom = [feature['geometry']]
    rdarr = mask(rio.open(rasterpath), shapes=geom, crop=True)[0]
    stack = reshape_as_image(rdarr)
    new_shape = (stack.shape[0] * stack.shape[1], stack.shape[2])
    predstack = stack.reshape(new_shape)
    tvs = predstack[~(predstack == nodata).all(1)]
    df = pd.DataFrame(data=tvs, columns=column_names)
    return df


def addVectorLayer(vector_path, name, group):
    vlayer = QgsVectorLayer(vector_path, name, "ogr")
    if not vlayer.isValid():
        print("Layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(vlayer, False)
        group.addLayer(vlayer)


def rasterBandDescAslist(rasterpath):
    descs = []
    RasterDataSet = gdal.Open(rasterpath)
    for rb in range(1, RasterDataSet.RasterCount+1, 1):
        descs.append(RasterDataSet.GetRasterBand(rb).GetDescription())
    return descs


@loggingDecorator
def add_macrostrat_vectortilemap_to_project():
    url = 'https://dev.macrostrat.org/tiles/carto/{z}/{x}/{y}'
    options = QgsMapLayerFactory.LayerOptions(
        QgsCoordinateTransformContext())
    ds = QgsDataSourceUri()
    ds.setParam("type", "xyz")
    ds.setParam("url", url)
    ds.setParam("zmax", "14")
    ds.setParam("zmin", "0")
    ds.setParam('http-header:referer', '')
    ml = QgsMapLayerFactory.createLayer(ds.encodedUri().data().decode(),
                                        'Macrostrat Carto',
                                        QgsMapLayerType.VectorTileLayer, options)
    ml.setProviderType('xyzvectortiles')

    thisdir = Path(__file__).parent
    ml.loadNamedStyle(str(thisdir / "macrostrat_style.qml"))
    # QgsProject.instance().addMapLayer(ml)
    return ml


def return_selected_macrostrat_features_as_qgsLayer():
    # Make sure the Macrostrat Layer is selected
    layer = QgsProject.instance().mapLayersByName('Macrostrat Carto')[0]
    feats = layer.selectedFeatures()
    # layer CRS
    crs = layer.crs()
    # The geometries (Might need to parse the Geometry Types (LineString, Polygon)
    geoms = [feat.geometry() for feat in feats]
    # And the attributes
    attrs = [feat.attributeMap() for feat in feats]
    # Separate the Lines from the Polygons
    lineIndices, polygonIndices = [], []
    for idx, geom in enumerate(geoms):
        geoType = QgsWkbTypes.displayString(geom.wkbType())
        if geoType == 'LineString':
            lineIndices.append(idx)
        elif geoType == 'Polygon' or geoType == 'MultiPolygon':
            polygonIndices.append(idx)
        else:
            pass
    if len(lineIndices) > 0 and len(polygonIndices) > 0:
        lines = make_qgsVectorLayer_from_indices(lineIndices, geoms, attrs, crs, "Faults")
        polys = make_qgsVectorLayer_from_indices(polygonIndices, geoms, attrs, crs, "Polygons")
        return [lines, polys]
    elif len(lineIndices) == 0 and len(polygonIndices) > 0:
        polys = make_qgsVectorLayer_from_indices(polygonIndices, geoms, attrs, crs, "Polygons")
        return [polys]
    elif len(lineIndices) > 0 and len(polygonIndices) == 0:
        lines = make_qgsVectorLayer_from_indices(lineIndices, geoms, attrs, crs, "Faults")
        return [lines]
    else:
        pass


def make_qgsVectorLayer_from_indices(indices, geoms, attrs, crs, name):
    import geopandas as gpd
    geo = [geoms[i] for i in indices]
    attr = [attrs[i] for i in indices]
    gdf = gpd.GeoDataFrame(data=attr, geometry=geo, crs=crs.toWkt())
    # Todo: Should this be projected to the project CRS?
    # Todo: shoudl this go to tempfile or the CMA proj dir
    tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
    tfile = tempfile.mkstemp(dir=tfol, suffix='.json', prefix='macrostrat_selection')
    output_file_path = tfile[1]
    gdf.to_file(output_file_path, driver="GeoJSON")
    return QgsVectorLayer(output_file_path, f"Selected Macrostrat {name}", "ogr")


def set_project_crs(QgsRef):
    QgsProject.instance().setCrs(QgsRef)


def apply_model_to_array(model, array, raster_dict):
    data_array = np.transpose(array, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
    twoDshape = (data_array.shape[0] * data_array.shape[1], data_array.shape[2])
    pred_data = data_array.reshape(twoDshape)
    bool_arr = np.all(pred_data == raster_dict['NoData'], axis=1)
    if np.count_nonzero(bool_arr == 1) < 1:
        print('not over no data values')
        scores = model.score_samples(pred_data)

    else:
        idxr = bool_arr.reshape(pred_data.shape[0])
        pstack = pred_data[idxr == 0, :]
        scrs = model.score_samples(pstack)

        scores = np.zeros_like(bool_arr, dtype='float32')
        scores[~bool_arr] = scrs
        scores[bool_arr] = 0

    preds = scores.reshape(raster_dict['sizeY'], raster_dict['sizeX'], 1)
    classout = np.transpose(preds, (0, 1, 2))[:, :, 0]

    return classout


def qgis_poly_to_gdf(poly, poly_crs, raster_crs):
    wkt = poly.asWkt()
    shapely_geom = loads(wkt)
    print(type(shapely_geom))
    if type(shapely_geom) == 'MultiPolygon':
        geom = list(shapely_geom.geoms[0])
    else:
        geom = [shapely_geom]
    print(geom)
    gdf = gpd.GeoDataFrame(geometry=geom, crs=poly_crs)
    print(gdf.head())
    gdf.to_crs(raster_crs, inplace=True)
    return gdf


def shape_raster_array_to_data_array(raster_array, raster_dict, return_mask=False):
    da = np.transpose(raster_array, (1, 2, 0))  # convert from bands, rows, columns to rows, cols, bands
    data2D_full = da.reshape((da.shape[0] * da.shape[1], da.shape[2]))
    if return_mask:
        nodata_mask = np.all(data2D_full == raster_dict['NoData'], axis=1)
        idxr = nodata_mask.reshape(data2D_full.shape[0])
        # Test which of these is correct and best
        # data_nd_removed = data2D_full[~idxr]
        data_nd_removed = data2D_full[idxr == 0, :]
        return data_nd_removed, nodata_mask
    else:
        data_nan = np.where(data2D_full == raster_dict['NoData'], np.nan, data2D_full)
        return data_nan


def shape_data_array_to_raster_array(data_array, raster_dict, mask_array=None, nodata=None):
    rsizeX, rsizeY = raster_dict['sizeX'], raster_dict['sizeY']
    if mask_array is not None:
        da = np.zeros_like(mask_array).astype(data_array.dtype)
        da[~mask_array] = data_array
        da[mask_array] = nodata
        rda = da.reshape(rsizeY, rsizeX, 1)
        raster_data = np.transpose(rda, (0, 1, 2))[:, :, 0]
        return raster_data

    else:

        rda = data_array.reshape(rsizeY, rsizeX, 1)
        raster_data = np.transpose(rda, (0, 1, 2))[:, :, 0]
        if nodata is not None:
            return np.where(raster_data == np.nan, nodata, raster_data).astype(data_array.dtype)
        else:
            return raster_data.astype(data_array.dtype)
