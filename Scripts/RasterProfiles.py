#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Create Raster Profiles 
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: October 2022, updated November 2023
'''
This script creates profiles from raster grids and cross section lines.
Tool can accept multiple raster surfaces, and outputs are labeled with raster
name. Outputs are: 3-dimensional profiles that can be viewed in a local scene, 
and 2-dimensional profiles that can be viewed in 2d stacked or traditional 
cross section space.
'''

#%% 1 Import modules and define functions

import arcpy
import os
import datetime

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement function for testing and compiled geoprocessing tool

def printit(message):
    arcpy.AddMessage(message)
    print(message)
        
        
def printerror(message):
    arcpy.AddError(message)
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

#%% 
# 2 Set parameters to work in testing and compiled geopocessing tool

#run_location = "ide"
run_location = "Pro"

if run_location == "Pro":
    rasters_input = arcpy.GetParameterAsText(0) #input raster surfaces
    xsln_file_orig = arcpy.GetParameterAsText(1) #mapview xsln file
    xsln_etid_field = arcpy.GetParameterAsText(2)
    output_gdb_location = arcpy.GetParameterAsText(3) #output gdb. tool does not create a gdb.
    display_system = arcpy.GetParameterAsText(4) #or "traditional"
    #parameter below only appears if display system is set to "traditional"
    vertical_exaggeration_in = arcpy.GetParameter(5)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    #input raster surfaces: make sure to split with semicolon and use backslashes
    rasters_input = 'D:/Cross_Section_Programming/112123/script_testing/Steele_Script_Testing.gdb/dem30dnr;D:/Cross_Section_Programming/112123/script_testing/Steele_Script_Testing.gdb/bedrock_topo_dem_30m' #input raster surfaces
    xsln_file_orig = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\xsln' #mapview xsln file
    xsln_etid_field = 'et_id'
    output_gdb_location = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb' #output gdb. tool does not create a gdb.
    display_system = "stacked" #"stacked" or "traditional"
    #parameter below only appears if display system is set to "traditional"
    vertical_exaggeration_in = int(50)
    printit("Variables set with hard-coded parameters for testing.")

#%% 
# 3 if display is stacked, set county relief variable 
# this controls the distance between cross sections
#also set vertical exaggeration
#DO NOT edit this value, except in special cases
if display_system == "stacked":
    county_relief = 700
    vertical_exaggeration = int(50)
if display_system == "traditional":
    vertical_exaggeration = int(vertical_exaggeration_in)

#%% 
# 4 Set up raster surfaces list

rasters_list = rasters_input.split(";")

#%% 
# 5 Set spatial reference based on xsln file

