import arcpy

# 1a. Generate Transects Along Baseline
from tools.generateTransects import GenerateTransects

# 1b. Correct Transects
from tools.correctTransects import CorrectTransects

# 2. Compute Intersections
from tools.computeIntersections import ComputeIntersection

# 3. Perform the Shoreline Evolution Analysis
from tools.performAnalysis import PerformAnalysis

# 4. Plot The Analysis Results
from tools.plotResults import PlotResults

class Toolbox(object):
    def __init__(self):
        
        self.label = "SEATool"
        self.alias = "Shoreline Evolution Analysis Toolboox"

        # List of tool classes associated with this toolbox
        self.tools = [GenerateTransects, CorrectTransects, ComputeIntersection,
                      PerformAnalysis, PlotResults]
