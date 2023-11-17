import arcpy
from shapely.geometry import Point, LineString, MultiLineString


def line_arcgis2shapely(feature, id):
    if id:
        featureLines = {}
        with arcpy.da.SearchCursor(feature, [id, "SHAPE@"]) as cursor:
            for row in cursor:
                # Get the id of the row
                row_id = row[0]
                # Get the geometry (SHAPE@) of the row
                geometry = row[1]
                # Extract coordinates of geometry points
                if len(geometry) == 1:
                    for part in geometry:
                        featureLines.update(
                            {row_id: LineString([(point.X, point.Y) for point in part])}
                        )
                else:
                    lines = []
                    for part in geometry:
                        lines.append(LineString([(point.X, point.Y) for point in part]))
                    featureLines.update(
                        {row_id: MultiLineString(lines)}
                    )
    else:
        featureLines = []
        with arcpy.da.SearchCursor(feature, ["SHAPE@"]) as cursor:
            for row in cursor:
                # Get the geometry (SHAPE@) of the row
                geometry = row[0]
                # Extract coordinates of geometry points
                if len(geometry) == 1:
                    for part in geometry:
                        featureLines.append(LineString([(point.X, point.Y) for point in part]))
                else:
                    lines = []
                    for part in geometry:
                        lines.append(LineString([(point.X, point.Y) for point in part]))
                    featureLines.append(MultiLineString(lines))
    return featureLines


def intersect_baseline(transectsFeature, baselineFeature):
    basePoints = {}
    for id_transect, line_transect in transectsFeature.items():
        intersection = line_transect.intersection(baselineFeature[0])
        basePoints.update({id_transect: intersection})

    return basePoints


def intersect_shorelines(transectsFeature, shorelinesFeature):
    """
    :param transectFeature: dictionary with transect_id as its key and Shapely object as its value
    :param feature: dictionary with id (either baseline or shoreline) as its key and Shapely object as its value
    :return: dictionary with a tuple (transect_id, feature_id) as its key and Shapely object or list of Shapely object as its value
    """
    shorePoints = {}

    for id_transect, line_transect in transectsFeature.items():
        for id_shore, line_shore in shorelinesFeature.items():
            if isinstance(line_shore, MultiLineString):
                for part in list(line_shore.geoms):
                    intersection = line_transect.intersection(part)
                    if not intersection.is_empty:
                        if intersection.geom_type == 'MultiPoint':
                            # If the intersection is a MultiPoint, break it down into its components
                            shorePoints.update(
                                {(id_transect, id_shore): list(intersection.geoms)}
                            )
                        else:
                            shorePoints.update(
                                {(id_transect, id_shore): intersection}
                            )
            else:
                intersection = line_transect.intersection(line_shore)
                if not intersection.is_empty:
                    if intersection.geom_type == 'MultiPoint':
                        # If the intersection is a MultiPoint, break it down into its components
                        shorePoints.update(
                            {(id_transect, id_shore): list(intersection.geoms)}
                        )
                    else:
                        shorePoints.update(
                            {(id_transect, id_shore): intersection}
                        )

    return shorePoints

def point_arcgis2shapely(feature, id):
    if id:
        featurePoints = {}
        with arcpy.da.SearchCursor(feature, [id, "SHAPE@"]) as cursor:
            for row in cursor:
                # Get the id of the row
                row_id = row[0]
                # Get the geometry (SHAPE@) of the row
                geometry = row[1]
                # Extract coordinates of geometry points
                featurePoints.update(
                    {row_id: Point([(geom.X, geom.Y) for geom in geometry][0])}
                )
    return featurePoints
