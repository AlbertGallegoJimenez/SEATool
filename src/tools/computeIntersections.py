import arcpy
import os
import shapely
from shapely.geometry import Point
from tools.utils.intersect_lines import IntersectLines
from tools.utils.generic_funs import get_geodatabase_path, create_new_fields


class ComputeIntersection(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2. Intersect Shorelines And Baseline With Transects"
        self.description = "Compute the intersection points for Shorelines and Baseline with Transects"
        self.canRunInBackground = False
        arcpy.env.overwriteOutput = True

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
            displayName="Name of Shorelines ID Field",
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
        # Define the parameters
        baseFeature = parameters[0].valueAsText
        shoreFeature = parameters[1].valueAsText
        shoreID = parameters[2].valueAsText
        transectsFeature = parameters[3].valueAsText
        transectsID = "transect_id"
        baseOutFeature = parameters[4].valueAsText
        shoreOutFeature = parameters[5].valueAsText

        #  == Convert ArcGIS geometry to Shapely geometry ==
        # Check if the baseline has multiple features
        field_names = [f.name for f in arcpy.ListFields(baseFeature)]
        baseHasMultipleFeatures = 'baseline_id' in field_names
        
        # Baseline - convert with or without ID depending on multiple features
        if baseHasMultipleFeatures:
            baseShapely = IntersectLines.line_arcgis2shapely(baseFeature, 'baseline_id')  # dict
            # Get mapping of transect_id to baseline_id
            transect_baseline_map = {}
            with arcpy.da.SearchCursor(transectsFeature, ['transect_id', 'baseline_id']) as cursor:
                for row in cursor:
                    transect_baseline_map[row[0]] = row[1]
        else:
            baseShapely = IntersectLines.line_arcgis2shapely(baseFeature, None)  # list
            transect_baseline_map = None
        
        # Shorelines
        shoreShapely = IntersectLines.line_arcgis2shapely(shoreFeature, shoreID)
        # Transects
        transectsShapely = IntersectLines.line_arcgis2shapely(transectsFeature, transectsID)

        # == Create two empty Feature Classes for the intersections (baseline and shorelines)
        # Get the spatial reference
        sr = arcpy.Describe(parameters[0].valueAsText).spatialReference
        
        #  == 1. Baseline Intersection Points ==
        # Get the intersection points
        basePoints = IntersectLines.intersect_baseline(
            transectsShapely, 
            baseShapely, 
            has_multiple_features=baseHasMultipleFeatures,
            transect_baseline_map=transect_baseline_map
        )
        
        # Check if the output feature class exists and delete it
        if arcpy.Exists(baseOutFeature):
            arcpy.Delete_management(baseOutFeature)
        # Get the gdb path and the output fc name
        gdb_path = get_geodatabase_path(baseOutFeature)
        baseOutFeature_name = os.path.basename(baseOutFeature)
        # Create the feature class
        arcpy.management.CreateFeatureclass(out_path=gdb_path,
                                            out_name=baseOutFeature_name,
                                            geometry_type="POINT",
                                            spatial_reference=sr)
        # Add the transect_id field
        arcpy.management.AddField(baseOutFeature, transectsID, 'SHORT')
        # Fill with the geometries (intersection points) and the transect_id
        with arcpy.da.InsertCursor(baseOutFeature, [transectsID, "SHAPE@"]) as cursor:
            for id, point in basePoints.items():
                # Validate that the intersection exists and has coordinates
                if point and not point.is_empty and hasattr(point, 'coords'):
                    coords_list = list(point.coords)
                    if len(coords_list) > 0:
                        # Create the arcgis point
                        arc_Point = arcpy.Point(coords_list[0][0], coords_list[0][1])
                        # Insert the row with the id and the point
                        cursor.insertRow([id, arc_Point])
                    else:
                        arcpy.AddWarning(f"Transect {id}: Empty coordinates in baseline intersection")
                else:
                    arcpy.AddWarning(f"Transect {id}: No baseline intersection found")

        #  == 2. Shoreline Intersection Points ==
        # Get the intersection points
        shorePoints = IntersectLines.intersect_shorelines(transectsShapely, shoreShapely) # dict
        
        # Check if the output feature class exists and delete it
        if arcpy.Exists(shoreOutFeature):
            arcpy.Delete_management(shoreOutFeature)
        # Get the output fc name
        shoreOutFeature_name = os.path.basename(shoreOutFeature)
        # Create the feature class
        arcpy.management.CreateFeatureclass(out_path=gdb_path,
                                            out_name=shoreOutFeature_name,
                                            geometry_type="POINT",
                                            spatial_reference=sr)
        # Add the transect_id, shore_id and the distance from baseline fields
        fields_to_add = [transectsID, shoreID, "distance_from_base"]
        data_type = ["SHORT", "SHORT", "DOUBLE"]
        create_new_fields(shoreOutFeature, fields_to_add, data_type)
        
        """
        Iterate over the shorePoints (dictionary). The keys are tuples with the ids of the transects and shorelines.
        If the value is a list, add the key as many times as the length of the list (to match the number of geometries with the number of ids).
        """
        # Fill with the geometries (intersection points) and the transect_id and shore_id
        with arcpy.da.InsertCursor(shoreOutFeature, [transectsID, shoreID, "SHAPE@"]) as cursor:
            for t_id_shore_id, point in shorePoints.items():
                if isinstance(point, list): # The intersection point is a list of points (MultiPoint)
                    for part in point:
                        # Validate that the point has coordinates
                        if part and not part.is_empty and hasattr(part, 'coords'):
                            coords_list = list(part.coords)
                            if len(coords_list) > 0:
                                # Create the arcgis point
                                arc_Point = arcpy.Point(coords_list[0][0], coords_list[0][1])
                                # Insert the row with the transect_id and shore_id and the point
                                cursor.insertRow([t_id_shore_id[0], t_id_shore_id[1], arc_Point])
                else:
                    # Validate that the point has coordinates
                    if point and not point.is_empty and hasattr(point, 'coords'):
                        coords_list = list(point.coords)
                        if len(coords_list) > 0:
                            # Create the arcgis point
                            arc_Point = arcpy.Point(coords_list[0][0], coords_list[0][1])
                            # Insert the row with the transect_id and shore_id and the point
                            cursor.insertRow([t_id_shore_id[0], t_id_shore_id[1], arc_Point])

        # Add the other fields of the Polyline Shorelines Feature Class
        # Get the fields to join
        fieldsToJoin = [field.name for field in arcpy.ListFields(shoreFeature)
                        if "object" not in field.name.lower()
                        and "shape" not in field.name.lower()
                        and field.name.lower() != shoreID]
        # Join the fields
        arcpy.management.JoinField(
            in_data=shoreOutFeature,
            in_field=shoreID,
            join_table=shoreFeature,
            join_field=shoreID,
            fields=fieldsToJoin,
            fm_option="NOT_USE_FM",
            field_mapping=None
        )

        # == Calculate distances from baseline to shoreline points ==
        # Read the geometries of the baseOutFeature (baseline intersection points)
        basePoints = IntersectLines.point_arcgis2shapely(baseOutFeature, transectsID)
        # Update the distance_from_base field from the shoreOutFeature
        with arcpy.da.UpdateCursor(shoreOutFeature, ["SHAPE@", transectsID, "distance_from_base"]) as cursor:
            for row in cursor:
                transect_id = row[1]
                # Check if this transect has a baseline intersection
                if transect_id in basePoints:
                    # Get the geometry of the point
                    shore_shapely_geom = Point([(geom.X, geom.Y) for geom in row[0]][0])
                    # Calculate the distance from the baseline
                    row[2] = basePoints[transect_id].distance(shore_shapely_geom)
                    # Update the row
                    cursor.updateRow(row)
                else:
                    # If no baseline intersection, set distance to None and log warning
                    arcpy.AddWarning(f"Transect {transect_id}: Cannot calculate distance - no baseline intersection found")
                    row[2] = None
                    cursor.updateRow(row)
        return


    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
