#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Create Stacked Cross Section Geodatabase
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: March 2023
'''
This script creates the geodatabase structure for the stacked cross section
display. It will create a gdb and copy over the county boundary and bedrock
topography. It will then create a project area polygon, mapping area polygon 
(1 mile buffer around the county), surface DEM, and cross section line file.
Finally, it creates an editing geodatabase and creates an empty stratline
file inside.
'''

# %% 1 Import modules

import arcpy
import sys
import os
import datetime

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement function for testing and compiled geoprocessing tool

def printit(message):
    if (len(sys.argv) > 1):
        arcpy.AddMessage(message)
    else:
        print(message)

def printwarning(message):
    if (len(sys.argv) > 1):
        arcpy.AddWarning(message)
    else:
        print(message)
        
def printerror(message):
    if (len(sys.argv) > 1):
        arcpy.AddError(message)
    else:
        print(message)

# %% 2 Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):
    #variables retrieved by esri geoprocessing tool
    output_dir = arcpy.GetParameterAsText(0)
    county_boundary = arcpy.GetParameterAsText(1) #or project area, usually the county
    bed_topo_in = arcpy.GetParameterAsText(2)
    project_buffer_area_num = arcpy.GetParameterAsText(3)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    output_dir = r'D:\ScottXS\Script_Testing'
    county_boundary = r'D:\ScottXS\CrossSections.gdb\bdry_counpy2' #or project area, usually the county
    bed_topo_in = r'D:\ScottXS\bt_12_6_22' #bedrock topography
    project_buffer_area_num = "1" #miles, string data type
    printit("Variables set with hard-coded parameters for testing.")

#%% 3 Create gdbs
#DONT create lixpys and profiles feature datasets yet, have later tools do that
printit("Creating cross section gdb in output folder. Tool will overwrite gdb if it already exists.")
arcpy.env.overwriteOutput = True

output_gdb = os.path.join(output_dir, "Cross_Sections_Stacked.gdb")
printit("Creating output gdb {0}".format(output_gdb))
arcpy.management.CreateFileGDB(output_dir, "Cross_Sections_Stacked.gdb")

editing_gdb = os.path.join(output_dir, "Cross_Sections_Stacked_Editing.gdb")
printit("Creating editing gdb {0}".format(editing_gdb))
arcpy.management.CreateFileGDB(output_dir, "Cross_Sections_Stacked_Editing.gdb")

printit("Adding blank stratlines file to editing gdb.")
arcpy.management.CreateFeatureclass(editing_gdb, "stratlines", "POLYLINE")
stratlines = os.path.join(editing_gdb, 'stratlines')
arcpy.management.AddField(stratlines, 'unit', 'TEXT')

#%% Copy over relevant files
#county boundary
printit("Copying county boundary.")
arcpy.conversion.FeatureClassToFeatureClass(county_boundary, output_gdb, 'county_boundary')
county_boundary = os.path.join(output_gdb, 'county_boundary')

#bedrock topography
printit("Copying bedrock topography.")
bed_topo_out = os.path.join(output_gdb, os.path.basename(bed_topo_in))
arcpy.management.CopyRaster(bed_topo_in, bed_topo_out)

#%% Set spatial reference based on county boundary file

spatialref = arcpy.Describe(county_boundary).spatialReference
if spatialref.name == "Unknown":
    printerror("{0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(county_boundary)))
else:
    printit("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(county_boundary)))
    
#%% Buffer county boundary by project buffer parameter(mapping boundary)
printit("Creating mapping boundary by buffering county boundary by {0} miles.".format(project_buffer_area_num))
mapping_boundary = os.path.join(output_gdb, 'mapping_boundary')
project_buffer_area = str(project_buffer_area_num + " Miles")
arcpy.analysis.Buffer(county_boundary, mapping_boundary, project_buffer_area)


#%% Create papg from mapping boundary extent
printit("Creating project area polygon rectangle based on mapping boundary extent.")
#make empty list of x and y vertices
x_list = []
y_list = []

#read geometry of mapping boundary polygon and populate lists
with arcpy.da.SearchCursor(mapping_boundary, ["Shape@"]) as cursor:
    for row in cursor:
        for vertex in cursor[0].getPart(0):
            x = vertex.X
            x_list.append(x)
            y = vertex.Y
            y_list.append(y)

#find min and max values from lists
x_min = min(x_list)
x_max = max(x_list)
y_min = min(y_list)
y_max = max(y_list)

#make point objects for corners of the papg
vertex_1 = arcpy.Point(x_min, y_min)
vertex_2 = arcpy.Point(x_min, y_max)
vertex_3 = arcpy.Point(x_max, y_max)
vertex_4 = arcpy.Point(x_max, y_min)
#make a list and array and polygon geometry object
vertex_list = [vertex_1, vertex_2, vertex_3, vertex_4]
array = arcpy.Array(vertex_list)
poly_geometry = arcpy.Polygon(array)

#create empty papg file and add geometry
arcpy.management.CreateFeatureclass(output_gdb, 'papg', 'POLYGON', '', '', '', spatialref)
papg = os.path.join(output_gdb, 'papg')

with arcpy.da.InsertCursor(papg, ['Shape@']) as papg_cursor:
    papg_cursor.insertRow([poly_geometry])

#%% Clip statewide xsln with papg

arcpy.env.overwriteOutput = True

printit("Clipping statewide cross sections with project area polygon.")
xsln_statewide = r'L:\mgs_doc_repos\statewide_cross_section_lines\CrossSections.gdb\xsln'
xsln = os.path.join(output_gdb, "xsln")
arcpy.analysis.Clip(xsln_statewide, papg, xsln)

printit("Adding et_id field and calculating based on mn_et_id.")
#add et_id field
#create blank mn_et_id list
mn_id_list = []
#create list of mn_et_id values with integer data type
with arcpy.da.SearchCursor(xsln, ['mn_et_id']) as xsln_cursor:
    for row in xsln_cursor:
        mn_et_id = row[0]
        mn_et_id_int = int(mn_et_id)
        mn_id_list.append(mn_et_id_int)

#find minimum mn_et_id
min_mn_id = min(mn_id_list)    
subtract_value = min_mn_id - 1

#add et_id field to xsln
arcpy.management.AddField(xsln, "et_id", "TEXT", '', '', 5)
with arcpy.da.UpdateCursor(xsln, ["mn_et_id", "et_id"]) as xsln_update:
    for row in xsln_update:
        mn_et_id = row[0]
        mn_et_id_int = int(mn_et_id)
        et_id_int = mn_et_id_int - subtract_value
        et_id = str(et_id_int)
        if len (et_id) == 1:
            et_id = "0" + et_id   
        row[1] = et_id
        xsln_update.updateRow(row)

#%% Create surface DEM
#clip to papg
printit("Creating land surface DEM by clipping statewide DEM.")
state_dem = r'G:\gis_data\elevation\elev_dem30_bath_2015\dem30_bath_16'
out_dem = os.path.join(output_gdb, 'dem30dnr')
arcpy.management.Clip(state_dem, '', out_dem, papg, '', 'ClippingGeometry', 'NO_MAINTAIN_EXTENT')

# %% 10 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))