spatialref = arcpy.Describe(xsln_file_orig).spatialReference
if spatialref.name == "Unknown":
    printerror("{0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(xsln_file_orig)))
else:
    printit("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(xsln_file_orig)))

#%% 
# 6 Data QC
printit("Checking that input files have correct fields and geometry types for tool to run correctly.")
FileExists(xsln_file_orig)
#check for mn_et_id if output is in stacked display
if display_system == "stacked":
    FieldExists(xsln_file_orig, 'mn_et_id')     
CorrectGeometry(xsln_file_orig, 'Polyline', 'Line')

# %% 
# 7 define fields needed in 2d xsec view output
if display_system == "stacked":
    fields_2d = [[xsln_etid_field, 'TEXT'], ['mn_et_id', 'TEXT', '', 5]]
if display_system == "traditional":
    fields_2d = [[xsln_etid_field, 'TEXT']]

# list fields to be joined after geometry creation
xsln_fields = arcpy.ListFields(xsln_file_orig)
xsln_field_names = []
for field in xsln_fields:
    name = field.name
    xsln_field_names.append(name)
    
#list fields not to be joined if they exist  
#etid field is already in the file, so it won't need to be joined again  
fields_no_join = [xsln_etid_field, "mn_et_id", "OBJECTID", "Shape", "Join_Count", "TARGET_FID", "Shape_Length"]

for name in fields_no_join:
    if name in xsln_field_names:
        xsln_field_names.remove(name)

#%% 
# 8 Create 3D profiles from input raster surface

arcpy.env.overwriteOutput = True

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
    if display_system == "stacked":
        profiles_2d_name = name + "_profiles2d"
    if display_system == "traditional":
        profiles_2d_name = name + "_profiles2d" + "_" + str(vertical_exaggeration) + "x"
    profiles_2d = os.path.join(output_gdb_location, profiles_2d_name)
    arcpy.management.CreateFeatureclass(output_gdb_location, profiles_2d_name, 'POLYLINE', '', 'DISABLED', 'DISABLED')
    # Add fields to empty 2d profiles file

    arcpy.management.AddFields(profiles_2d, fields_2d)

# Convert to 2d view and write geometry
    printit("Starting 2D geometry creation for {0} raster surface.".format(name))
    if display_system == "stacked":
        
        with arcpy.da.SearchCursor(profiles_3d, ['SHAPE@', xsln_etid_field, 'mn_et_id']) as profile:
            for feature in profile:
                et_id = feature[1]
                mn_et_id = feature[2]
                profile_pointlist = []
                # Convert vertices into 2d space and put them in an array
                for vertex in feature[0].getPart(0):
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

    if display_system == "traditional":
        # Create empty feature dataset for storing 3d profiles by xs number. Necessary for 2d geometry loop below.
        printit("Creating feature dataset for storing 3d profiles by cross section number for {0} raster surface.".format(name))
        profiles_3d_byxsec = os.path.join(output_gdb_location, name + "profiles3d_byxsec")
        arcpy.management.CreateFeatureDataset(output_gdb_location, name + "profiles3d_byxsec", spatialref)

        with arcpy.da.SearchCursor(xsln_file_orig, ['SHAPE@', xsln_etid_field]) as xsln:
            for line in xsln:
                et_id = line[1]
                xsln_pointlist = []
                for apex in line[0].getPart(0):
                    # Creates a polyline geometry object from xsln vertex points.
                    # Necessary for MeasureOnLine method used later.
                    point = arcpy.Point(apex.X, apex.Y)
                    xsln_pointlist.append(point)
                xsln_array = arcpy.Array(xsln_pointlist)
                xsln_geometry = arcpy.Polyline(xsln_array)
                # Create a new 3d profile file with only line associated with current xsln
                profile_by_xs_file = os.path.join(profiles_3d_byxsec, "{0}_{1}".format(xsln_etid_field, et_id))
                arcpy.analysis.Select(profiles_3d, profile_by_xs_file, '"{0}" = \'{1}\''.format(xsln_etid_field, et_id))
                printit("Writing 2D geometry for xsec {0} on {1} surface.".format(et_id, name))
                with arcpy.da.SearchCursor(profile_by_xs_file, ['SHAPE@', xsln_etid_field]) as profile:
                    for feature in profile:
                        et_id = feature[1]
                        profile_pointlist = []
                        # Convert vertices into 2d space and put them in an array
                        for vertex in feature[0].getPart(0):
                            xy_mapview = arcpy.Point(vertex.X, vertex.Y)
                            x_2d_meters = xsln_geometry.measureOnLine(xy_mapview)
                            x_2d_feet = x_2d_meters/0.3048
                            x_2d = x_2d_feet/vertical_exaggeration
                            y_2d = vertex.Z
                            xy_xsecview = arcpy.Point(x_2d, y_2d)
                            profile_pointlist.append(xy_xsecview)
                        profile_array = arcpy.Array(profile_pointlist)
                        profile_polyline = arcpy.Polyline(profile_array)
                        # Use Update cursor to write geometry to new file
                        with arcpy.da.InsertCursor(profiles_2d, ['SHAPE@', xsln_etid_field]) as cursor2d:
                            cursor2d.insertRow([profile_polyline, et_id])
        # Delete temporary feature dataset
        printit("Deleting temporary feature dataset for {0} raster surface.".format(name))
        try:
            arcpy.management.Delete(profiles_3d_byxsec)
        except:
            printit("Unable to delete temporary feature dataset.")
    
    # join other fields that are in xsln file
    arcpy.management.JoinField(profiles_2d, xsln_etid_field, xsln_file_orig, xsln_etid_field, xsln_field_names)

    #add layers to current map
    if run_location == "Pro":
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.listMaps()[0] 
        aprxMap.addDataFromPath(profiles_2d)

#%% 
# 9 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))
# %%
