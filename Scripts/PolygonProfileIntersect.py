#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Polygon Profile Intersect
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: November 2023
'''
This script will create feature classes that will show mapview polygon 
data along a raster profile in cross section view. It will create a point
file with points at the boundary of each polygon. It will also create a 
line file that follows the raster profile, where each line segment is 
labeled with the corresponding mapview polygon. Tool can output data
in the traditional or stacked display. 
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
    profiles_3d = arcpy.GetParameterAsText(0) #raster profiles in 3D (not xsec view)
    xsln_file = arcpy.GetParameterAsText(1)
    xsec_id_field = arcpy.GetParameterAsText(2) #cross section ID in surface profiles
    polygons_orig = arcpy.GetParameterAsText(3) #polygons to intersect
    display_system = arcpy.GetParameterAsText(4) #"stacked" or "traditional"
    output_dir = arcpy.GetParameterAsText(5) #output gdb
    #parameter below appears if display_system == "traditional"
    vertical_exaggeration_in = arcpy.GetParameter(6)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    profiles_3d = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\bedrock_topo_dem_30m_profiles3d' #raster profiles in 3D (not xsec view)
    xsln_file = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\xsln'
    xsec_id_field = "et_id" #cross section ID in surface profiles
    polygons_orig = r'D:\Cross_Section_Programming\112123\script_testing\demo_data_steele.gdb\Bedrock_polys' #polygons to intersect
    display_system = "traditional" #"stacked" or "traditional"
    output_dir = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb' #output gdb
    #parameter below appears if display_system == "traditional"
    vertical_exaggeration_in = 50

    printit("Variables set with hard-coded parameters for testing.")

#%%
# 3 set county relief variable (controls distance between cross sections)
#DO NOT edit this value, except in special cases
if display_system == "stacked":
    county_relief = 700
    vertical_exaggeration = 50
if display_system == "traditional":
    vertical_exaggeration = int(vertical_exaggeration_in)

#%% 
# 4 Data QC

#check to make sure profiles are 3d, not cross section view
desc = arcpy.Describe(profiles_3d)
if desc.hasZ == False:
    printerror("!!ERROR!! Surface profiles do not have z 3D geometry. Select 3D profiles for this parameter and try again.")

#Check that  profiles have mn_et_id field
if display_system == "stacked":
    FieldExists(profiles_3d, 'mn_et_id')

#%% 
# 5 Create temporary polygon file and add unique ID field to use for join later

arcpy.env.overwriteOutput = True

printit("Creating temporary copy of polygon file.")
input_name = os.path.basename(polygons_orig)
polygons = os.path.join(output_dir, input_name + "_temp")
arcpy.conversion.ExportFeatures(polygons_orig, polygons)

printit("Adding temporary join field.")
unique_id_field = 'unique_id'

try:
    arcpy.management.AddField(polygons, unique_id_field, 'LONG')
except:
    printit("Unable to add unique_id field. Field may already exist.")

if 'OBJECTID' in [field.name for field in arcpy.ListFields(polygons)]:
    arcpy.management.CalculateField(polygons, unique_id_field, "!OBJECTID!")
elif 'FID' in [field.name for field in arcpy.ListFields(polygons)]:
    arcpy.management.CalculateField(polygons, unique_id_field, "!FID!")
else:
    printerror("Error: input feature class does not contain OBJECTID or FID field. Conversion will not work without one of these fields.") 

#%% 
# 6 Intersect polygons with 3D surface profiles and create line

printit("Intersecting temp polygons with 3d profiles and creating temporary line file.")

#get filename of output
poly_filename = os.path.basename(polygons_orig)
if display_system == "stacked":
    output_name = poly_filename + "_intersect_lines"
if display_system == "traditional":
    output_name = poly_filename + "_intersect_lines_" + str(vertical_exaggeration) +  "x"
output_line_fc = os.path.join(output_dir, output_name)
#set derived output parameter for script tool
if run_location == "Pro":
    arcpy.SetParameterAsText(7, output_line_fc)

#create name and path for temp output
output_line_fc_temp_multi = os.path.join(output_dir, output_name + "_temp_line_3d_multi")
#create temporary 3D intersect file
arcpy.analysis.Intersect([profiles_3d, polygons], output_line_fc_temp_multi, 'NO_FID', '', 'LINE')
#convert multipart to singlepart
output_line_fc_temp = os.path.join(output_dir, output_name + "_temp_line_3d")
arcpy.management.MultipartToSinglepart(output_line_fc_temp_multi, output_line_fc_temp)

#%% 7 Create empty line file and add fields

printit("Creating empty line file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POLYLINE')
if display_system == "stacked":
    fields = [[xsec_id_field, 'TEXT', '', 5], ["mn_et_id", "TEXT", '', 5], [unique_id_field, 'LONG']]
if display_system == "traditional":
    fields = [[xsec_id_field, 'TEXT', '', 5], [unique_id_field, 'LONG']]
arcpy.management.AddFields(output_line_fc, fields)

#%% 
# 8 Convert geometry to cross section view and write to output file

printit("Creating 2d line geometry.")

if display_system == "stacked":
    # loop thru each line segment in the 3D temp line fc
    # convert xyz coordinates to 2d stacked display
    with arcpy.da.SearchCursor(output_line_fc_temp, ['SHAPE@', xsec_id_field, unique_id_field, 'mn_et_id']) as cursor:
        for line in cursor:
            etid = line[1]
            mn_etid = line[3]
            mn_etid_float = float(mn_etid)
            unique_id = line[2]
            line_pointlist = []
            for vertex in line[0].getPart(0):
                #x coordinate is the same as original
                x_2d = vertex.X
                #calculate new y coordinate based on true z coordinate
                y_2d = (((vertex.Z * 0.3048) - (county_relief * mn_etid_float)) * vertical_exaggeration) + 23100000
                #turn it into a point object
                xy_xsecview = arcpy.Point(x_2d, y_2d)
                line_pointlist.append(xy_xsecview)
            #turn point list into an array and then polyline geometry
            line_array = arcpy.Array(line_pointlist)
            line_geometry = arcpy.Polyline(line_array)
            #insert geometry into output fc
            #attach unique ID to join attributes
            with arcpy.da.InsertCursor(output_line_fc, ['SHAPE@', xsec_id_field, unique_id_field, 'mn_et_id']) as cursor2d:
                cursor2d.insertRow([line_geometry, etid, unique_id, mn_etid])
           
if display_system == "traditional":
    #loop thru each cross section line
    with arcpy.da.SearchCursor(xsln_file, ['SHAPE@', xsec_id_field]) as xsln:
        for line in xsln:
            xsec = line[1]
            printit("Working on line {0}".format(xsec))
            pointlist = []
            for vertex in line[0].getPart(0):
                # Creates a polyline geometry object from xsln vertex points.
                # Necessary for MeasureOnLine method used later.
                point = arcpy.Point(vertex.X, vertex.Y)
                pointlist.append(point)
            array = arcpy.Array(pointlist)
            xsln_geometry = arcpy.Polyline(array)
            #search cursor to get geometry of 3D profile in this line
            with arcpy.da.SearchCursor(output_line_fc_temp, ['SHAPE@', xsec_id_field, unique_id_field], '"{0}" = \'{1}\''.format(xsec_id_field, xsec)) as cursor:
                for line in cursor:
                    unique_id = line[2]
                    line_pointlist = []
                    #get geometry and convert to 2d space
                    for vertex in line[0].getPart(0):
                        #mapview true coordinates
                        x_mp = vertex.X
                        y_mp = vertex.Y
                        z_mp = vertex.Z
                        xy_mp = arcpy.Point(x_mp, y_mp)    
                        #measure on line to find distance from start of xsln                    
                        x_2d_raw = arcpy.Polyline.measureOnLine(xsln_geometry, xy_mp)
                        #convert to feet and divide by vertical exaggeration to squish the x axis
                        x_2d = (x_2d_raw/0.3048)/vertical_exaggeration
                        #y coordinate in 2d space is the same as true elevation (z)
                        y_2d = z_mp
                        xy_2d = arcpy.Point(x_2d, y_2d)
                        #add to list of points
                        line_pointlist.append(xy_2d)
                    #create array and geometry, add geometry to output file
                    line_array = arcpy.Array(line_pointlist)
                    line_geometry = arcpy.Polyline(line_array)
                    with arcpy.da.InsertCursor(output_line_fc, ['SHAPE@', xsec_id_field, unique_id_field]) as cursor2d:
                        cursor2d.insertRow([line_geometry, xsec, unique_id])

#%% 
# 9 Delete temporary files

printit("Deleting temporary line files.")
try: arcpy.management.Delete(output_line_fc_temp_multi)
except: printit("Unable to delete temporary file {0}".format(output_line_fc_temp_multi))
try: arcpy.management.Delete(output_line_fc_temp)
except: printit("Unable to delete temporary file {0}".format(output_line_fc_temp))

#%%
# 10 Create empty point file and add fields
arcpy.env.overwriteOutput = True

#get filename of output
if display_system == "stacked":
    output_name = poly_filename + "_intersect_points"
if display_system == "traditional":
    output_name = poly_filename + "_intersect_points_" + str(vertical_exaggeration) + "x"
output_point_fc = os.path.join(output_dir, output_name)
#set derived output parameter for script tool
if run_location == "Pro":
    arcpy.SetParameterAsText(8, output_point_fc)

printit("Creating empty point file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POINT')
if display_system == "stacked":
    fields = [[xsec_id_field, 'TEXT', '', 5],["mn_et_id", "TEXT", '', 5], [unique_id_field, "LONG"]]
if display_system == "traditional":
    fields = [[xsec_id_field, 'TEXT', '', 5], [unique_id_field, "LONG"]]
arcpy.management.AddFields(output_point_fc, fields)

#%% 
# 11 Convert geometry to cross section view and write to output file

printit("Creating 2d point geometry.")

if display_system == "stacked":
    fields = ['SHAPE@', xsec_id_field, unique_id_field, 'mn_et_id']
if display_system == "traditional":
    fields = ['SHAPE@', xsec_id_field, unique_id_field]

with arcpy.da.SearchCursor(output_line_fc, fields) as cursor:
    for line in cursor:
        geom = line[0]
        etid = line[1]
        unique_id = line[2]
        if display_system == "stacked":
            mn_etid = line[3]
        start = geom.firstPoint
        end = geom.lastPoint
        #with arcpy.da.InsertCursor(output_point_fc, ['SHAPE@', xsec_id_field, unit_field]) as cursor2d:
            #cursor2d.insertRow([start, etid, unit])
            #cursor2d.insertRow([end, etid, unit])
        if display_system == "stacked":
            with arcpy.da.InsertCursor(output_point_fc, ['SHAPE@', xsec_id_field, unique_id_field, 'mn_et_id']) as cursor2d:
                cursor2d.insertRow([start, etid, unique_id, mn_etid])
                cursor2d.insertRow([end, etid, unique_id, mn_etid])
        if display_system == "traditional":
            with arcpy.da.InsertCursor(output_point_fc, ['SHAPE@', xsec_id_field, unique_id_field]) as cursor2d:
                cursor2d.insertRow([start, etid, unique_id])
                cursor2d.insertRow([end, etid, unique_id])

#%% 
# 12 Join fields to line and point files

printit("Joining fields from input to output.")
# list fields in input feature class
join_fields = []
in_fc_fields_all = arcpy.ListFields(polygons)
for field in in_fc_fields_all:
    name = field.name
    join_fields.append(name)

#remove redundant fields from list
#join_fields.remove(xsec_id_field)
join_fields.remove(unique_id_field)
if "Shape" in join_fields:
    join_fields.remove("Shape")
if "OBJECTID" in join_fields:
    join_fields.remove("OBJECTID")
if "FID" in join_fields:
    join_fields.remove("FID")
if "Shape_Length" in join_fields:
    join_fields.remove("Shape_Length")
if "Shape_Area" in join_fields:
    join_fields.remove("Shape_Area")
if "TARGET_FID" in join_fields:
    join_fields.remove("TARGET_FID")
if "Join_Count" in join_fields:
    join_fields.remove("Join_Count")
if "et_id" in join_fields:
    join_fields.remove("et_id")

arcpy.management.JoinField(output_line_fc, unique_id_field, polygons, unique_id_field, join_fields)
arcpy.management.JoinField(output_point_fc, unique_id_field, polygons, unique_id_field, join_fields)

#%% 
# 13 Delete temp files and fields

try: arcpy.management.Delete(polygons)
except: printit("Unable to delete temporary file {0}".format(polygons))
try: arcpy.management.DeleteField(output_line_fc, unique_id_field)
except: printit("Unable to delete temp unique id field from {0}.".format(output_line_fc))
try: arcpy.management.DeleteField(output_point_fc, unique_id_field)
except: printit("Unable to delete temp unique id field from {0}.".format(output_point_fc))

# %% Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))
# %%
