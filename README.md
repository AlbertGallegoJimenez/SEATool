<a name="readme-top"></a>

<!-- PROJECT SHIELDS -->
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/AlbertGallegoJimenez/shoreline-evolution-tool">
    <img src="images/logo-tool.png" alt="Logo" width="80" height="80">
  </a>

<h3 align="center">Shoreline Evolution Analysis</h3>

  <p align="center">
    This repository houses a set of tools that allow the user to perform simple and automated regression analysis of a given coastal zone, all integrated into ArcGIS Pro.
    <br />
    <a href="https://github.com/AlbertGallegoJimenez/shoreline-evolution-tool/tree/main/src/tools"><strong>Explore the code »</strong></a>
    <br />
  </p>
</div>

<!-- ABOUT THE PROJECT -->
## About The Project

<div align="center">
  <a href="https://github.com/AlbertGallegoJimenez/shoreline-evolution-tool">
    <img src="images/framework.png">
  </a>
<br />

The analysis methodology is simple but effective, it is based on the analysis of shoreline variations by segmenting the area into profiles and evaluating linear regressions.
This tool is developed as part of a [Python Toolbox](https://pro.arcgis.com/en/pro-app/latest/arcpy/geoprocessing_and_python/a-quick-tour-of-python-toolboxes.htm) for ArcGIS Pro. The tools that make up the toolbox are designed in a very intuitive way with an interface that is fully integrated seamlessly into ArcGIS Pro.


<!-- GETTING STARTED -->
## Getting Started

### Prerequisites
The following is a list of the programs and libraries used in the tool, with their respective versions:

* ArcGIS Pro (version 3.1)
* Pandas (version 1.4)
* Numpy (version 1.20)
* Shapely (version 2.0)
* Statsmodels (version 0.13)

Regarding the data, this tool is based on the following two files:
* Baseline (Vector - Polyline). This is the reference line used for the assessment of the evolution of the coastal stretch.
* Shorelines (Vector - Polyline). These are the time series of the different shorelines on which the analysis will be based.
  * For the correct functioning of the tool, the file must have a numeric id and date fields.

### Installation

0. Make sure you have cloned the base ArcGIS' anaconda environment so you can install more packages. More info [here](https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/clone-an-environment.htm).
1. Download the content in the "src" folder.
2. Open the Catalog Pane in ArcGIS Pro and open the Toolbox (.pyt file) to see the tools.
<div align="center">
  <a href="https://github.com/AlbertGallegoJimenez/shoreline-evolution-tool">
    <img src="images/open-toolbox.png" >
  </a>


<!-- CONTACT -->
## Contact

Albert Gallego Jiménez - [LinkedIn](https://www.linkedin.com/in/albert-gallego-jimenez) - agalleji8@gmail.com

Project Link: [https://github.com/AlbertGallegoJimenez/shoreline-evolution-tool](https://github.com/AlbertGallegoJimenez/shoreline-evolution-tool)

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[forks-shield]: https://img.shields.io/github/forks/github_username/repo_name.svg?style=for-the-badge
[forks-url]: https://github.com/AlbertGallegoJimenez/shoreline-evolution-tool/forks
[stars-shield]: https://img.shields.io/github/stars/github_username/repo_name.svg?style=for-the-badge
[stars-url]: https://github.com/AlbertGallegoJimenez/shoreline-evolution-tool/stargazers
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/albert-gallego-jimenez
[product-screenshot]: images/framework.png