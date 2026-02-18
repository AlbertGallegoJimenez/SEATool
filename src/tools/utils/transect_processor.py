import arcpy
import math
import numpy as np
import pandas as pd


class TransectGenerator(object):
    def __init__(self, baseline_fc, distance, length, sea_side, output_fc):
        """
        This class generates transects along a baseline with intelligent smoothing to handle
        abrupt orientation changes and circular angle geometry (0° = 360°).
        
        Parameters:
            baseline_fc (str): Path to the baseline feature class.
            distance (float): Distance between transects in meters.
            length (float): Length of each transect in meters.
            sea_side (str): Direction to extend transects ("Right" or "Left" relative to baseline direction).
            output_fc (str): Path to the output transect feature class.
            
        Returns:
            None
        """
        self.baseline_fc = baseline_fc
        self.distance = distance
        self.length = length
        self.sea_side = sea_side
        self.output_fc = output_fc
        self.spatial_ref = arcpy.Describe(baseline_fc).spatialReference
        
        # Check if baseline has multiple features
        self.has_baseline_id = self._check_baseline_id()
        
    def _check_baseline_id(self):
        """Check if the baseline feature class has a baseline_id field."""
        field_names = [f.name for f in arcpy.ListFields(self.baseline_fc)]
        return 'baseline_id' in field_names
    
    def generate_transects(self):
        """
        Main method to generate transects along the baseline.
        Processes each baseline feature independently if multiple features exist.
        """
        # Create output feature class
        arcpy.management.CreateFeatureclass(
            out_path=arcpy.env.workspace if arcpy.env.workspace else "in_memory",
            out_name=self.output_fc.split("\\")[-1],
            geometry_type="POLYLINE",
            spatial_reference=self.spatial_ref
        )
        
        # Add transect_id field
        arcpy.management.AddField(self.output_fc, "transect_id", "SHORT")
        
        # Add baseline_id field if needed
        if self.has_baseline_id:
            arcpy.management.AddField(self.output_fc, "baseline_id", "SHORT")
        
        # Generate transects for each baseline feature
        transect_counter = 1
        
        if self.has_baseline_id:
            # Process each baseline feature separately
            fields = ["SHAPE@", "baseline_id"]
        else:
            # Process all as single baseline
            fields = ["SHAPE@"]
        
        with arcpy.da.SearchCursor(self.baseline_fc, fields) as cursor:
            for row in cursor:
                baseline_geom = row[0]
                baseline_id = row[1] if self.has_baseline_id else None
                
                # Generate transects for this baseline feature
                transects = self._generate_transects_for_feature(baseline_geom, baseline_id, transect_counter)
                
                # Insert transects into output feature class
                transect_counter = self._insert_transects(transects, transect_counter)
        
        return self.output_fc
    
    def _generate_transects_for_feature(self, baseline_geom, baseline_id, start_id):
        """
        Generate transects for a single baseline feature with smoothed orientations.
        
        Parameters:
            baseline_geom: Polyline geometry of the baseline
            baseline_id: ID of the baseline feature (or None)
            start_id: Starting transect ID
            
        Returns:
            List of tuples: [(geometry, transect_id, baseline_id), ...]
        """
        transects = []
        
        # Get points along the baseline at specified intervals
        points_data = self._get_baseline_points(baseline_geom)
        
        # Calculate smoothed orientations using circular geometry
        orientations = self._calculate_smoothed_orientations(points_data)
        
        # Generate transect geometries
        for i, (point, orientation) in enumerate(zip(points_data, orientations)):
            # Calculate perpendicular angle based on sea side
            transect_angle = self._calculate_transect_angle(orientation)
            
            # Create transect geometry
            transect_geom = self._create_transect_geometry(point, transect_angle)
            
            # Store transect data
            transect_id = start_id + i
            transects.append((transect_geom, transect_id, baseline_id))
        
        return transects
    
    def _get_baseline_points(self, baseline_geom):
        """
        Get points along the baseline at specified intervals.
        The first transect has a small longitudinal offset to avoid further spatial operations 
        mismatches due to placing it exactly at the baseline start.
        
        Parameters:
            baseline_geom: Polyline geometry
            
        Returns:
            List of (x, y, distance_along) tuples
        """
        points_data = []
        total_length = baseline_geom.length
        
        # Generate points at specified intervals
        # Start with a small longitudinal offset (1m) for the first transect
        longitudinal_offset = 1.0  # meters
        current_distance = longitudinal_offset
        
        while current_distance <= total_length:
            point = baseline_geom.positionAlongLine(current_distance)
            centroid = point.centroid
            points_data.append((centroid.X, centroid.Y, current_distance))
            current_distance += self.distance
        
        return points_data
    
    def _calculate_smoothed_orientations(self, points_data):
        """
        Calculate smoothed orientations at each point using circular averaging.
        Uses a moving window to smooth out abrupt changes in baseline direction.
        
        Parameters:
            points_data: List of (x, y, distance_along) tuples
            
        Returns:
            List of smoothed orientations in degrees (0-360)
        """
        if len(points_data) < 2:
            return [0]  # Default orientation if insufficient points
        
        # Window size for smoothing (number of points on each side)
        window_points = 5
        
        orientations = []
        
        for i in range(len(points_data)):
            # Define window bounds
            start_idx = max(0, i - window_points)
            end_idx = min(len(points_data) - 1, i + window_points)
            
            # Extract window points
            window = points_data[start_idx:end_idx + 1]
            
            if len(window) < 2:
                # Use simple bearing if window too small
                if i > 0:
                    dx = points_data[i][0] - points_data[i-1][0]
                    dy = points_data[i][1] - points_data[i-1][1]
                else:
                    dx = points_data[i+1][0] - points_data[i][0]
                    dy = points_data[i+1][1] - points_data[i][1]
                angle = math.degrees(math.atan2(dx, dy)) % 360
                orientations.append(angle)
                continue
            
            # Calculate bearing vectors between consecutive points in window
            vectors_x = []
            vectors_y = []
            
            for j in range(len(window) - 1):
                dx = window[j+1][0] - window[j][0]
                dy = window[j+1][1] - window[j][1]
                
                # Convert to unit vector with angle
                angle = math.atan2(dx, dy)  # Bearing angle in radians
                vectors_x.append(math.sin(angle))
                vectors_y.append(math.cos(angle))
            
            # Average vectors (circular mean)
            mean_x = np.mean(vectors_x)
            mean_y = np.mean(vectors_y)
            
            # Convert back to angle
            smoothed_angle = math.degrees(math.atan2(mean_x, mean_y)) % 360
            orientations.append(smoothed_angle)
        
        return orientations
    
    def _calculate_transect_angle(self, baseline_orientation):
        """
        Calculate the angle for the transect based on baseline orientation and sea side.
        
        Parameters:
            baseline_orientation: Orientation of baseline in degrees (0-360)
            
        Returns:
            Transect angle in degrees (0-360)
        """
        # Calculate perpendicular angle
        if self.sea_side == "Right":
            # Perpendicular to the right (clockwise 90°)
            transect_angle = (baseline_orientation + 90) % 360
        else:  # "Left"
            # Perpendicular to the left (counter-clockwise 90°)
            transect_angle = (baseline_orientation - 90) % 360
        
        return transect_angle
    
    def _create_transect_geometry(self, point, angle):
        """
        Create a transect line geometry from a point extending in the specified direction.
        The transect extends slightly inland (0.5m) to ensure intersection with baseline,
        then extends the full length toward the sea.
        
        Parameters:
            point: Tuple (x, y) of the baseline point
            angle: Angle in degrees (0-360) for transect direction
            
        Returns:
            Polyline geometry
        """
        baseline_x, baseline_y = point[0], point[1]
        
        # Convert angle to radians
        angle_rad = math.radians(angle)
        
        # Calculate start point: 0.5m inland from baseline (opposite direction)
        inland_offset = 0.5  # meters
        start_x = baseline_x - inland_offset * math.sin(angle_rad)
        start_y = baseline_y - inland_offset * math.cos(angle_rad)
        
        # Calculate end point: full length from baseline toward sea
        end_x = baseline_x + self.length * math.sin(angle_rad)
        end_y = baseline_y + self.length * math.cos(angle_rad)
        
        # Create polyline from inland to sea
        array = arcpy.Array([
            arcpy.Point(start_x, start_y),
            arcpy.Point(end_x, end_y)
        ])
        
        return arcpy.Polyline(array, self.spatial_ref)
    
    def _insert_transects(self, transects, start_id):
        """
        Insert generated transects into the output feature class.
        
        Parameters:
            transects: List of (geometry, transect_id, baseline_id) tuples
            start_id: Starting transect ID
            
        Returns:
            Next available transect ID
        """
        if self.has_baseline_id:
            fields = ["SHAPE@", "transect_id", "baseline_id"]
        else:
            fields = ["SHAPE@", "transect_id"]
        
        with arcpy.da.InsertCursor(self.output_fc, fields) as cursor:
            for transect_geom, transect_id, baseline_id in transects:
                if self.has_baseline_id:
                    cursor.insertRow([transect_geom, transect_id, baseline_id])
                else:
                    cursor.insertRow([transect_geom, transect_id])
        
        return start_id + len(transects)


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
