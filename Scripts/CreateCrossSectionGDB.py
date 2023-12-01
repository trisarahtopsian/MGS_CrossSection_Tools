#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Create Cross Section GDB
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: November 2023
'''
This script creates a geodatabase for cross section creation. Based
on the county boundary or project area, it will create a surface
topography DEM, mapping boundary, and project area polygon. Optionally,
it will add a bedrock topography raster. Also optionally, it will
create a qstrat editing gdb with a stratline file, and create
1-km spaced cross sections for qstrat.
'''

# %%
# 1 Import modules and define functions

import arcpy
import os
import datetime

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement function for testing and compiled geoprocessing tool

def printit(message):
    arcpy.AddMessage(message)
    print(message)

def printwarning(message):
    arcpy.AddWarning(message)
    print(message)
        
def printerror(message):
    arcpy.AddError(message)
    print(message)

# Define file exists function and field exists function

def FileExists(file):
    if not arcpy.Exists(file):
        printerror("Error: {0} does not exist.".format(os.path.basename(file)))
    #else: printit("{0} found.".format(os.path.basename(file)))
    
def FieldExists(dataset, field_name):
    if field_name in [field.name for field in arcpy.ListFields(dataset)]:
        return True
    else:
        printerror("Error: {0} field does not exist in {1}."
                .format(field_name, os.path.basename(dataset)))

# Define function to check for geometry type

def correctGeometry(file, geometry1, geometry2):
    desc = arcpy.Describe(file)
    if not desc.shapeType == geometry1:
        if not desc.shapeType == geometry2:
            printerror("Error: {0} does not have {1} geometry.".format(os.path.basename(file), geometry1))
    #else: printit("{0} has {1} geometry.".format(os.path.basename(file), geometry))

# %% 
# 2 Set parameters to work in testing and compiled geopocessing tool

# !!!!!!!!!!!!!!!!!!!!!! 
#change the variable below if running in an IDE. 
# MAKE SURE TO CHANGE BACK TO "PRO" WHEN FINISHED
#----------------------------------------------------------------
#run_location = "ide"
run_location = "Pro"
#----------------------------------------------------------------
#!!!!!!!!!!!!!!!!!!!!!!

if run_location == "Pro":
    #variable = arcpy.GetParameterAsText(0)
    county_boundary_in = arcpy.GetParameterAsText(0)
    bed_topo_in = arcpy.GetParameterAsText(1) #optional parameter
    project_buffer_area_num = int(arcpy.GetParameterAsText(2))
    output_gdb = arcpy.GetParameterAsText(3) #EXISTING gdb
    qstrat_xsln_file = arcpy.GetParameter(4) #boolean
    qstrat_editing_gdb = arcpy.GetParameter(5) #boolean
    xsln_in = arcpy.GetParameterAsText(6)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    county_boundary_in = r'D:\Cross_Section_Programming\112123\script_testing\demo_data_steele.gdb\county_boundary'
    bed_topo_in = r'D:\Cross_Section_Programming\112123\script_testing\demo_data_steele.gdb\bedrock_topo_dem_30m' #optional parameter
    project_buffer_area_num = 1 #distance in miles to buffer county boundary for project mapping area
    output_gdb = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb' #EXISTING gdb
    qstrat_xsln_file = True #boolean to create qstrat xsln file
    qstrat_editing_gdb = True #boolean to create qstrat editing gdb with stratline file
    xsln_in = r'' # if it already exists, copy it over
    printit("Variables set with hard-coded parameters for testing.")

#%%
# 3 Create GDB(s)
arcpy.env.overwriteOutput = True

output_dir = os.path.dirname(output_gdb)
output_name = os.path.basename(output_gdb)
printit("Creating output gdb {0}. Tool will overwrite gdb if it already exists".format(output_gdb))
arcpy.management.CreateFileGDB(output_dir, output_name)

if qstrat_editing_gdb == True:
    output_name2 = output_name.replace(".gdb", "_Editing.gdb")
    editing_gdb = os.path.join(output_dir, output_name2)
    printit("Creating editing gdb {0}".format(editing_gdb))
    arcpy.management.CreateFileGDB(output_dir, output_name2)

    printit("Adding blank stratlines file to editing gdb.")
    arcpy.management.CreateFeatureclass(editing_gdb, "stratlines", "POLYLINE")
    stratlines = os.path.join(editing_gdb, 'stratlines')
    arcpy.management.AddField(stratlines, 'unit', 'TEXT')

#%% 
# 4 Copy over county boundary and bedrock topo
#county boundary
printit("Copying county boundary.")
county_boundary_out = os.path.join(output_gdb, 'county_boundary')
arcpy.conversion.ExportFeatures(county_boundary_in, county_boundary_out)

try:
    printit("Copying bedrock topography.")
    bed_topo_out = os.path.join(output_gdb, os.path.basename(bed_topo_in))
    arcpy.management.CopyRaster(bed_topo_in, bed_topo_out)
except:
    printit("No bedrock topography raster added.")

try:
    printit("Copying cross section line file.")
    xsln_out = os.path.join(output_gdb, os.path.basename(xsln_in))
    arcpy.conversion.ExportFeatures(xsln_in, xsln_out)
except:
    printit("No cross section lines copied from existing file.")

#%% 
# 5 Set spatial reference based on county boundary file

spatialref = arcpy.Describe(county_boundary_out).spatialReference
if spatialref.name == "Unknown":
    printerror("{0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(county_boundary_out)))
else:
    printit("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(county_boundary_out)))

#%% 
# 6 Buffer county boundary by project buffer parameter(mapping boundary)
printit("Creating mapping boundary by buffering county boundary by {0} miles.".format(project_buffer_area_num))
mapping_boundary = os.path.join(output_gdb, 'mapping_boundary')
project_buffer_area = str(project_buffer_area_num) + " Miles"
arcpy.analysis.Buffer(county_boundary_out, mapping_boundary, project_buffer_area)
 
#%% 
# 7 Create papg from mapping boundary extent
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

#%% 
# 8 Clip statewide xsln with papg
if qstrat_xsln_file == True:
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

else:
    printit("No qstrat xsln file added to gdb.")

#%% 
# 9 Create surface DEM
#clip to papg

printit("Creating land surface DEM by clipping statewide DEM.")
state_dem = r'G:\gis_data\elevation\elev_dem30_bath_2015\dem30_bath_16'
out_dem = os.path.join(output_gdb, 'dem30dnr')
arcpy.management.Clip(state_dem, '', out_dem, papg, '', 'ClippingGeometry', 'NO_MAINTAIN_EXTENT')

# %% Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))
# %%
