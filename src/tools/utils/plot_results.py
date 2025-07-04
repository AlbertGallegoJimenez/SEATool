import arcpy
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import re
import contextily as cx
import cartopy.crs as ccrs
from tools.utils.generic_funs import line_arcgis2shapely
from matplotlib.patches import Patch
import matplotlib.patheffects as pe
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.cm import ScalarMappable
import matplotlib.lines as mlines
from matplotlib.gridspec import GridSpec

# Define the settings for the plots
plt.style.use('classic')
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['axes.prop_cycle'] = plt.cycler(color=['#5B9CFD', '#FECB31', '#bfbbd9', '#fa8174', '#81b1d2',
                                                    '#fdb462', '#b3de69', '#bc82bd', '#ccebc4', '#ffed6f'])
# Get the color palette
palette = plt.rcParams['axes.prop_cycle'].by_key()['color']

class PlottingUtils():
    def __init__(self, transects, shore_intersections):
        """
        Constructor method for initializing PlottingUtils class.

        Parameters:
            transects (arcpy.FeatureClass): Feature Class object for transects (Line geometries).
            shore_intersections (arcpy.FeatureClass): Feature Class object for shoreline intersections (Point geometries).
        """
        self.transects = transects

        # Set the directory where plots will be stored
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        self.out_dir = os.path.join(aprx.homeFolder, 'Plots results')
        if not os.path.exists(self.out_dir):
            os.mkdir(self.out_dir)

        # Convert Feature Classes to Pandas DataFrames
        self.transects_df = self._feature_class_to_dataframe(transects)
        self.shore_intersections_df = self._feature_class_to_dataframe(shore_intersections)
        self.shore_intersections_df['date'] = pd.to_datetime(self.shore_intersections_df['date'])

        # Create Shapely Object for transects geometries
        self.transects_shapely = line_arcgis2shapely(feature=transects, id='transect_id')
    

    def _feature_class_to_dataframe(self, feature_class):
        """
        Private method to convert an ArcGIS Feature Class to a Pandas DataFrame.

        Parameters:
            feature_class (arcpy.FeatureClass): Feature Class object.

        Returns:
            pd.DataFrame: Pandas DataFrame containing feature class data.
        """
        fields = [field.name for field in arcpy.ListFields(feature_class)]

        return pd.DataFrame([row for row in arcpy.da.SearchCursor(feature_class, fields)], columns=fields)
    

    def _get_UTM_projection(self):
        """
        Private method to get UTM projection from transects Feature Class.

        Returns:
            UTM_number (int): UTM number.
            southern_hemisphere (bool): Whether or not the Feature Class is in the southern hemisphere.
        """
        # CRS string (e.g. 'WGS_1984_UTM_Zone_19N')
        crs = arcpy.Describe(self.transects).SpatialReference.name

        # Regex codes to extract the UTM number and the hemisphere
        num_code = r'\b(\d+)[A-Za-z]?\b'
        hemisphere_code = r'\b\d+([A-Za-z])\b'

        UTM_number = int(re.findall(num_code, crs.split('_')[-1])[0])
        hemisphere_UTM = re.findall(hemisphere_code, crs.split('_')[-1])[0]

        if hemisphere_UTM == 'N':
            southern_hemisphere = False
        else:
            southern_hemisphere = True
        
        return UTM_number, southern_hemisphere
    

    def _set_map_configuration(self, metric):
        """
        Private method to set the map configuration for plotting LRR, SCE and NSM.
        That is, the colormap, the type of normalization scale and the type of colorbar according to the metric.

        Parameters:
            metric (string): Name of the feature to plot.

        Returns:
            cmap (matplotlib.colors.LinearSegmentedColormap): The colormap.
            norm (matplotlib.colors.TwoSlopeNorm or matplotlib.colors.Normalize): The type of the normalization.
            extend_cbar (string): The type of the colorbar according to cmap and norm.
        """

        metric_min, metric_max = self.transects_df[metric].describe()[['min', 'max']]

        if metric_min < 0 and metric_max > 0:
            cmap = plt.get_cmap('RdYlBu')
            norm = TwoSlopeNorm(vmin=metric_min, vcenter=0, vmax=metric_max)
            extend_cbar = 'both'
        elif metric_min < 0 and metric_max < 0:
            cmap = plt.get_cmap('Reds_r')
            norm = Normalize(vmin=metric_min, vmax=0)
            extend_cbar = 'min'
        elif metric_min > 0 and metric_max > 0:
            cmap = plt.get_cmap('Blues')
            norm = Normalize(vmin=0, vmax=metric_max)
            extend_cbar = 'max'
        
        return cmap, norm, extend_cbar
    
    def _set_xylim(self, list_shapely):
        """
        Private method to set the x and y limits for plotting LRR, SCE and NSM.

        Parameters:
            list_shapely (dict): Dictionary of transect_id (key) and transects geometry in Shapely format (value).

        Returns:
            x_lim (list): List with the starting and ending x limits.
            y_lim (list): List with the starting and ending y limits.
        """
        # Get a list with all longitudes and latitudes values for all vertices of each transect
        lons = [x for t in list_shapely.values() for x in t.xy[0]]
        lats = [y for t in list_shapely.values() for y in t.xy[1]]

        # Calculate the offset for each axis
        x_offset = abs(max(lons) - min(lons)) / 10
        y_offset = abs(max(lats) - min(lats)) / 10

        # Set the x and y limits       
        x_lim = [min(lons) - x_offset, max(lons) + x_offset]
        y_lim = [min(lats) - y_offset, max(lats) + y_offset]
        
        # Determine if the map is oriented horizontally or vertically for further adjustments
        if (x_lim[1] - x_lim[0]) > (y_lim[1] - y_lim[0]):
            self.orientation = 'horizontal'
        else:
            self.orientation = 'vertical'

        return x_lim, y_lim


     #  ===== FROM HERE, ALL THE FUNCTIONS TO CREATE THE PLOTS ARE DEFINED =====
  
    def plot_spatial_evolution(self):
        """Plot the distances between all shorelines and the baseline on each transect"""
        
        fig, ax = plt.subplots(figsize=(12, 5))

        # Plot all values as scatter
        ax.scatter(self.shore_intersections_df['transect_id'],
                   self.shore_intersections_df['distance_from_base'],
                   color='#5B9CFD', alpha=.1, lw=0, zorder=1)

        # Plot average width value for each transect
        ax.plot(self.shore_intersections_df['transect_id'].unique(),
                self.shore_intersections_df.groupby('transect_id')['distance_from_base'].mean(),
                label='avg', color='#FECB31', lw=2, zorder=2)
        
        # Plot mean +-std width value for each transect
        ax.fill_between(self.shore_intersections_df['transect_id'].unique(),
                        self.shore_intersections_df.groupby('transect_id')['distance_from_base'].mean()+\
                        1 * self.shore_intersections_df.groupby('transect_id')['distance_from_base'].std(),
                        self.shore_intersections_df.groupby('transect_id')['distance_from_base'].mean()-\
                        1 * self.shore_intersections_df.groupby('transect_id')['distance_from_base'].std(),
                        color='#5B9CFD', alpha=.5, lw=0, label='avg\u00B1std', zorder=0) #color='#bfbbd9'
        
        # Plot settings
        #ax.set_xticks((np.arange(0, max(self.shore_intersections_df['transect_id']) + 2, 2)).tolist())
        ax.set_xlabel('Transect ID')
        ax.set_ylabel('Distance from baseline (m)')
        ax.set_xlim([-1, max(self.shore_intersections_df['transect_id']) + 2])
        plt.text(-0.05, 0.9, 'Seaward', transform=plt.gca().transAxes, horizontalalignment='right', fontstyle='italic')
        plt.text(-0.05, .1, 'Landward', transform=plt.gca().transAxes, horizontalalignment='right', fontstyle='italic')
        plt.grid(linestyle='--', alpha=0.3)
        ax.legend()
        ax.set_title('Spatial shoreline evolution (%.f - %.f)' % (self.shore_intersections_df['date'].min().year,
                                                                  self.shore_intersections_df['date'].max().year))
        fig.savefig(os.path.join(self.out_dir, 'spatial_shoreline_evolution.png'), dpi=300, bbox_inches='tight')


    def plot_time_series(self, transects2plot):
        """
        Plot time series for selected transects.
        
        Parameters:
            transects2plot (list): List of transect IDs to plot
            
        Returns:
            None
        """
        fig = plt.figure(figsize=(10, 2 * len(transects2plot)))
        gs = GridSpec(len(transects2plot), 7, figure=fig)
        
        # Variable to hold reference to the first x-axis created
        first_x_axis = None

        for i, t in enumerate(transects2plot):
            ax = fig.add_subplot(gs[i, :-1])

            # Prepare the data to plot
            data_transect = self.shore_intersections_df.loc[self.shore_intersections_df['transect_id'] == t, :]
            data_transect.index = pd.to_datetime(data_transect['date'])
            data_transect = data_transect.sort_index()
            data_transect['Time'] = np.arange(len(data_transect.index))
            X = data_transect.index.map(pd.Timestamp.toordinal)  # features
            y = data_transect.loc[:, 'distance_from_base']  # target

            # Plot time series
            ax.scatter(X, y.values, label='shoreline positions', color=palette[0])
            sns.regplot(x=X, y=y, ci=95, scatter=False, label='linear regression fit',
                        line_kws={"color": palette[1]}, ax=ax)

            # Plot settings
            xticks = ax.get_xticks().tolist()
            xticks.pop(0)
            xticks.pop(-1)
            labels = [pd.Timestamp.fromordinal(int(label)).date().strftime("%Y") for label in xticks]
            ax.set_xticks(xticks)
            ax.set_xticklabels(labels)
            ax.set_ylabel('Distance from\nbaseline (m)')
            ax.locator_params(axis='y', nbins=4)
            ax.set_title('Transect ' + str(t))
            ax.grid(alpha=0.3)
            # Share the x-axis in the time series plot
            if first_x_axis is None:
                first_x_axis = ax
            else:
                try:
                    ax.get_shared_x_axes().join(first_x_axis, ax)
                except Exception as e:
                    pass

            # Plot LRR error plot
            ax2 = fig.add_subplot(gs[i, -1:])
            lrr = self.transects_df.loc[self.transects_df['transect_id']==t, 'LRR']
            lci = self.transects_df.loc[self.transects_df['transect_id']==t, ['LCI_low', 'LCI_upp']].to_numpy()[0]
            ax2.errorbar(0, lrr, yerr=([abs(lci[0] - lrr.values[0])], [lci[1] - lrr.values[0]]),
                        fmt='or', markersize=8, capsize=5)
            
            # Plot settings
            ax2.set_xticklabels([])
            ax2.locator_params(axis='y', nbins=4)
            ax2.locator_params(axis='x', nbins=1)
            ax2.grid(axis='y', alpha=0.3)
            ax2.grid(axis='x', alpha=0)
            
            if i == len(transects2plot) - 1:
                # Time series plot
                ax.legend(fontsize=8, loc='best')
                ax.set_xlabel('Date')
                xticks = ax.get_xticks()
                labels = [pd.Timestamp.fromordinal(int(label)).date().strftime("%m-%Y") for label in xticks]
                ax.set_xticks(xticks)
                ax.set_xticklabels(labels)
                
                # LRR error plot
                ax2.set_xlabel('LRR\u00B195%\n(m/year)')
                
            else:
                # Time series plot
                ax.set_xlabel('')
                ax.set_xticklabels([])
            
            plt.subplots_adjust(hspace=0.4, wspace=1)
        
        fig.savefig(os.path.join(self.out_dir, 'time_shoreline_evolution.png'), bbox_inches='tight', dpi=300)


    def plot_seasonality(self, transects2plot):
        """
        Boxplot by months for selected transects
        
        Parameters:
            transects2plot (list): List of transect IDs to plot
            
        Returns:
            None
        """
        shore_month = self.shore_intersections_df.copy()
        shore_month['month'] = shore_month['date'].dt.month

        fig, ax = plt.subplots(len(transects2plot), 1, figsize=(10, 4 * len(transects2plot)), sharex=True)

        for i, t in enumerate(transects2plot):
            # Grab the data
            data = shore_month.loc[shore_month['transect_id'] == t, ['month', 'distance_from_base']]
            # Check that all months are present in the data. If not, add one NaN value so the boxplot is created correctly.
            if len(data['month'].unique()) < 12:
                for m in range(1, 13):
                    if m not in data['month'].unique():
                        data = pd.concat([data, pd.DataFrame({'month': [m], 'distance_from_base': [np.nan]})])
            
            # Median values Line plot
            ax[i].plot(data.groupby('month')['distance_from_base'].median(),
                    color='#FECB31', marker='o', markeredgecolor=None, alpha=.7)
            
            # Box plot
            medianprops = dict(linestyle='-', linewidth=2, color='#FECB31')
            whiskerprops = dict(linestyle='-', color='#5B9CFD')
            data.boxplot(column='distance_from_base', by='month', ax=ax[i], medianprops=medianprops, whiskerprops=whiskerprops)
            
            # Plot settings
            ax[i].set_xlabel('')
            ax[i].set_ylabel('Distance from\nbaseline (m)')
            ax[i].locator_params(axis='y', nbins=5)
            ax[i].set_title('Transect ' + str(t))
            ax[i].grid(linestyle='--', alpha=0.3)
            ax[i].grid(axis='x', alpha=0)
            
            if i == len(transects2plot) - 1:
                ax[i].set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] * len(transects2plot))
                ax[i].set_xlabel('Months')
                
        fig.suptitle(None)
        plt.subplots_adjust(hspace=0.2)
        fig.savefig(os.path.join(self.out_dir, 'shoreline_evolution_seasonality.png'), dpi=300, bbox_inches='tight')


    def plot_map(self, metric):
        """
        Plot a map of the selected metric (LRR, SCE or NSM).
        
        Parameters:
            metric (string): Name of the feature to plot.
        
        Returns:
            None
        """
        # Set the cmap, norm and the type of cbar of the plot
        cmap, norm, extend_cbar = self._set_map_configuration(metric)
        
        # Set projection parameter
        UTM_number, southern_hemisphere = self._get_UTM_projection()
        proj = ccrs.UTM(UTM_number, southern_hemisphere=southern_hemisphere)
        
        # Set x, y limits for the plot
        x_lim, y_lim = self._set_xylim(self.transects_shapely)
        
        # Calculate optimal step for transect labels based on spatial distribution
        step = self._calculate_optimal_label_step(x_lim, y_lim)

        # Create a subplot with UTM projection
        fig, ax = plt.subplots(subplot_kw={'projection':proj})

        # Iterate through transects and plot lines
        for i, t in self.transects_shapely.items():
            
            if metric == 'LRR':
                # Check if Pvalue is less than 0.05 for significance
                if self.transects_df.loc[self.transects_df['transect_id'] == i, 'Pvalue'].values <= 0.05:
                    color = cmap(norm(self.transects_df.loc[self.transects_df['transect_id'] == i, metric]))
                    ls = '-'
                else:
                    color = 'gray'
                    ls = '--'
            else:
                color = cmap(norm(self.transects_df.loc[self.transects_df['transect_id'] == i, metric]))
                ls = '-'
            
            # Plot the transect line
            x, y = t.xy
            ax.plot(x, y,
                    color=color,
                    transform=proj,
                    lw=3,
                    ls=ls)
            
            # Add labels every 'step' transects
            if i % step == 0:
                x_cent, y_cent = t.centroid.xy
                ax.text(x_cent[0], y_cent[0], str(i), color='black', transform=proj, fontsize=6,
                        ha='center', va='center', path_effects=[pe.withStroke(linewidth=2, foreground='white')])

        # Create a legend entry for non-significant transects
        legend_entry = mlines.Line2D([], [], color='gray', lw=2, ls='--', label='Non-significant transect')

        # Customize gridlines, ticks, and appearance
        ax.gridlines(crs=proj, linewidth=1, color='black', alpha=0, linestyle="--")
        ax.set_xticks(ax.get_xticks(), crs=proj)
        ax.set_yticks(ax.get_yticks(), crs=proj)
        ax.grid(alpha=.3)

        # Add colorbar and set title
        if self.transects_df['Pvalue'].min() <= 0.05:
            # shrink to 0.5 the colorbar
            fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), extend=extend_cbar, ax=ax, shrink=0.5)
        if metric == 'LRR':
            ax.set_title('Linear Regression Rate, LRR (m/year)', y=1.05)
        elif metric == 'SCE':
            ax.set_title('Shoreline Change Envelope, SCE (m)', y=1.05)
        elif metric == 'NSM':
            ax.set_title('Net Shoreline Movement, NSM (m)', y=1.05)

        # Set limits, labels, legend, and save the figure
        try:
            cx.add_basemap(ax, crs=proj, source=cx.providers.Esri.WorldImagery, alpha=.7, attribution=False)
        except:
            arcpy.AddMessage("Basemap could not be added to the {}_transect.png map.".format(metric))
        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)
        ax.set_xlabel('Eastings (m)')
        ax.set_ylabel('Northings (m)')
        if metric == 'LRR':
            ax.legend(handles=[legend_entry], fontsize='small', loc='best')
        fig.savefig(os.path.join(self.out_dir, 'map_{0}_transects.png'.format(metric)), dpi=300, bbox_inches='tight')

    def plot_bar_chart(self, metric):
        """
        Plot a bar chart of the selected metric (LRR, SCE or NSM).
        
        Parameters:
            metric (string): Name of the feature to plot.
        
        Returns:
            None
        """
        # Set the cmap, norm and the type of cbar of the plot
        cmap, norm, _ = self._set_map_configuration(metric)
        
        fig, ax = plt.subplots(figsize=(10, 4))
        # Plot the bar chart
        ax.bar(self.transects_df['transect_id'], self.transects_df[metric],
               color=cmap(norm(self.transects_df[metric])),
               lw=0)
        # Change the color of the bars for non-significant transects
        if metric == 'LRR':
            for i, p in enumerate(ax.patches):
                if self.transects_df.loc[self.transects_df['transect_id'] == (i + 1), 'Pvalue'].values > 0.05:
                    p.set_color('gray')
        # Set title and labels
        if metric == 'LRR':
            # Check if there's any transect with Pvalue more than 0.05
            if self.transects_df['Pvalue'].max() > 0.05:
                # Create a legend entry for non-significant transects
                legend_entry = mlines.Line2D([], [], color='gray', lw=2, label='Non-significant transect')
                ax.legend(handles=[legend_entry], fontsize='small', loc='best')
            ax.set_title('Linear Regression Rate, LRR (m/year)', y=1.05)
            ax.set_ylabel('LRR (m/year)')
        elif metric == 'SCE':
            ax.set_title('Shoreline Change Envelope, SCE (m)', y=1.05)
            ax.set_ylabel('SCE (m)')
        elif metric == 'NSM':
            ax.set_title('Net Shoreline Movement, NSM (m)', y=1.05)
            ax.set_ylabel('NSM (m)')
        # Get the x-axis ticks
        xticks = ax.get_xticks().tolist()
        xticks.pop(-1)
        # Set the x-axis limits and ticks
        ax.set_xlim([-1, max(self.transects_df['transect_id']) + 2])
        ax.set_xticks(xticks)
        # Set the grid
        ax.grid(linestyle='--', alpha=0.3)
        # Set labels and save the figure
        ax.set_xlabel('Transect ID')
        # Save the figure
        fig.savefig(os.path.join(self.out_dir, 'bar_{0}_transects.png'.format(metric)), dpi=300, bbox_inches='tight')

    def plot_spatiotemporal_chart(self):
        """
        Plot a spatiotemporal chart (similar to a heatmap or Hövmoller plot).
        """
        # Calculate the difference in days between each date and the first date
        self.shore_intersections_df["days"] = (
            self.shore_intersections_df["date"] -
            self.shore_intersections_df["date"].min()
            ).dt.days
        
        # Create a pivot table with the distance_from_base values
        pivot_table = self.shore_intersections_df.pivot_table(
            index='transect_id',
            columns='days',
            values='distance_from_base'
            )
        
        # Calculate the difference of the distance_from_base values with the first date
        # Create a method to get the first position with a threshold of 95% of data
        def get_first_position(pivot_table, threshold=0.95):
            for i in range(pivot_table.shape[1]):
                if pivot_table.iloc[:, i].notna().sum().sum() / pivot_table.shape[0] > threshold:
                    return i
            return 0
        first_position = get_first_position(pivot_table, 0.95)
        # Print a message with the first date selected
        arcpy.AddMessage(f"First date selected for the spatiotemporal chart: {self.shore_intersections_df['date'].min() + pd.to_timedelta(first_position, unit='D')}")
        # Calculate the difference values with the first date
        first_distance = pivot_table.iloc[:, first_position]
        first_dist_diff = pivot_table.subtract(first_distance, axis=0)
        
        # Set the gradient values for the plot
        vmin, vmax = np.nanmin(first_dist_diff.values), np.nanmax(first_dist_diff.values)
        norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
        
        # Create the figure
        fig, ax = plt.subplots(figsize=(12, 5))
        # Plot a gray background for the gaps in the data
        ax.contourf(first_dist_diff.columns, first_dist_diff.index, first_dist_diff.isnull(),
                    levels=0, colors='gray', alpha=0.3)
        # Plot the first_dist_diff values
        ax.contourf(first_dist_diff.columns, first_dist_diff.index, first_dist_diff,
                    levels=8, cmap='RdYlBu',
                    norm=norm, extend='both')
        # Change the y-axis to start from the bottom
        ax.invert_yaxis()
        # Add 1 to the y-axis to match the transect_id
        yticks = plt.gca().get_yticks().tolist()
        yticks = [int(ytick) + 1 for ytick in yticks]
        # Add a colorbar
        plt.colorbar(ScalarMappable(norm=norm, cmap='RdYlBu'), ax=ax)
        # Substitute the days in the x-axis for the actual dates in year-month format
        xticks = ax.get_xticks().tolist()
        xticks.pop(-1)
        xticklabels = pd.to_datetime(self.shore_intersections_df['date'].min()) + pd.to_timedelta(xticks, unit='D')
        ax.set_xticks(xticks, xticklabels.strftime('%Y-%m'), rotation=0)
        # Add a legend for the gray values
        gray_patch = Patch(color='gray', alpha=0.3, label='No data')
        ax.legend(handles=[gray_patch], loc='upper right')
        # Set the grid
        ax.grid(linestyle='--', alpha=0.3)
        # Set the axis and title labels
        ax.set_xlabel('Date')
        ax.set_ylabel('Transect ID')
        ax.set_title('Shoreline position difference from the first date')
        # Save the figure
        fig.savefig(os.path.join(self.out_dir, 'spatiotemporal_shoreline_evolution.png'), dpi=300, bbox_inches='tight')

    def _calculate_optimal_label_step(self, x_lim, y_lim):
        """
        Private method to calculate the optimal step for transect labels based on 
        spatial distribution and map dimensions.

        Parameters:
            x_lim (list): List with the starting and ending x limits.
            y_lim (list): List with the starting and ending y limits.

        Returns:
            step (int): Optimal step size for displaying transect labels.
        """
        # Get transect centroids in order
        transect_ids = sorted(self.transects_shapely.keys())
        centroids = []
        
        for transect_id in transect_ids:
            t = self.transects_shapely[transect_id]
            x_cent, y_cent = t.centroid.xy
            centroids.append((x_cent[0], y_cent[0]))
        
        # Calculate distances between consecutive transect centroids
        if len(centroids) < 2:
            return 1  # Only one transect, show label
        
        distances = []
        for i in range(len(centroids) - 1):
            dist = np.sqrt((centroids[i+1][0] - centroids[i][0])**2 + 
                          (centroids[i+1][1] - centroids[i][1])**2)
            distances.append(dist)
        
        # Calculate average distance between consecutive transects
        avg_centroid_distance = np.mean(distances) if distances else 0
        
        # Estimate label size based on map dimensions
        map_width = x_lim[1] - x_lim[0]
        map_height = y_lim[1] - y_lim[0]
        min_map_dimension = min(map_width, map_height)
        
        # Estimate label size as 2% of the smaller map dimension
        estimated_label_size = min_map_dimension * 0.02
        
        # Add some padding to prevent label overlap
        min_safe_distance = estimated_label_size * 5
        
        # Calculate optimal step
        if avg_centroid_distance > 0 and avg_centroid_distance < min_safe_distance:
            step = max(1, int(np.ceil(min_safe_distance / avg_centroid_distance)))
        else:
            step = 1  # Labels won't overlap with current spacing
        
        # Apply reasonable bounds and fallback logic
        if step > 10:  # Maximum step to ensure some labels are shown
            step = max(1, len(self.transects_shapely) // 20)  # Show ~5% of transects
        
        # Ensure minimum of 1 and maximum reasonable step
        step = max(1, min(step, 10))
        
        return step