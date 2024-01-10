import arcpy
import math
import numpy as np
import pandas as pd

class TransectProcessor(object):
    def __init__(self, df, corrFactor):
        # Initialize the class with a DataFrame
        self.df = df.copy()
        # Set the correction factor
        self.corrFactor = corrFactor
        # Calculate the bearing differences between consecutive transects
        self.df['diffBear'] = self.df['Bearing'].diff()

    def invert_angles(self):
        # Detect if there are transects that are totally inverted and calculate the angle that needs to be rotated
        # Detect the first transects that are inverted (if there are more than one change). To do so, find a difference angle around ~180º (it has been selected a range of 180 +-50).
        start_change_transects = self.df[(self.df['diffBear'].abs() >= 130) & (self.df['diffBear'].abs() < 230)]['transect_id'].to_list()

        # Empty list of the transects that need to be inverted
        transects2correct = []
        for i, _ in enumerate(start_change_transects):
            if (i + 1) % 2 != 0: # Odd number
                if i == len(start_change_transects) - 1: # Is the last change
                    mask = (self.df['transect_id'] > start_change_transects[i] - 1)
                    transects2correct.extend(self.df[mask]['transect_id'].to_list())
                else: # The change is not the last
                    mask = (self.df['transect_id'] > start_change_transects[i] - 1) & (self.df['transect_id'] <= start_change_transects[i + 1] - 1)
                    transects2correct.extend(self.df[mask]['transect_id'].to_list())
            else:
                pass
        
        self.df['Angle'] = 0
        self.df.loc[self.df['transect_id'].isin(transects2correct), 'Angle'] = 180 # Rotate 180 degrees the bearing angle

    def classify_transects(self):
        # Classify transects with large differences using the corrFactor value. In addition, try not to take into account the differences in the 360-0 sector.
        self.df['correctAngle'] = (self.df['diffBear'].abs() > self.corrFactor) & (self.df['diffBear'].abs() < 330)

    def interpolate_angles(self):
        # Interpolate angles for transects with large differences
        self.df['newBearing'] = self.df['Bearing']
        self.df.loc[self.df['correctAngle'], 'newBearing'] = np.nan
        self.df['newBearing'] = self.df['newBearing'].interpolate(method='linear')
        # Calculate the angle that needs to be rotated
        self.df['Angle'] = self.df['newBearing'] - self.df['Bearing']

class RotateFeatures(object):
    def __init__(self, df, fclass):
        # Initialize the class by adding an angle field with the values calculated above
        arcpy.management.AddField(fclass, 'Angle', 'DOUBLE')
        
        with arcpy.da.UpdateCursor(fclass, 'Angle') as cursor:
            for i, row in enumerate(cursor):
                cursor.updateRow([df.loc[i, 'Angle']])

        # Rebuild each polyine with rotated vertices
        with arcpy.da.UpdateCursor(fclass, ['SHAPE@', 'Angle']) as cursor:
            for row in cursor:
                linelist = []
                for part in row[0]:
                    partlist = []
                    for pnt in part:
                        if pnt is not None:
                            partlist.append(self.rotatepoint(pnt, row[0].centroid, row[1])) # Centroid is pivot point
                    linelist.append(partlist)
                row[0] = arcpy.Polyline(arcpy.Array(linelist))
                cursor.updateRow(row)

    @staticmethod
    def rotatepoint(point, pivotpoint, angle):
        # Source: https://stackoverflow.com/questions/34372480/rotate-point-about-another-point-in-degrees-python
        angle_rad = - math.radians(angle)
        ox, oy = pivotpoint.X, pivotpoint.Y
        px, py = point.X, point.Y
        qx = ox + math.cos(angle_rad) * (px - ox) - math.sin(angle_rad) * (py - oy)
        qy = oy + math.sin(angle_rad) * (px - ox) + math.cos(angle_rad) * (py - oy)    
        return arcpy.Point(qx, qy)
    

