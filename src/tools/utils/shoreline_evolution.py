import statsmodels.api as sm
import pandas as pd
import numpy as np

# Define a class with functions to calculate the metrics of the shoreline evolution analysis
class ShorelineEvolution:
    def __init__(self, df, transect_id):
        """
        Class constructor
        
        Args: 
            df (pandas.DataFrame): Time series data with at least three columns, one for dates, one for the variable of interest and another for transects.
            transect_id (integer): Number of the transect in which the analysis will be performed.
        """
        self.df = df.copy()
        self.transect_id = transect_id
        
        # Select only the values of the transect of interest
        self.df = self.df.loc[self.df['transect_id'] == self.transect_id, ['date', 'distance_from_base']]
        
        # Set date as index
        if self.df['date'].dtype == 'object':
            self.df['date'] = pd.to_datetime(self.df['date'])
            
        self.df.set_index('date', inplace=True)
              
        # Calculate the number of days elapsed since the first date
        self.df['days'] = ((self.df.index - self.df.index[0]).days) / 365.24
        
        # Convert data to arrays
        self.X = self.df['days'].values.reshape(-1, 1)
        self.y = self.df['distance_from_base'].values
        
        # Fit linear regression
        self.lr = sm.OLS(self.y, sm.add_constant(self.X)).fit()
        self.ci = self.lr.conf_int(0.05) # 95% confidence interval
        
    def LRR(self):
        """
        Performs a simple linear regression on a time series data and calculates the annual variation rate.
        
        Returns:
            tuple of three elements: The annual variation rate obtained from the linear regression with its lower and upper confidence interval.
        """
        annual_rate = self.lr.params[1]
        lower_ci = self.ci[1, 0]
        upper_ci = self.ci[1, 1]
        
        return annual_rate, lower_ci, upper_ci
    
    def R2(self):
        """
        Performs the calculation of the determination coefficient (R-squared).
        
        Returns:
            float: R-squared value
        """
        return self.lr.rsquared
    
    def Pvalue(self):
        """
        Performs the calculation of the p-value.
        
        Returns:
            float: p-value
        """
        return self.lr.pvalues[1]
    
    def RMSE(self):
        """
        Performs the calculation of the root mean squared error (RMSE) of the linear regression.
        
        Returns:
            float: RMSE
        """
        y_pred = self.lr.predict(sm.add_constant(self.X))
        
        return np.sqrt(np.mean((self.y - y_pred) ** 2))
    
    def SCE(self):
        """
        The shoreline change envelope (SCE) reports a distance (in meters), not a rate.
        The SCE value represents the greatest distance among all the shorelines that intersect a given transect.
        
        Returns:
            float: SCE
        """
        return self.df['distance_from_base'].max() - self.df['distance_from_base'].min()
    
    def NSM(self):
        """
        The net shoreline movement (NSM) is the distance between the oldest and the youngest shorelines for each transect.
        
        Returns:
            float: NSM
        """
        return self.df.iloc[-1]['distance_from_base'] - self.df.iloc[0]['distance_from_base']