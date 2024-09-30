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
            cmap = plt.get_cmap('RdBu')
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
        # Plot the distances between all shorelines and the baseline on each transect
        
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
        ax.set_xlabel('Transect id')
        ax.set_ylabel('Distance from baseline (m)')
        ax.set_xlim([-1, max(self.shore_intersections_df['transect_id']) + 2])
        plt.text(-0.05, 0.9, 'Seaward', transform=plt.gca().transAxes, horizontalalignment='right', fontstyle='italic')
        plt.text(-0.05, .1, 'Landward', transform=plt.gca().transAxes, horizontalalignment='right', fontstyle='italic')
        plt.grid(linestyle='--', alpha=0.3)
        ax.legend()
        ax.set_title('Spatial shoreline evolution (%.f - %.f)' % (self.shore_intersections_df['date'].min().year,
                                                                  self.shore_intersections_df['date'].max().year))
        fig.savefig(os.path.join(self.out_dir, 'Spatial shoreline evolution.png'), dpi=300, bbox_inches='tight')


    def plot_time_series(self, transects2plot):
        # Plot time series for selected transects

        fig = plt.figure(figsize=(12, 2 * len(transects2plot)))
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
            ax.plot(X, y.values, linestyle='-', marker='o', markersize=2, label='shoreline positions')
            sns.regplot(x=X, y=y, ci=95, scatter=False, label='linear regression fit', ax=ax)

            # Plot settings
            x_offset = abs(max(X) - min(X)) / 15
            ax.set_xlim([min(X) - x_offset, max(X) + x_offset])
            ax.set_ylabel('Distance from\nbaseline (m)')
            ax.locator_params(axis='y', nbins=4)
            ax.set_title('Transect ' + str(t))
            ax.grid(alpha=0.3)
            # Share the x-axis in the time series plot
            if first_x_axis is None:
                first_x_axis = ax
            else:
                ax.get_shared_x_axes().join(first_x_axis, ax)

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
        
        fig.savefig(os.path.join(self.out_dir, 'Time shoreline evolution.png'), bbox_inches='tight', dpi=300)


    def plot_seasonality(self, transects2plot):
        # Boxplot by months for selected transects

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
        fig.savefig(os.path.join(self.out_dir, 'Shoreline evolution seasonality.png'), dpi=300, bbox_inches='tight')


    def plot_map(self, metric):
        # Plot a map of the selected metric (LRR, SCE or NSM)

        # Set the cmap, norm and the type of cbar of the plot
        cmap, norm, extend_cbar = self._set_map_configuration(metric)
        
        # Set projection parameter
        UTM_number, southern_hemisphere = self._get_UTM_projection()
        proj = ccrs.UTM(UTM_number, southern_hemisphere=southern_hemisphere)
        
        # Set x, y limits for the plot
        x_lim, y_lim = self._set_xylim(self.transects_shapely)
        
        # Set every how many transects to display the labels (transect ID)
        if len(self.transects_shapely) < 10:
            step = 1
        elif len(self.transects_shapely) < 50:
            step = 2
        else:
            step = 5

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
                ax.text(x_cent[0], y_cent[0], str(i), color='black', transform=proj, fontsize='x-small',
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
            cx.add_basemap(ax, crs=proj, source=cx.providers.Esri.WorldImagery, alpha=.7, attribution_size=6)
        except:
            arcpy.AddMessage("Basemap could not be added to the {}_transect.png map.".format(metric))
        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)
        ax.set_xlabel('Eastings (m)')
        ax.set_ylabel('Northings (m)')
        if metric == 'LRR':
            ax.legend(handles=[legend_entry], fontsize='small', loc='best')
        fig.savefig(os.path.join(self.out_dir, '{0}_transects.png'.format(metric)), dpi=300, bbox_inches='tight')
