import arcpy
import os

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