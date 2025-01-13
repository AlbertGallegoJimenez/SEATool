import arcpy
from tools.utils.plot_results import PlottingUtils

class PlotResults(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "4. Plot The Analysis Results"
        self.description = "Plot some figures to see the analysis results."
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

        transects_ID_2plot_param = arcpy.Parameter(
            displayName="Input Transects ID To Plot",
            name="transects_ID_2plot",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        transects_ID_2plot_param.columns = [['GPLong', 'Transects ID']]

        parameters = [shoreline_param, transects_param, transects_ID_2plot_param]

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
        parameters[2].setWarningMessage(
            "Check significance before selecting transects (Pvalue < 0.05).")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Get the parameters
        shoreFeatures = parameters[0].valueAsText
        transectsFeature = parameters[1].valueAsText
        transectsID_2plot = parameters[2].value
        transectsID_2plot = [id[0] for id in transectsID_2plot] # As the parameter value is passed as a list of lists, instead of a list of integers

        # Check for errors in the transect IDs selected
        self._check_transects_id(transectsID_2plot, transectsFeature)

        # Initialize the class
        plotter = PlottingUtils(transects=transectsFeature,
                                shore_intersections=shoreFeatures)
        try:
            # Plot the spatial evolution
            plotter.plot_spatial_evolution()
        except Exception as e:
            arcpy.AddError(f"An error occurred while plotting the spatial evolution: {e}")
        
        try:
            # Plot the time series for the transects selected
            plotter.plot_time_series(transects2plot=transectsID_2plot)
        except Exception as e:
            arcpy.AddError(f"An error occurred while plotting the time series: {e}")

        # Plot the seasonality for the transects selected.
        try:
            # Set a minimum of 2 years of data to plot the seasonality.
            if plotter.shore_intersections_df['date'].dt.year.max() - plotter.shore_intersections_df['date'].dt.year.min() >= 2:
                plotter.plot_seasonality(transects2plot=transectsID_2plot)
        except Exception as e:
            arcpy.AddError(f"An error occurred while plotting the seasonality: {e}")

        for metric in ['LRR', 'SCE', 'NSM']:
            try:
                # Plot the map
                plotter.plot_map(metric)
            except Exception as e:
                arcpy.AddError(f"An error occurred while plotting the {metric} map: {e}")
            try:
                # Plot the bar chart
                plotter.plot_bar_chart(metric)
            except Exception as e:
                arcpy.AddError(f"An error occurred while plotting the {metric} bar chart: {e}")
        
        arcpy.AddMessage("The analysis results have been plotted successfully.\n Please, check the 'Plots results' folder.")

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
    
    def _check_transects_id(self, transectsID_2plot, transectsFeature):
        """
        This method checks the transects ID selected by the user.
        
        Parameters:
            - transectsID_2plot: List of the transects ID selected by the user.
            - transectsFeature: Path to the transects feature class.
            
        Returns:
            - None (Raises an exception if the IDs are not valid). 
        """
        # Check that all IDs are numerical. This code may be unnecessary since the parameter is defined as 'GPLong' and this means that ArcGIS will only accept numerical values.
        if not all(isinstance(id, (int, float)) for id in transectsID_2plot):
            arcpy.AddError('Invalid transect ID, check that all IDs are numeric.')
            raise Exception('Invalid transect ID, check that all IDs are numeric.')
        
        # Check for duplicates
        if len(transectsID_2plot) != len(set(transectsID_2plot)):
            arcpy.AddError('Some transects are repeated.')
            raise Exception('Some transects are repeated.')
        
        # Check if the user only has selected one transect
        if len(transectsID_2plot) == 1:
            arcpy.AddError('Please, select more than one transect to plot.')
            raise Exception('Please, select more than one transect to plot.')
        
        # Check for ID out of range
        list_transect_id = [row[0] for row in arcpy.da.SearchCursor(transectsFeature, ['transect_id'])]
        if set(transectsID_2plot) - set(list_transect_id):
            arcpy.AddError('Invalid transect ID, check that all IDs are within the valid range.')
            raise Exception('Invalid transect ID, check that all IDs are within the valid range.')
