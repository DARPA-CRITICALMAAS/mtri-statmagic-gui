""" Functions that handle raster/vector layers and depend on QGIS gui components. """
import itertools
import tempfile
from pathlib import Path

import numpy as np
from osgeo import gdal, ogr, osr

from statmagic_backend.geo.transform import boundingBoxToOffsets, geotFromOffsets
from statmagic_backend.maths.sampling import randomSample
from statmagic_backend.utils import polytextreplace, loggingDecorator

from PyQt5.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, \
    QgsColorRampShader, QgsPalettedRasterRenderer, QgsField, QgsFields, QgsVectorFileWriter, \
    QgsWkbTypes, QgsCoordinateTransformContext, QgsCoordinateReferenceSystem, QgsMapLayerFactory, \
    QgsDataSourceUri, QgsMapLayerType

from .constants import returnColorMap, getRGBvals




def makeTempLayer(crs):
    tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
    tfile = tempfile.mkstemp(dir=tfol, suffix='.gpkg', prefix='Training_')
    schema = QgsFields()
    schema.append(QgsField('type_id', QVariant.Int))
    schema.append(QgsField('type_Desc', QVariant.String))
    scrs = QgsCoordinateReferenceSystem(crs)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.fileEncoding = 'cp1251'
    fw = QgsVectorFileWriter.create(
        fileName=tfile[1],
        fields=schema,
        geometryType=QgsWkbTypes.Polygon,
        srs=scrs,
        transformContext=QgsCoordinateTransformContext(),
        options=options)
    del fw
    lyr = QgsVectorLayer(tfile[1], 'Training_Polys', 'ogr')
    QgsProject.instance().addMapLayer(lyr)


def addLayerSymbol(rasterLayer, layerName, classID, colorProfile):
    clrmap = returnColorMap(colorProfile)
    res = QgsRasterLayer(rasterLayer, layerName)
    QgsProject.instance().addMapLayer(res)
    red, green, blue = getRGBvals(classID, clrmap)
    pcolor = []
    pcolor.append(QgsColorRampShader.ColorRampItem(int(classID), QColor.fromRgb(red, green, blue), str(classID)))
    renderer = QgsPalettedRasterRenderer(res.dataProvider(), 1,
                                         QgsPalettedRasterRenderer.colorTableToClassData(pcolor))
    res.setRenderer(renderer)
    res.triggerRepaint()


def addRFconfLayer(rasterLayer, layerName, group):
    res = QgsRasterLayer(rasterLayer, layerName)
    QgsProject.instance().addMapLayer(res, False)
    group.addLayer(res)


def addLayerSymbolGroup(rasterLayer, layerName, classID, group, colorProfile):
    clrmap = returnColorMap(colorProfile)
    res = QgsRasterLayer(rasterLayer, layerName)
    QgsProject.instance().addMapLayer(res, False)
    group.addLayer(res)
    red, green, blue = getRGBvals(classID, clrmap)
    pcolor = []
    pcolor.append(QgsColorRampShader.ColorRampItem(int(classID), QColor.fromRgb(red, green, blue), str(classID)))
    renderer = QgsPalettedRasterRenderer(res.dataProvider(), 1,
                                         QgsPalettedRasterRenderer.colorTableToClassData(pcolor))
    res.setRenderer(renderer)
    res.triggerRepaint()


def addLayerSymbolMutliClass(rasterLayer, layerName, uniqueValList, colorProfile):
    clrmap = returnColorMap(colorProfile)
    res = QgsRasterLayer(rasterLayer, layerName)
    QgsProject.instance().addMapLayer(res)
    pcolor = []
    for classID in uniqueValList:
        red, green, blue = getRGBvals(classID, clrmap)
        pcolor.append(QgsColorRampShader.ColorRampItem(int(classID), QColor.fromRgb(red, green, blue), str(classID)))
    renderer = QgsPalettedRasterRenderer(res.dataProvider(), 1,
                                         QgsPalettedRasterRenderer.colorTableToClassData(pcolor))
    res.setRenderer(renderer)
    res.triggerRepaint()


