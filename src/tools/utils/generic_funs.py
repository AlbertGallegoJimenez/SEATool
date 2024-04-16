import arcpy
import os
from shapely.geometry import LineString, MultiLineString

"""
This file contains generic functions that are used in multiple scripts. The aim is to avoid code repetition.
"""

# Function to get the Geodatabase path
def get_geodatabase_path(input_fc):
    """
    This method splits the input table or feature class path and returns the Geodatabase path.
    Adapted from: https://stackoverflow.com/questions/29191633/arcpy-get-database-path-of-feature-class-in-feature-dataset
    
    Params:
        - input_fc: Path to the input feature class.
    
    Returns:
        - Path to the Geodatabase.
    """
    # Get the workspace of the input feature class
    workspace = os.path.dirname(input_fc)
    # Check if the workspace is a Geodatabase
    if [any(ext) for ext in ('.gdb', '.mdb', '.sde') if ext in os.path.splitext(workspace)]:
        return workspace
    else:
        return os.path.dirname(workspace)

# Function to automate the creation of new fields in a feature class
def create_new_fields(input_fc, fields_to_add, data_type):
    """
    This is method creates new fields in a given feature class.
    
    Params:
        - input_fc: Feature class where the fields will be added.
        - fields_to_add: List of fields to add.
        - data_type: List of date types of the fields to add.
    
    Returns:
        - None
    """
    # Check if the fields to add are in the feature class and if not, add them
    fields_list = [f.name for f in arcpy.ListFields(input_fc)]
    for i, field in enumerate(fields_to_add):
        if field not in fields_list:
            arcpy.management.AddField(in_table=input_fc,
                                      field_name=field,
                                      field_type=data_type[i])

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