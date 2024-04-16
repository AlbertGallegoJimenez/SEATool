import arcpy
import math
import numpy as np
import pandas as pd

class TransectProcessor(object):
    def __init__(self, df, corr_factor):
        """
        This class processes the transects to correct the angle values.
        The class detects the transects that are totally inverted and the transects with large differences in the bearing angle.
        
        Parameters:
            df (DataFrame): The DataFrame with the transects.
            corr_factor (int): The correction factor (threshold) to classify the transects with large differences.
            
        Returns:
            None
        """
        # Initialize the class with a DataFrame
        self.df = df.copy()
        # Set the correction factor
        self.corr_factor = corr_factor
        # Calculate the bearing differences between consecutive transects
        self.df['diff_bear'] = self.df['Bearing'].diff()

    def invert_angles(self):
        """
        This method inverts the angles of the transects that are totally inverted.
        The method detects the first transects that are inverted (if there are more than one change).
        To do so, find a difference angle around ~180º (it has been selected a range of 180 +-50).
        Then, the method detects the transects that need to be inverted and rotates them 180 degrees.
        
        Parameters:
            None
        
        Returns:
            None
        """
        # Define the boolean mask to detect the transects that are totally inverted
        mask_180 = (self.df['diff_bear'].abs() >= 130) & (self.df['diff_bear'].abs() < 230)
        
        # Get a list with the transects that need to be inverted
        start_change_transects = self.df[mask_180]['transect_id'].to_list()

        # Define an empty list of the transects that need to be inverted
        transects2correct = []
        # Iterate over the transects that need to be inverted
        for i, _ in enumerate(start_change_transects):
            if (i + 1) % 2 != 0: # Odd number
                if i == len(start_change_transects) - 1: # Is the last change detected
                    # Get the transects that need to be inverted
                    mask = (self.df['transect_id'] > start_change_transects[i] - 1)
                    # Append the transects to the list
                    transects2correct.extend(self.df[mask]['transect_id'].to_list())
                else: # The change is not the last
                    # Get the transects that need to be inverted
                    mask = (self.df['transect_id'] > start_change_transects[i] - 1) & (self.df['transect_id'] <= start_change_transects[i + 1] - 1)
                    # Append the transects to the list
                    transects2correct.extend(self.df[mask]['transect_id'].to_list())
            else:
                pass
        # Create a new column to store the angle that needs to be rotated
        self.df['Angle'] = 0 # Initialize the column with zeros
        # Rotate the bearing angle 180 degrees
        self.df.loc[self.df['transect_id'].isin(transects2correct), 'Angle'] = 180

    def classify_transects(self):
        """
        This method classifies the transects with large differences in the bearing angle.
        The method uses the correction factor to classify the transects with large differences.
        The method also tries not to take into account the differences in the 360-0 sector. An upper limit of 330 has been set.
        
        Parameters:
            None
            
        Returns:
            None
        """
        # Define the boolean mask to detect the transects with large differences
        mask = (self.df['diff_bear'].abs() > self.corr_factor) & (self.df['diff_bear'].abs() < 330)
        # Create a new column to store the classification
        self.df['correct_angle'] = mask

    def interpolate_angles(self):
        """
        This method interpolates the angles for the transects with large differences.
        The method uses the pandas interpolate method to calculate the missing angles.
        
        Parameters:
            None
            
        Returns:
            None
        """
        # Create a new column to store the new bearing angles
        self.df['new_bearing'] = self.df['Bearing']
        # Set the new bearing angles to NaN for the transects with large differences
        self.df.loc[self.df['correct_angle'], 'new_bearing'] = np.nan
        # Interpolate the missing angles
        self.df['new_bearing'] = self.df['new_bearing'].interpolate(method='linear')
        # Modify the "Angle" column with the angle that needs to be rotated
        self.df['Angle'] = self.df['new_bearing'] - self.df['Bearing']

class RotateFeatures(object):
    def __init__(self, df, fclass):
        """
        This class rotates the features of a polyline feature class.
        The class rotates the vertices of the polylines based on the angle calculated in the previous class.
        
        Parameters:
            df (DataFrame): The DataFrame with the transects.
            fclass (str): The path to the polyline feature class.
        
        Returns:
            None
        
        References:
            https://stackoverflow.com/questions/34372480/rotate-point-about-another-point-in-degrees-python
        """
        # Add an angle field to the feature class
        arcpy.management.AddField(fclass, 'Angle', 'DOUBLE')
        # Update the angle field with the values calculated in the previous class
        with arcpy.da.UpdateCursor(fclass, 'Angle') as cursor:
            for i, row in enumerate(cursor):
                cursor.updateRow([df.loc[i, 'Angle']])

        # Rebuild each polyine with rotated vertices
        with arcpy.da.UpdateCursor(fclass, ['SHAPE@', 'Angle']) as cursor:
            for row in cursor:
                # Create a list to store the rotated vertices
                linelist = []
                for part in row[0]: # Iterate over the parts of the polyline
                    # Create a list to store the rotated points
                    partlist = []
                    for pnt in part: # Iterate over the vertices of the polyline
                        if pnt is not None:
                            # Rotate the points based on the angle
                            partlist.append(self.rotatepoint(pnt, row[0].centroid, row[1])) # Centroid is pivot point
                    # Append the rotated points to the list
                    linelist.append(partlist)
                # Update the row with the rotated vertices
                row[0] = arcpy.Polyline(arcpy.Array(linelist))
                cursor.updateRow(row)

    @staticmethod
    def rotatepoint(point, pivotpoint, angle):
        """
        This method rotates a point around a pivot point.
        The method uses the pivot point as the center of the rotation.
        
        Parameters:
            point (Point): The point to rotate.
            pivotpoint (Point): The pivot point.
            angle (float): The angle to rotate.
            
        Returns:
            Point: The rotated point.
        """
        angle_rad = - math.radians(angle)
        ox, oy = pivotpoint.X, pivotpoint.Y
        px, py = point.X, point.Y
        qx = ox + math.cos(angle_rad) * (px - ox) - math.sin(angle_rad) * (py - oy)
        qy = oy + math.sin(angle_rad) * (px - ox) + math.cos(angle_rad) * (py - oy)    
        return arcpy.Point(qx, qy)
