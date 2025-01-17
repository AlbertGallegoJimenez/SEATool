import arcpy
import pandas as pd
import numpy as np
import os
from tools.utils.shoreline_evolution import ShorelineEvolution
from tools.utils.generic_funs import create_new_fields

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
        # Get the parameters
        shoreFeatures = parameters[0].valueAsText
        transectsFeature = parameters[1].valueAsText
        transectsID = "transect_id"
        
        # Get the data from the Shoreline Intersection Points Feature Class
        cursor = arcpy.da.SearchCursor(shoreFeatures, [transectsID, "date", "distance_from_base"])
        # Create a DataFrame with the data
        df = pd.DataFrame(data=[row for row in cursor], columns=[transectsID, "date", "distance_from_base"])
        
        # For the multiple intersections, keep only the minimum distance from the base for each transect and date.
        if df[[transectsID, "date"]].duplicated(keep=False).sum() != 0: # If there are multiple intersections
            # Keep only the minimum distance from the base for each transect and date
            df = df.groupby(by=[transectsID, "date"], as_index=False).agg(
                {"distance_from_base": "min"}).sort_values([transectsID, "date"])
        else:
            # Sort the DataFrame by transect ID and date (to ensure the correct order of the data)
            df = df.sort_values([transectsID, "date"])

        # Perform the Linear Regression Analysis on each transect
        # Calculate the metrics of the Linear Regression Fit
        shore_metrics = pd.DataFrame({transectsID: np.arange(1, df[transectsID].max() + 1, 1)})
        # LRR: Linear Regression Rate and Confidence Intervals
        shore_metrics[["LRR", "LCI_low", "LCI_upp"]] = shore_metrics[transectsID].apply(
            lambda x: pd.Series(ShorelineEvolution(df=df, transect_id=x).LRR()))
        # R2: Coefficient of Determination
        shore_metrics["R2"] = shore_metrics[transectsID].apply(
            lambda x: ShorelineEvolution(df=df, transect_id=x).R2())
        # Pvalue: P-value of the Linear Regression Fit
        shore_metrics["Pvalue"] = shore_metrics[transectsID].apply(
            lambda x: ShorelineEvolution(df=df, transect_id=x).Pvalue())
        # RMSE: Root Mean Square Error
        shore_metrics["RMSE"] = shore_metrics[transectsID].apply(
            lambda x: ShorelineEvolution(df=df, transect_id=x).RMSE())
        # SCE: Shoreline Change Envelope
        shore_metrics["SCE"] = shore_metrics[transectsID].apply(
            lambda x: ShorelineEvolution(df=df, transect_id=x).SCE())
        # NSM: Net Shoreline Movement
        shore_metrics["NSM"] = shore_metrics[transectsID].apply(
            lambda x: ShorelineEvolution(df=df, transect_id=x).NSM())
        
        # Add the metrics to the Transects Feature Class
        metrics_fields = shore_metrics.columns[1::].tolist() # Exclude the transect ID
        # Create the new fields in the Transects Feature Class
        create_new_fields(transectsFeature, metrics_fields, ['DOUBLE'] * len(metrics_fields))

        # Update the Transects Feature Class with the metrics
        with arcpy.da.UpdateCursor(transectsFeature, ["transect_id"] + metrics_fields) as cursor:
            for i, _ in enumerate(cursor):
                # Check if the transect ID is in the DataFrame (to handle the case where a transect has no intersections)
                if cursor[0] in shore_metrics[transectsID].values:
                    # Update the row with the metrics
                    cursor.updateRow([cursor[0]] + shore_metrics.loc[i, metrics_fields].tolist())                   
                else:
                    # Update the row with NaN values
                    cursor.updateRow([cursor[0]] + [np.nan] * len(metrics_fields))

        # Export the output CSVs
        self._export_output_data(shoreFeatures, transectsID, shore_metrics)
        arcpy.AddMessage("The analysis has been successfully performed.\nPlease check the output data in the 'Output data' folder.")
        
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        
        """
        Define a generic symbology for the Transects Feature Class.
        The symbology will be based on the Linear Regression Rate (LRR) field.
        """
        # Get the parameters
        transectsFeature = parameters[1].valueAsText
        
        # Get the ArcGIS Project
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
        sym.renderer.breakCount = 7

        # Define upper bound values for each class break
        upperBoundValues = [-4, -2, -0.5, 0.5, 2, 4, 100]

        # Define labels for each class
        labels = ["MIN - -4.0", "-4.0 - -2.0", "-2.0 - -0.5", "-0.5 - 0.5", "0.5 - 2.0", "2.0 - 4.0", "4.0 - MAX"]

        # Define sizes for each class
        sizes = [6, 3, 1.5, 1, 1.5, 3, 6]

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

        # Exclude non-significant transects and apply unique symbology (grey dashed line)
        cim.renderer.useExclusionSymbol = True
        cim.renderer.exclusionClause = 'Pvalue > 0.05'
        cim.renderer.exclusionLabel = 'Non-significant transect'
        cim.renderer.exclusionSymbol.symbol.symbolLayers[0].color.values = [130, 130, 130, 100] # Grey color
        cim.renderer.exclusionSymbol.symbol.symbolLayers[0].width = 1.5
        cim.renderer.exclusionSymbol.symbol.symbolLayers[0].effects = [{
                    "type" : "CIMGeometricEffectDashes",
                    "dashTemplate" : [5, 5],
                    "lineDashEnding" : "NoConstraint",
                    "controlPointEnding" : "NoConstraint"
                  }]
        # Update the CIM
        transectsLayerObj.setDefinition(cim)
        
        return

    def _export_output_data(self, shoreFeatures, transectsID, shore_metrics):
        """
        Private method to export the output data.

        Parameters:
            shoreFeatures (str): Name of Shoreline Intersection Points Feature Class.
            transectsID (str): Name of ID field of Transects Feature Class.
            shore_metrics (pd.DataFrame): DataFrame where the metrics of the analysis are stored.

        Returns:
            None
        """
        # Extract the values of the feature class by arcpy cursor
        cursor = arcpy.da.SearchCursor(shoreFeatures, [transectsID, "date", "distance_from_base"])
        shoreFeatures_df = pd.DataFrame(data=[row for row in cursor], columns=[transectsID, "date", "distance_from_base"])

        # Set the directory where XLSX will be stored
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        out_dir = os.path.join(aprx.homeFolder, 'Output data')
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)
        
        # Export the shorelines intersections to a XLSX file
        shoreFeatures_df.to_excel(os.path.join(out_dir, 'shorelines_distances.xlsx'), index=False)

        # Export the metrics of the Linear Regression Fit to a XLSX file
        shore_metrics.to_excel(os.path.join(out_dir, 'analysis_metrics_transects.xlsx'), index=False)
