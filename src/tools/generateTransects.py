import arcpy, os
from tools.utils.transect_processor import TransectGenerator


class GenerateTransects(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1. Generate Transects Along Baseline"
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

        # Sea side parameter
        sea_side = arcpy.Parameter(
            displayName="Sea side relative to baseline direction",
            name="sea_side",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        sea_side.filter.type = "ValueList"
        sea_side.filter.list = ["Right", "Left"]

        # Derived Output Features parameter
        out_features = arcpy.Parameter(
            displayName="Output Features",
            name="out_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Output")

        parameters = [in_features, distance_parameter, length_parameter, sea_side, out_features]

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
                              parameters[3]: "Left",
                              parameters[4]: projectName + "_Transects"}
        # Update the parameters
        for param in params_suggestions:
            if not param.altered:
                param.value = params_suggestions[param]
            else:
                param.value

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        parameters[3].setWarningMessage(
            "When following the baseline from start to end, on which side is the sea located?")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Define the parameters
        inFeatures = parameters[0].valueAsText
        distanceValue = parameters[1].valueAsText
        lengthValue = parameters[2].valueAsText
        seaSide = parameters[3].valueAsText
        outFeatures = parameters[4].valueAsText
        
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

        # Extract numeric values from the distance and length parameters
        distance_meters = float(distanceValue.split()[0])
        length_meters = float(lengthValue.split()[0])
        
        # Generate transects using the new TransectGenerator class
        arcpy.AddMessage("Generating transects with intelligent smoothing...")
        generator = TransectGenerator(
            baseline_fc=inFeatures,
            distance=distance_meters,
            length=length_meters,
            sea_side=seaSide,
            output_fc=outFeatures
        )
        generator.generate_transects()
        
        arcpy.AddMessage(f"Transects generated successfully extending towards the sea on the {seaSide.lower()} side.")
        
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
