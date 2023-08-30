#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Extract Profiles (Stacked)
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: October 2022
'''
This script creates profiles from raster grids and cross section lines.
Tool can accept multiple raster surfaces, and outputs are labeled with raster
name. Outputs are: 3-dimensional profiles that can be viewed in a local scene, 
and 2-dimensional profiles that can be viewed in 2d stacked cross section space.
'''

#%% 1 Import modules and define functions

import arcpy
import os
import sys
import datetime

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement function for testing and compiled geoprocessing tool

def printit(message):
    if (len(sys.argv) > 1):
        arcpy.AddMessage(message)
    else:
        print(message)
        
        
def printerror(message):
    if (len(sys.argv) > 1):
        arcpy.AddError(message)
    else:
        print(message)

# Define file exists function and field exists function

def FileExists(file):
    if not arcpy.Exists(file):
        printerror("Error: {0} does not exist.".format(os.path.basename(file)))
    
def FieldExists(dataset, field_name):
    if field_name in [field.name for field in arcpy.ListFields(dataset)]:
        return True
    else:
        printerror("Error: {0} field does not exist in {1}."
                .format(field_name, os.path.basename(dataset)))

# Define function to check for geometry type

def CorrectGeometry(file, geometry1, geometry2):
    desc = arcpy.Describe(file)
    if not desc.shapeType == geometry1:
        if not desc.shapeType == geometry2:
            printerror("Error: {0} does not have {1} geometry.".format(os.path.basename(file), geometry1))

#%% 2 Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):
    rasters_input = arcpy.GetParameterAsText(0) #input raster surfaces
    xsln_file_orig = arcpy.GetParameterAsText(1)
    output_gdb_location = arcpy.GetParameterAsText(2) #output gdb
    xsln_etid_field = arcpy.GetParameterAsText(3)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    #input raster surfaces: make sure to split with semicolon and use backslashes
    rasters_input = 'D:/Pipestone_CrossSections/CrossSections_Stacked.gdb/bedrock_topography_raster;D:/Pipestone_CrossSections/dem30dnr' #input raster surfaces
    xsln_file_orig = r'D:\Pipestone_CrossSections\CrossSections_Stacked.gdb\xsln' #mapview xsln file
    output_gdb_location = r'D:\Pipestone_CrossSections\CrossSections_Stacked.gdb' #output gdb. tool does not create a gdb.
    xsln_etid_field = 'et_id'
    printit("Variables set with hard-coded parameters for testing.")

#%% 3 set county relief variable (controls distance between cross sections)
#also set vertical exaggeration
#DO NOT edit this value, except in special cases
county_relief = 700
vertical_exaggeration = int(50)

#%% 4 Set up raster surfaces list

rasters_list = rasters_input.split(";")

#%% 5 Set spatial reference based on xsln file

spatialref = arcpy.Describe(xsln_file_orig).spatialReference
if spatialref.name == "Unknown":
    printerror("{0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(xsln_file_orig)))
else:
    printit("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(xsln_file_orig)))

#%% 6 Data QC

printit("Checking that input files have correct fields and geometry types for tool to run correctly.")
FileExists(xsln_file_orig)
FieldExists(xsln_file_orig, 'mn_et_id')     
CorrectGeometry(xsln_file_orig, 'Polyline', 'Line')

#%% 7 Create 3D profiles from input raster surface

arcpy.env.overwriteOutput = True

# define fields needed in 2d xsec view output
fields_2d = [[xsln_etid_field, 'TEXT'], ['mn_et_id', 'TEXT', '', 5]]

for raster in rasters_list:
    name = os.path.basename(raster)
    printit("Creating 3d profiles for {0} raster surface.".format(name))
    # Use interpolate shape to create 3d profiles along xs lines
    profiles_3d_multi = os.path.join(output_gdb_location, name + "_profiles3d_multi")
    arcpy.ddd.InterpolateShape(raster, xsln_file_orig, profiles_3d_multi, 10)
    #arcpy.ddd.InterpolateShape(raster, xsln_file_orig, profiles_3d_multi)
    # Convert to single part in case there was a gap in the raster
    printit("Converting multipart 3d profiles into single part for {0} raster surface.".format(name))
    profiles_3d = os.path.join(output_gdb_location, name + "_profiles3d")
    arcpy.management.MultipartToSinglepart(profiles_3d_multi, profiles_3d)
    # Delete multipart profiles
    printit("Deleting multipart profiles file for {0} raster surface.".format(name))
    arcpy.management.Delete(profiles_3d_multi)

# Convert 3D xsln's to 2D view
    # Create empty 2d profiles file
    printit("Creating empty 2d profiles file for geometry creation for {0} surface.".format(name))
    profiles_2d = os.path.join(output_gdb_location, name + "_profiles2d")
    arcpy.management.CreateFeatureclass(output_gdb_location, name + "_profiles2d", 'POLYLINE', '', 'DISABLED', 'DISABLED')
    # Add fields to empty 2d profiles file

    arcpy.management.AddFields(profiles_2d, fields_2d)

# Convert to 2d view and write geometry
    printit("Starting 2D geometry creation for {0} raster surface.".format(name))
    with arcpy.da.SearchCursor(profiles_3d, ['OID@', 'SHAPE@', xsln_etid_field, 'mn_et_id']) as profile:
        for feature in profile:
            et_id = feature[2]
            mn_et_id = feature[3]
            profile_pointlist = []
            # Convert vertices into 2d space and put them in an array
            for vertex in feature[1].getPart(0):
                x_2d = vertex.X
                y_2d_raw = vertex.Z
                #etid_int = int(et_id)
                mn_etid_int = int(mn_et_id)
                #y_2d = ((y_2d_raw * 0.3048) - (county_relief * etid_int)) * vertical_exaggeration
                #y_2d = ((y_2d_raw * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration
                y_2d = (((y_2d_raw * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
                xy_xsecview = arcpy.Point(x_2d, y_2d)
                profile_pointlist.append(xy_xsecview)
            profile_array = arcpy.Array(profile_pointlist)
            profile_polyline = arcpy.Polyline(profile_array)
            # Use Update cursor to write geometry to new file
            with arcpy.da.InsertCursor(profiles_2d, ['SHAPE@', xsln_etid_field, 'mn_et_id']) as cursor2d:
                cursor2d.insertRow([profile_polyline, et_id, mn_et_id])

#%% 8 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))