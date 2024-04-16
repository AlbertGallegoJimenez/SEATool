import arcpy, os
import pandas as pd
from tools.utils.transect_processor import TransectProcessor, RotateFeatures


class CorrectTransects(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1b. Correct Transects"
        self.description = "Correct the transects (if necessary) by rotating the features"

    def getParameterInfo(self):
        """Define parameter definitions"""

        # Input Feature parameter
        in_features = arcpy.Parameter(
            displayName="Input Features",
            name="in_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        in_features.filter.list = ["Polyline"]

        # Deviation Standard factor
        corr_factor = arcpy.Parameter(
            displayName="Correction Factor",
            name="corr_factor",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")

        # Output Feature parameter
        out_features = arcpy.Parameter(
            displayName="Output Features",
            name="out_features",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output")

        out_features.parameterDependencies = [in_features.name]
        out_features.schema.clone = True

        parameters = [in_features, corr_factor, out_features]

        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if not parameters[1].altered:
            parameters[1].value = 15.0
        else:
            parameters[1].value

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        parameters[1].setWarningMessage(
            "The correction factor is the largest acceptable difference in orientation between consecutive transects.")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Define the parameters
        transectsFeature = parameters[0].valueAsText
        corrFactor = float(parameters[1].valueAsText)

        # Add Bearing attribute
        arcpy.management.CalculateGeometryAttributes(transectsFeature, "Bearing LINE_BEARING")
        cursor = arcpy.da.SearchCursor(transectsFeature, ["transect_id", "Bearing"])
        # Create a DataFrame with the transects and their bearings
        df = pd.DataFrame(data=[row for row in cursor], columns=["transect_id", "Bearing"])

        # === 0. Identify (if applicable) the inverted transects
        processor = TransectProcessor(df, corrFactor)
        processor.invert_angles() # Identify the transects that are totally inverted
        
        # Update the DataFrame
        df = processor.df # This dataframe contains the transects with the inverted angles
        # Make the changes in the feature class
        RotateFeatures(df, transectsFeature)

        # Recalculate the bearing with the transects inverted
        arcpy.management.CalculateGeometryAttributes(transectsFeature, "Bearing LINE_BEARING")
        cursor = arcpy.da.SearchCursor(transectsFeature, ["transect_id", "Bearing"])
        # Create a DataFrame with the transects and their (updated) bearings
        df = pd.DataFrame(data=[row for row in cursor], columns=["transect_id", "Bearing"])
        
        # === 1. Identify and correct the transects with the largest differences between their orientations
        # Create an instance of the TransectProcessor class
        processor = TransectProcessor(df, corrFactor)
        # Classify the transects with large differences, that is, the transects that need to be corrected
        processor.classify_transects()
        # Interpolate the angles of the transects that need to be corrected
        processor.interpolate_angles()
        
        # Update the DataFrame
        df = processor.df

        # Make the changes in the feature class
        RotateFeatures(df, transectsFeature)

        # Delete the fields used to rotate the features
        arcpy.DeleteField_management(transectsFeature, ['Bearing', 'Angle'])
        
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        # Update the labels of the transect feature
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap
        transectsFeature = aprxMap.listLayers(os.path.basename(parameters[0].valueAsText))[0]
        labelClass = transectsFeature.listLabelClasses()[0]
        labelClass.expression = "$feature.transect_id"
        transectsFeature.showLabels = True

        return
