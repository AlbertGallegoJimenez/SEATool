import arcpy
import pandas as pd
import numpy as np
from tools.utils.shoreline_evolution import ShorelineEvolution

class PerformAnalysis(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3. Perform The Analysis"
        self.description = "Perform the Linear Regression Analysis on each transect."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        shoreline_param = arcpy.Parameter(
            displayName="Input Shorelines Intersection Points Feature",
            name="shore_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        shoreline_param.filter.list = ["Point"]

        transects_param = arcpy.Parameter(
            displayName="Input Transects Feature",
            name="transects_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        transects_param.filter.list = ["Polyline"]

        parameters = [shoreline_param, transects_param]

        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        shoreFeatures = parameters[0].valueAsText
        transectsFeature = parameters[1].valueAsText
        transectsID = "transect_id"

        cursor = arcpy.da.SearchCursor(shoreFeatures, [transectsID, "date", "distance_from_base"])
        df = pd.DataFrame(data=[row for row in cursor], columns=[transectsID, "date", "distance_from_base"])

        if df[[transectsID, "date"]].duplicated(keep=False).sum() != 0:
            df = df.groupby(by=[transectsID, "date"], as_index=False).agg(
                {"distance_from_base": "min"}).sort_values([transectsID, "date"])
        else:
            df = df.sort_values([transectsID, "date"])

        shore_metrics = pd.DataFrame({transectsID: np.arange(1, df[transectsID].max() + 1, 1)})
        shore_metrics[["LRR", "LCI_low", "LCI_upp"]] = shore_metrics[transectsID].apply(
            lambda x: pd.Series(ShorelineEvolution(df=df, transect_id=x).LRR()))
        shore_metrics["R2"] = shore_metrics[transectsID].apply(
            lambda x: ShorelineEvolution(df=df, transect_id=x).R2())
        shore_metrics["Pvalue"] = shore_metrics[transectsID].apply(
            lambda x: ShorelineEvolution(df=df, transect_id=x).Pvalue())
        shore_metrics["RMSE"] = shore_metrics[transectsID].apply(
            lambda x: ShorelineEvolution(df=df, transect_id=x).RMSE())
        shore_metrics["SCE"] = shore_metrics[transectsID].apply(
            lambda x: ShorelineEvolution(df=df, transect_id=x).SCE())
        shore_metrics["NSM"] = shore_metrics[transectsID].apply(
            lambda x: ShorelineEvolution(df=df, transect_id=x).NSM())

        metrics_fields = shore_metrics.columns[1::].tolist()
        for field in metrics_fields:
            arcpy.management.AddField(transectsFeature, field, "DOUBLE")

        with arcpy.da.UpdateCursor(transectsFeature, metrics_fields) as cursor:
            for i, _ in enumerate(cursor):
                cursor.updateRow(shore_metrics.loc[i, metrics_fields].tolist())

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        transectsFeature = parameters[1].valueAsText

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap

        # Get the layer to symbolise from the map object
        transectsLayerObj = [layer for layer in aprxMap.listLayers() if layer.name == transectsFeature][0]

        # Get the current symbology settings of the layer
        sym = transectsLayerObj.symbology

        # Set the renderer to Graduated Colors
        sym.updateRenderer('GraduatedColorsRenderer')

        # Set the color ramp for the renderer
        sym.renderer.colorRamp = aprx.listColorRamps("Red-Yellow-Blue (Continuous)")[0]

        # Specify the field used for classification
        sym.renderer.classificationField = 'LRR'

        # Set the number of class breaks
        sym.renderer.breakCount = 6

        # Define upper bound values for each class break
        upperBoundValues = [-4, -2, 0, 2, 4, 50]

        # Define labels for each class
        labels = ["-50.0 - -4.0", "-4.0 - -2.0", "-2.0 - 0.0", "0.0 - 2.0", "2.0 - 4.0", "4.0 - 50.0"]

        # Define sizes for each class
        sizes = [6, 3, 1.5, 1.5, 3, 6]

        # Update values for each class
        for i, brk in enumerate(sym.renderer.classBreaks):
            brk.upperBound = upperBoundValues[i]  # Set upper bound value
            brk.symbol.size = sizes[i]  # Set symbol size
            brk.label = labels[i]  # Set label for the class

        # Apply the updated symbology settings to the layer
        transectsLayerObj.symbology = sym

        # Get the layer's CIM definition
        cim = transectsLayerObj.getDefinition('V3')

        # Set the label for the symbolised field
        cim.renderer.heading = 'LRR (m/year)'

        # Exclude non-significant transects and apply unique symbology
        cim.renderer.useExclusionSymbol = True
        cim.renderer.exclusionClause = 'Pvalue > 0.05'
        cim.renderer.exclusionLabel = 'Non-significant transect'
        cim.renderer.exclusionSymbol.symbol.symbolLayers[0].color.values = [130, 130, 130, 100]
        cim.renderer.exclusionSymbol.symbol.symbolLayers[0].width = 1.5
        
        # Update the CIM
        transectsLayerObj.setDefinition(cim)
        
        return