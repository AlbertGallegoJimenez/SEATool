import arcpy, os


class GenerateTransects(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1a. Generate Transects Along Baseline"
        self.description = "Generate transects along the baseline for further analysis based on these transects."
        arcpy.env.overwriteOutput = True

    def getParameterInfo(self):
        """Define parameter definitions"""

        # Input Features parameter
        in_features = arcpy.Parameter(
            displayName="Input Features",
            name="in_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        in_features.filter.list = ["Polyline"]

        # Distance between transects parameter
        distance_parameter = arcpy.Parameter(
            displayName="Distance between transects",
            name="distance_param",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input")

        # Transects length parameter
        length_parameter = arcpy.Parameter(
            displayName="Length of the transects",
            name="transect_length_param",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input")

        # Derived Output Features parameter
        out_features = arcpy.Parameter(
            displayName="Output Features",
            name="out_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Output")

        parameters = [in_features, distance_parameter, length_parameter, out_features]

        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        projectName = os.path.splitext(os.path.basename(aprx.filePath))[0]
        # Set the default values for the distance and length parameters
        params_suggestions = {parameters[1]: "100 Meters",
                              parameters[2]: "300 Meters",
                              parameters[3]: projectName + "_Transects"}
        # Update the parameters
        for param in params_suggestions:
            if not param.altered:
                param.value = params_suggestions[param]
            else:
                param.value

        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Define the parameters
        inFeatures = parameters[0].valueAsText
        distanceValue = parameters[1].valueAsText
        lengthValue = parameters[2].valueAsText
        outFeatures = parameters[3].valueAsText
        
        # Check if the baseline feature class has multiple features. 
        # If so, generate an ID field for the baseline features and propagate the ID field to the transects features.
        # Get the number of features in the baseline feature class
        featureCount = int(arcpy.management.GetCount(inFeatures).getOutput(0))
        if featureCount > 1:
            # Add an ID field to the baseline feature class
            arcpy.management.AddField(inFeatures, "baseline_id", 'SHORT')
            # Calculate baseline_id with sequential numbers starting from 1
            with arcpy.da.UpdateCursor(inFeatures, ["baseline_id"]) as cursor:
                for i, row in enumerate(cursor, start=1):
                    row[0] = i
                    cursor.updateRow(row)

        # Generate transects along the baseline
        arcpy.management.GenerateTransectsAlongLines(inFeatures,
                                                     outFeatures,
                                                     distanceValue + " Meters",
                                                     lengthValue + " Meters",
                                                     "NO_END_POINTS")
        # Add a field to the transects feature
        arcpy.management.AddField(outFeatures, "transect_id", 'SHORT')
        arcpy.management.CalculateField(outFeatures, "transect_id", "!OBJECTID!")
        
        # If the baseline feature class has multiple features, join the transects features with the baseline features to get the baseline_id field in the transects features.
        if featureCount > 1:
            arcpy.management.JoinField(outFeatures, "ORIG_FID", inFeatures, "OBJECTID", ["baseline_id"])
        
        # If the transect has more than 2 vertices, keep only the first two.
        # I don't know the reason why the GenerateTransectsAlongLines tool creates transects with more than 2 vertices, but this is a workaround.
        with arcpy.da.UpdateCursor(outFeatures, ["transect_id", "SHAPE@"]) as cursor:
            for row in cursor:
                if len(row[1]) > 1: # If the transect has more than 2 vertices
                    # Keep only the first two vertices
                    row[1] = arcpy.Polyline(arcpy.Array([(point.X, point.Y) for point in row[1][:2]]))
                    # Update the row
                    cursor.updateRow(row)
                else:
                    pass
        # Delete the ORIG_FID field that is created by the GenerateTransectsAlongLines tool
        fieldList = [field.name for field in arcpy.ListFields(outFeatures)]
        if 'ORIG_FID' in fieldList:
            arcpy.management.DeleteField(outFeatures, 'ORIG_FID')

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
