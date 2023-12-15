import arcpy
import shapely
from tools.utils.intersect_lines import *


class ComputeIntersection(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2. Intersect Shorelines And Baseline With Transects"
        self.description = "Compute the intersection points for Shorelines and Baseline with Transects"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        baseline_param = arcpy.Parameter(
            displayName="Input Baseline Feature",
            name="base_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        baseline_param.filter.list = ['Polyline']

        shoreline_param = arcpy.Parameter(
            displayName="Input Shorelines Feature",
            name="shore_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        shoreline_param.filter.list = ['Polyline']

        shore_id_param = arcpy.Parameter(
            displayName="Name of ID Shoreline Field",
            name="id_shore",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        shore_id_param.parameterDependencies = [shoreline_param.name]

        transects_param = arcpy.Parameter(
            displayName="Input Transects Feature",
            name="transects_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        transects_param.filter.list = ['Polyline']

        baseline_points_param = arcpy.Parameter(
            displayName="Output Baseline Points",
            name="base_points",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Output")

        shoreline_points_param = arcpy.Parameter(
            displayName="Output Shoreline Points",
            name="shore_points",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Output")

        parameters = [baseline_param, shoreline_param, shore_id_param, transects_param, baseline_points_param, shoreline_points_param]

        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if not parameters[4].altered and parameters[0].value:
            parameters[4].value = parameters[0].valueAsText + "_Intersect"
        else:
            parameters[4].value

        if not parameters[5].altered and parameters[1].value:
            parameters[5].value = parameters[1].valueAsText + "_Intersect"
        else:
            parameters[5].value

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):

        """The source code of the tool."""
        arcpy.env.overwriteOutput = True

        baseFeature = parameters[0].valueAsText
        shoreFeature = parameters[1].valueAsText
        shoreID = parameters[2].valueAsText
        transectsFeature = parameters[3].valueAsText
        transectsID = "transect_id"
        baseOutFeature = parameters[4].valueAsText
        shoreOutFeature = parameters[5].valueAsText

        # Convert ArcGIS geometry to Shapely
        baseShapely = line_arcgis2shapely(baseFeature, None)
        shoreShapely = line_arcgis2shapely(shoreFeature, shoreID)
        transectsShapely = line_arcgis2shapely(transectsFeature, transectsID)

        # Convert two empty Feature Classes for the intersections (baseline and shorelines)
        sr = arcpy.Describe(parameters[0].valueAsText).spatialReference

        #  == 1. Baseline Intersection Points ==
        basePoints = intersect_baseline(transectsShapely, baseShapely)
        # Create an empty Feature Class with empty field
        if arcpy.Exists(baseOutFeature):
            arcpy.Delete_management(baseOutFeature)

        arcpy.management.CreateFeatureclass(out_name=baseOutFeature,
                                            geometry_type="POINT",
                                            spatial_reference=sr)
        arcpy.management.AddField(baseOutFeature, transectsID, 'SHORT')

        # Fill with geometries (intersection points)
        with arcpy.da.InsertCursor(baseOutFeature, ["SHAPE@"]) as cursor:
            for point in basePoints.values():
                cursor.insertRow([arcpy.Point(coord[0], coord[1]) for coord in point.coords])

        # Fill the id field
        i = 0
        with arcpy.da.UpdateCursor(baseOutFeature, [transectsID]) as cursor:
            for row in cursor:
                cursor.updateRow([list(basePoints.keys())[i]])
                i += 1

        #  == 2. Shoreline Intersection Points ==
        shorePoints = intersect_shorelines(transectsShapely, shoreShapely)
        # Create an empty Feature Class with empty fields
        if arcpy.Exists(shoreOutFeature):
            arcpy.Delete_management(shoreOutFeature)
        arcpy.management.CreateFeatureclass(out_name=shoreOutFeature,
                                            geometry_type="POINT",
                                            spatial_reference=sr)
        arcpy.management.AddField(shoreOutFeature, transectsID, 'SHORT')
        arcpy.management.AddField(shoreOutFeature, shoreID, 'SHORT')
        arcpy.management.AddField(shoreOutFeature, "distance_from_base", 'DOUBLE')

        # Fill with geometries (intersection points)
        with arcpy.da.InsertCursor(shoreOutFeature, ["SHAPE@"]) as cursor:
            for point in shorePoints.values():
                if type(point) == list:
                    for part in point:
                        cursor.insertRow([arcpy.Point(coord[0], coord[1]) for coord in part.coords])
                else:
                    cursor.insertRow([arcpy.Point(coord[0], coord[1]) for coord in point.coords])

        # Fill the id fields
        list_keys = []
        for key, value in shorePoints.items():
            if type(value) == list:
                for _ in range(len(value)):
                    list_keys.append((key[0], key[1]))
            else:
                list_keys.append((key[0], key[1]))

        i = 0
        with arcpy.da.UpdateCursor(shoreOutFeature, [transectsID, shoreID]) as cursor:
            for row in cursor:
                row[0], row[1] = list_keys[i][0], list_keys[i][1]
                cursor.updateRow(row)
                i += 1

        # Add the other fields of Shorelines Feature Class
        fieldsToJoin = [field.name for field in arcpy.ListFields(shoreFeature)
                        if "object" not in field.name.lower()
                        and "shape" not in field.name.lower()
                        and field.name.lower() != shoreID]

        arcpy.management.JoinField(
            in_data=shoreOutFeature,
            in_field=shoreID,
            join_table=shoreFeature,
            join_field=shoreID,
            fields=fieldsToJoin,
            fm_option="NOT_USE_FM",
            field_mapping=None
        )

        # Calculate Distances
        basePoints = point_arcgis2shapely(baseOutFeature, transectsID)

        with arcpy.da.UpdateCursor(shoreOutFeature, ["SHAPE@", transectsID, "distance_from_base"]) as cursor:
            for row in cursor:
                shapely_geom = Point([(geom.X, geom.Y) for geom in row[0]][0])
                row[2] = basePoints[row[1]].distance(shapely_geom)
                cursor.updateRow(row)
        return


    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
