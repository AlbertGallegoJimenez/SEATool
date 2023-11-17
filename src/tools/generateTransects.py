import arcpy, os


class GenerateTransects(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1a. Generate Transects Along Baseline"
        self.description = "Generate transects along the baseline for further analysis based on these transects."

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

        params_suggestions = {parameters[1]: "100 Meters",
                              parameters[2]: "300 Meters",
                              parameters[3]: projectName + "_Transects"}

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
        arcpy.env.overwriteOutput = True

        inFeatures = parameters[0].valueAsText
        distanceValue = parameters[1].valueAsText
        lengthValue = parameters[2].valueAsText
        outFeatures = parameters[3].valueAsText

        arcpy.management.GenerateTransectsAlongLines(inFeatures,
                                                     outFeatures,
                                                     distanceValue + " Meters",
                                                     lengthValue + " Meters",
                                                     "NO_END_POINTS")

        arcpy.management.AddField(outFeatures, "transect_id", 'SHORT')
        arcpy.management.CalculateField(outFeatures, "transect_id", "!OBJECTID!")

        with arcpy.da.UpdateCursor(outFeatures, ["transect_id", "SHAPE@"]) as cursor:
            for row in cursor:
                if len(row[1]) > 1:
                    row[1] = arcpy.Polyline(arcpy.Array([(point.X, point.Y) for point in row[1][:2]]))
                    cursor.updateRow(row)
                else:
                    pass

        fieldList = [field.name for field in arcpy.ListFields(outFeatures)]
        if 'ORIG_FID' in fieldList:
            arcpy.management.DeleteField(outFeatures, 'ORIG_FID')

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.activeMap
        transectsFeature = aprxMap.listLayers(os.path.basename(parameters[0].valueAsText))[0]
        labelClass = transectsFeature.listLabelClasses()[0]
        labelClass.expression = "$feature.transect_id"
        transectsFeature.showLabels = True
        return