def addLayerSymbolMutliClassGroup(rasterLayer, layerName, group, uniqueValList, colorProfile):
    clrmap = returnColorMap(colorProfile)
    res = QgsRasterLayer(rasterLayer, layerName)
    QgsProject.instance().addMapLayer(res, False)
    group.addLayer(res)
    pcolor = []
    for classID in uniqueValList:
        red, green, blue = getRGBvals(classID, clrmap)
        pcolor.append(QgsColorRampShader.ColorRampItem(int(classID), QColor.fromRgb(red, green, blue), str(classID)))
    renderer = QgsPalettedRasterRenderer(res.dataProvider(), 1,
                                         QgsPalettedRasterRenderer.colorTableToClassData(pcolor))
    res.setRenderer(renderer)
    res.triggerRepaint()


def bandSelToList(stats_table):
    qTable = stats_table
    tabLen = qTable.rowCount()
    bandlist = []
    for i in range(tabLen):
        entry = int(qTable.item(i, 1).text())
        if entry == 1:
            bandlist.append(i+1)
    return bandlist


def bands2indices(bandlist):
    idxs = [b - 1 for b in bandlist]
    return np.array(idxs)


def ExtractRasterValuesFromSelectedFeature(SelectedRaster, SelectedLayer, Feature):
    r_ds = gdal.Open(SelectedRaster.source())
    geot = r_ds.GetGeoTransform()
    cellres = geot[1]
    r_proj = r_ds.GetProjection()

    vl = QgsVectorLayer('Polygon?crs=%s' % SelectedLayer.crs().authid(), "temp",
                        "memory")  # Create a temp Polygon Layer
    pr = vl.dataProvider()
    pr.addFeature(Feature)
    vl.updateExtents()

    bb = Feature.geometry().boundingBox()  # xMin: float, yMin: float = 0, xMax: float = 0, yMax: float = 0
    bbc = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]

    offsets = boundingBoxToOffsets(bbc, geot)
    new_geot = geotFromOffsets(offsets[0], offsets[2], geot)

    sizeX = int(((bbc[2] - bbc[0]) / cellres) + 1)
    sizeY = int(((bbc[3] - bbc[1]) / cellres) + 1)

    mem_driver_gdal = gdal.GetDriverByName("MEM")
    tr_ds = mem_driver_gdal.Create("", sizeX, sizeY, 1, gdal.GDT_Byte)

    tr_ds.SetGeoTransform(new_geot)
    tr_ds.SetProjection(r_proj)
    vals = np.zeros((sizeY, sizeX))
    tr_ds.GetRasterBand(1).WriteArray(vals)

    mem_driver = ogr.GetDriverByName("Memory")
    shp_name = "temp"
    tp_ds = mem_driver.CreateDataSource(shp_name)

    prj = r_ds.GetProjection()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(prj)
    tp_lyr = tp_ds.CreateLayer('polygons', srs, ogr.wkbPolygon)

    featureDefn = tp_lyr.GetLayerDefn()
    feature = ogr.Feature(featureDefn)
    poly_text = Feature.geometry().asWkt()  # This is the geometry of the selected feature
    # Here need to change the MultiPolygonZ to POLYGON and remove 1 set of parentehes
    # print(poly_text)
    poly_text = polytextreplace(poly_text)

    polygeo = ogr.CreateGeometryFromWkt(poly_text)
    feature.SetGeometry(polygeo)
    tp_lyr.CreateFeature(feature)
    # feature = None

    gdal.RasterizeLayer(tr_ds, [1], tp_lyr, burn_values=[1])

    msk = tr_ds.ReadAsArray()
    dat = r_ds.ReadAsArray(offsets[2], offsets[0], sizeX, sizeY)[:, msk == 1]
    return dat


