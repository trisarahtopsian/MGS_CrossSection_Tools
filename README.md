# MGS Quaternary Cross Section Tools

This repository contains ArcGIS toolboxes of Python 3 geoprocessing tools for setting up cross section data, editing, and checking for data quality. The data are set up in a "stacked" display, which allows the user to view all east-west cross sections without the use of data-driven pages or map series. The stacked display uses mapview X coordinates for the horizontal dimension. The display only works for precisely east-west cross sections, and will not work for zig-zag or diagonal cross section lines.

There are two toolbox files: `MGS_ArcPro_CrossSectionTools.tbx` and `MGS_XSEditingAndQC_ArcPro.tbx`. The first toolbox contains all stacked cross section tools, and the second contains duplicates of tools that are used during cross section data creation. The second toolbox was created to reduce clutter for mapping geologists so they only see the tools that they need to use. The first toolbox also contains tools to convert data between the "stacked" and "traditional" cross section displays.

Some documentation, sample data, and layer files for the tools can be found in this repository. It is currently under construction.
