import arcpy
from shapely.geometry import Point, LineString, MultiLineString


class IntersectLines():
    def __init__():
        """
        This class computes the intersection between both baseline and shorelines with transects.
        The output will be a dictionary with the transect ID as key and the intersection point (Shapely object) as value.
        The class also contains two methods to convert line and point ArcGIS features to Shapely objects.
        
        Parameters:
            feature: ArcGIS feature class
        """
    
    def line_arcgis2shapely(feature: str, id: str=None):
        """
        Converts an ArcGIS line feature to a Shapely LineString object.
        This method is used to convert the baseline and shoreline features to Shapely objects.
        
        Parameters:
            feature (str): ArcGIS line feature
            id (str): ID of the feature
        Returns:
            feature_lines (list or dict): Shapely LineString objects
        """
        if id: # If the feature has an ID, return a dictionary. Otherwise, return a list.
            # Define an empty dictionary to store the Shapely LineString objects
            feature_lines = {} 
            # Iterate over the features and convert them to Shapely LineString objects
            with arcpy.da.SearchCursor(feature, [id, "SHAPE@"]) as cursor:
                for row in cursor:
                    # Get the id of the row
                    row_id = row[0]
                    # Get the geometry (SHAPE@) of the row
                    geometry = row[1]
                    # Extract coordinates of geometry points
                    if len(geometry) == 1: # If the geometry is a single part
                        # Extract the coordinates of the points in the geometry
                        for part in geometry:
                            # Create a Shapely LineString object
                            feature_lines.update(
                                {row_id: LineString([(point.X, point.Y) for point in part])}
                            )
                    else: # If the geometry is multipart
                        # Define a list to store the lines of the geometry
                        lines = []
                        # Extract the coordinates of the points in the geometry
                        for part in geometry:
                            # Create a Shapely LineString object
                            lines.append(LineString([(point.X, point.Y) for point in part]))
                        # Create a Shapely MultiLineString object
                        feature_lines.update(
                            {row_id: MultiLineString(lines)}
                        )
        else: # If the feature does not have an ID
            # Define an empty list to store the Shapely LineString objects
            feature_lines = []
            # Iterate over the features and convert them to Shapely LineString objects
            with arcpy.da.SearchCursor(feature, ["SHAPE@"]) as cursor:
                for row in cursor:
                    # Get the geometry (SHAPE@) of the row
                    geometry = row[0]
                    # Extract coordinates of geometry points
                    if len(geometry) == 1: # If the geometry is a single part
                        for part in geometry:
                            # Create a Shapely LineString object
                            feature_lines.append(LineString([(point.X, point.Y) for point in part]))
                    else: # If the geometry is multipart
                        # Define a list to store the lines of the geometry
                        lines = []
                        # Extract the coordinates of the points in the geometry
                        for part in geometry:
                            # Create a Shapely LineString object
                            lines.append(LineString([(point.X, point.Y) for point in part]))
                        # Create a Shapely MultiLineString object
                        feature_lines.append(MultiLineString(lines))
                        
        return feature_lines

    def point_arcgis2shapely(feature: str, id: str=None):
        """
        Converts an ArcGIS point feature to a Shapely Point object.
        
        Parameters:
            feature (str): ArcGIS point feature
            id (str): ID of the feature
        Returns:
            feature_points (dict): Shapely Point objects
        """
        if id: # If the feature has an ID, return a dictionary. Otherwise, return a list.
            # Define an empty dictionary to store the Shapely Point objects
            feature_points = {}
            # Iterate over the features and convert them to Shapely Point objects
            with arcpy.da.SearchCursor(feature, [id, "SHAPE@"]) as cursor:
                for row in cursor:
                    # Get the id of the row
                    row_id = row[0]
                    # Get the geometry (SHAPE@) of the row
                    geometry = row[1]
                    # Create a Shapely point object
                    feature_points.update(
                        {row_id: Point([(geom.X, geom.Y) for geom in geometry][0])}
                    )
        else: # If the feature does not have an ID
            # Define an empty list to store the Shapely Point objects
            feature_points = []
            # Iterate over the features and convert them to Shapely Point objects
            with arcpy.da.SearchCursor(feature, ["SHAPE@"]) as cursor:
                for row in cursor:
                    # Get the geometry (SHAPE@) of the row
                    geometry = row[0]
                    # Create a Shapely point object
                    feature_points.append(Point([(geom.X, geom.Y) for geom in geometry][0])
                    )
        
        return feature_points
    
    def intersect_baseline(transects_feature, baseline_feature):
        """
        This method computes the intersection between the baseline and transects.
        The output is a dictionary with the transect ID as key and the intersection point as value.
        
        Parameters:
            transects_feature (dict): Shapely LineString objects
            baseline_feature (list): Shapely LineString object
            
        Returns:
            base_points (dict): Shapely Point objects
        """
        # Define an empty dictionary to store the intersection points
        base_points = {}
        # Iterate over the transects and compute the intersection with the baseline
        for id_transect, line_transect in transects_feature.items():
            # Compute the intersection between the transect and the baseline
            intersection = line_transect.intersection(baseline_feature[0])
            # Store the intersection point in the dictionary
            base_points.update({id_transect: intersection})

        return base_points
    
    def intersect_shorelines(transects_feature, shorelines_feature):
        """
        This method computes the intersection between the shorelines and transects.
        The output is a dictionary with the transect ID and shoreline ID as key and the intersection point as value.
        
        Parameters:
            transects_feature (dict): Shapely LineString objects
            shorelines_feature (dict): Shapely LineString objects
            
        Returns:
            shore_points (dict): Shapely Point objects
        """
        # Define an empty dictionary to store the intersection points
        shore_points = {}
        # Iterate over the transects and compute the intersection with the shorelines
        for id_transect, line_transect in transects_feature.items():
            # Iterate over the shorelines and compute the intersection with the transects
            for id_shore, line_shore in shorelines_feature.items():
                if isinstance(line_shore, MultiLineString): # If the shoreline is a MultiLineString
                    # Iterate over the parts of the MultiLineString
                    for part in list(line_shore.geoms):
                        # Compute the intersection between the transect and the shoreline part
                        intersection = line_transect.intersection(part)
                        if not intersection.is_empty: # If the intersection is not empty
                            # If the intersection is a MultiPoint, break it down into its components
                            if intersection.geom_type == 'MultiPoint':
                                # Store the intersection points in the dictionary
                                shore_points.update(
                                    {(id_transect, id_shore): list(intersection.geoms)}
                                )
                            else:
                                # Store the intersection point in the dictionary
                                shore_points.update(
                                    {(id_transect, id_shore): intersection}
                                )
                else: # If the shoreline is a LineString
                    # Compute the intersection between the transect and the shoreline
                    intersection = line_transect.intersection(line_shore)
                    if not intersection.is_empty: # If the intersection is not empty
                        # If the intersection is a MultiPoint, break it down into its components
                        if intersection.geom_type == 'MultiPoint':
                            # Store the intersection points in the dictionary
                            shore_points.update(
                                {(id_transect, id_shore): list(intersection.geoms)}
                            )
                        else:
                            # Store the intersection point in the dictionary
                            shore_points.update(
                                {(id_transect, id_shore): intersection}
                            )

        return shore_points