def getTrainingDataFromFeatures(selRas, selLayer, withSelected=False, samplingRate=None, maxPerPoly=None):
    trainingList = []
    if withSelected is True:
        sel = selLayer.selectedFeatures()
    else:
        sel = selLayer.getFeatures()
    for feat in sel:
        classLabel = feat['type_id']
        plydat = ExtractRasterValuesFromSelectedFeature(selRas, selLayer, feat)
        plydatT = plydat.T
        cv = np.full((plydatT.shape[0], 1), classLabel)
        ds = np.hstack([cv, plydatT])
        if samplingRate is not None:
            ds = randomSample(ds, samplingRate)[0]
        if maxPerPoly is not None:
            if ds.shape[0] > maxPerPoly:
                ds = ds[np.random.choice(ds.shape[0], maxPerPoly, replace=False)]
        trainingList.append(ds)
    cds = np.vstack(trainingList)
    return cds


def addVectorLayer(vector_path, name, group):
    vlayer = QgsVectorLayer(vector_path, name, "ogr")
    if not vlayer.isValid():
        print("Layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(vlayer, False)
        group.addLayer(vlayer)


def doClassIDfield(layer):
    if layer.dataProvider().fieldNameIndex("Class_ID") == -1:
        myField = QgsField('Class_ID', QVariant.Int)
        layer.dataProvider().addAttributes([myField])
        layer.updateFields()

    request = QgsFeatureRequest()

    # set order by field
    clause = QgsFeatureRequest.OrderByClause('type_id', ascending=True)
    orderby = QgsFeatureRequest.OrderBy([clause])
    request.setOrderBy(orderby)

    layer.startEditing()

    features = layer.getFeatures(request)
    feat1 = next(features)
    cid = feat1[layer.fields().indexFromName('type_id')]
    classNum = 1
    features = layer.getFeatures(request)
    column_ID = layer.dataProvider().fieldNameIndex("Class_ID")
    for index, feat in enumerate(features):
        classid = feat['type_id']
        if index != 0:
            if cid != classid:
                classNum = 1
            else:
                classNum += 1
            cid = classid
        else:
            pass
        layer.changeAttributeValue(feat.id(), column_ID, classNum)
    layer.commitChanges()


def createClassCoverageList(uniqvals, matches):
    toCompareClassCoverList = []  # This
    withinClassCoverList = []  # Once populated each element can be saved out and added into a new group folder
    for valueOfClass, listofArrayMatchesFromClass in zip(uniqvals, matches):
        outsum = sum([np.where(x > 0, 1, 0) for x in listofArrayMatchesFromClass])  # This gives # of overlap from class
        # inClassAdditiveValue = valueOfClass * 10
        # inClassCover = np.where(outsum > 0, outsum + inClassAdditiveValue, 0)
        layerName = 'Class_' + str(valueOfClass) + '_Matches'
        # withinClassCoverList.append([inClassCover, layerName, valueOfClass])
        withinClassCoverList.append([outsum, layerName, valueOfClass])
        ClassCover = np.where(outsum > 0, valueOfClass, 0)
        toCompareClassCoverList.append(ClassCover)
    return toCompareClassCoverList, withinClassCoverList


def createCrossClassList(toCompareClassCoverList):
    iterable = itertools.combinations(toCompareClassCoverList, 2)
    crosslist = []
    for A, B in iterable:
        valA = np.unique(A)[1]
        valB = np.unique(B)[1]
        print(valA, valB)
        hundoA = A * 100
        expected_val = (100 * valA) + valB
        print(f'expected value = {expected_val}')
        A_B_mix = hundoA + B
        A_B = np.where(A_B_mix == expected_val, expected_val, 0)
        if len(np.unique(A_B)) == 1:
            print('no overlap. skipping')
            continue
        print(f'array values are {np.unique(A_B)}')
        layerName = 'Classes_' + str(valA) + '_&_' + str(valB)
        print(layerName)
        savelist = [A_B, layerName, expected_val]
        crosslist.append(savelist)
    return crosslist


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
    return QgsVectorLayer(gdf.to_json(), f"Selected Macrostrat {name}", "ogr")

def set_project_crs(QgsRef):
    QgsProject.instance().setCrs(QgsRef)

