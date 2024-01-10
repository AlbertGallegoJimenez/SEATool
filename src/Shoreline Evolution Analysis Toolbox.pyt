import arcpy

# 1. Generate Transects Along Baseline
from tools.generateTransects import GenerateTransects

# 2. Correct Transects
from tools.correctTransects import CorrectTransects

# 3. Compute Intersections
from tools.computeIntersections import ComputeIntersection

# 4. Perform the Shoreline Evolution Analysis
from tools.performAnalysis import PerformAnalysis

# 5. Plot The Analysis Results
from tools.plotResults import PlotResults

class Toolbox(object):
    def __init__(self):

        # List of tool classes associated with this toolbox
        self.tools = [GenerateTransects, CorrectTransects, ComputeIntersection, PerformAnalysis, PlotResults]
