#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Polygon Boxes
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: November 2023
'''
This tool will create rectangles in cross section view based on
locations of polygons in mapview. The anticipated use is to show areas of 
tribal land that should not be mapped. It can also be used to create a 
polygon showing county area in xsec view, which can be used to clip cross
section data to the county boundary. The tool may have additional
applications as well.
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
    xsln = arcpy.GetParameterAsText(0) #mapview xsln file
    xsec_id_field = arcpy.GetParameterAsText(1) #et_id in xsln
    intersect_polys = arcpy.GetParameterAsText(2) #polygon file to intersect with xsln. county boundary, papg, etc.
    output_dir = arcpy.GetParameterAsText(3)
    display_system = arcpy.GetParameterAsText(4) #"stacked" or "traditional"
    #parameter below only appears if display system is traditional
    vertical_exaggeration_in = arcpy.GetParameter(5)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    xsln = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\xsln' #mapview xsln file
    xsec_id_field = 'et_id' #et_id in xsln
    intersect_polys = r'D:\Cross_Section_Programming\112123\script_testing\demo_data_steele.gdb\Bedrock_polys_Mz' #polygon file to intersect with xsln. county boundary, papg, etc.
    output_dir = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb'
    display_system = "stacked" #"stacked" or "traditional"
    #parameter below only appears if display system is traditional
    vertical_exaggeration_in = 50
    printit("Variables set with hard-coded parameters for testing.")

#%% 
# 3 Stacked display variables and QC
#DO NOT edit these variables, except in special cases
if display_system == "stacked":
    county_relief = 700
    vertical_exaggeration = 50
    #Check that xsln file has mn_et_id field
    FieldExists(xsln, 'mn_et_id')
if display_system == "traditional":
    vertical_exaggeration = int(vertical_exaggeration_in)

# Set spatial reference based on xsln file

spatialref = arcpy.Describe(xsln).spatialReference
if spatialref.name == "Unknown":
    printerror("{0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(xsln)))
else:
    printit("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(xsln)))


#%% 
# 4 Add unique ID field to temp fc so join works correctly later
printit("Adding temporary join field.")
unique_id_field = 'unique_id'

try:
    arcpy.management.AddField(intersect_polys, unique_id_field, 'LONG')
except:
    printit("Unable to add unique_id field. Field may already exist.")

if 'OBJECTID' in [field.name for field in arcpy.ListFields(intersect_polys)]:
    arcpy.management.CalculateField(intersect_polys, unique_id_field, "!OBJECTID!")
elif 'objectid' in [field.name for field in arcpy.ListFields(intersect_polys)]:
    arcpy.management.CalculateField(intersect_polys, unique_id_field, "!objectid!")
elif 'FID' in [field.name for field in arcpy.ListFields(intersect_polys)]:
    arcpy.management.CalculateField(intersect_polys, unique_id_field, "!FID!")
elif 'fid' in [field.name for field in arcpy.ListFields(intersect_polys)]:
    arcpy.management.CalculateField(intersect_polys, unique_id_field, "!fid!")
else: printerror("Error: input feature class does not contain OBJECTID or FID field. Conversion will not work without one of these fields.") 
    
#%% 
# 5 Intersect 
arcpy.env.overwriteOutput = True

printit("Intersecting polygons with xsln and creating temporary line file.")

if display_system == "stacked":
    output_name = os.path.basename(intersect_polys + "_boxes_2d")
if display_system == "traditional":
    output_name = os.path.basename(intersect_polys + "_boxes_2d_" + str(vertical_exaggeration) + "x")

#create name and path for temp output
output_fc_temp_multi = os.path.join(output_dir, output_name + "_temp_3d_multi")
#create temporary 3D intersect file
arcpy.analysis.Intersect([xsln, intersect_polys], output_fc_temp_multi, 'NO_FID', '', 'LINE')
#convert multipart to singlepart
output_fc_temp = os.path.join(output_dir, output_name + "_temp_3d")
arcpy.management.MultipartToSinglepart(output_fc_temp_multi, output_fc_temp)

#%% 
# 6 Create empty polygon file and add fields

#define variable for temp geometry file
output_poly_geom = os.path.join(output_dir, output_name + "_temp_geom")

printit("Creating empty line file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name + "_temp_geom", 'POLYGON')
fields = [[xsec_id_field, 'TEXT', '', 5], [unique_id_field, "LONG"]]
if display_system == "stacked":
    fields.append(["mn_et_id", "TEXT", '', 5])
arcpy.management.AddFields(output_poly_geom, fields)

#%% 
# 7 Convert geometry to cross section view and write to output file

printit("Creating 2d line geometry.")

if display_system == "stacked":
    fields = ['SHAPE@', xsec_id_field, unique_id_field, 'mn_et_id']

    with arcpy.da.SearchCursor(output_fc_temp, fields) as cursor:
        for line in cursor:
            etid = line[1]
            mn_etid = line[3]
            mn_etid_int = int(mn_etid)
            unique_id = line[2]
            #set top and bottom y coordinates for every x
            y_2d_1 = (((50 * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
            y_2d_2 = (((2300 * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
            pointlist = []
            x_list = []
            for vertex in line[0].getPart(0):
                #get x coordinate
                x_2d = vertex.X
                #make list of x coordinates in line
                x_list.append(x_2d)
            #create 2 vertical lines, one at each endpoint of the line
            pt1 = arcpy.Point(x_list[0], y_2d_1)
            pt2 = arcpy.Point(x_list[0], y_2d_2)
            pt3 = arcpy.Point(x_list[-1], y_2d_2)
            pt4 = arcpy.Point(x_list[-1], y_2d_1)

            pointlist.append(pt1)
            pointlist.append(pt2)
            pointlist.append(pt3)
            pointlist.append(pt4)
            array = arcpy.Array(pointlist)
            geometry = arcpy.Polygon(array)
            #create geometry into output file
            with arcpy.da.InsertCursor(output_poly_geom, ['SHAPE@', unique_id_field, xsec_id_field, 'mn_et_id']) as cursor2d:
                cursor2d.insertRow([geometry, unique_id, etid, mn_etid])

if display_system == "traditional":
    # Create empty feature dataset for storing 3d profiles by xs number. Necessary for 2d geometry loop below.
    printit("Creating feature dataset for storing temporary lines by cross section number.")
    output_gdb_location = os.path.dirname(output_poly_geom)
    lines_byxsec = os.path.join(output_gdb_location, "lines_by_xsec_temp")
    arcpy.management.CreateFeatureDataset(output_gdb_location, "lines_by_xsec_temp", spatialref)
    
    #2D y coordinates are the same for every box
    #approximate max and min elevations for the whole state
    y_2d_1 = 50
    y_2d_2 = 2300

    with arcpy.da.SearchCursor(xsln, ['SHAPE@', xsec_id_field]) as xsln_cursor:
        for line in xsln_cursor:
            etid = line[1]
            xsln_pointlist = []
            for apex in line[0].getPart(0):
                # Creates a polyline geometry object from xsln vertex points.
                # Necessary for MeasureOnLine method used later.
                point = arcpy.Point(apex.X, apex.Y)
                xsln_pointlist.append(point)
            xsln_array = arcpy.Array(xsln_pointlist)
            xsln_geometry = arcpy.Polyline(xsln_array)
            # Create a new temp line file with intersect lines on the current xsln
            line_by_xs_file = os.path.join(lines_byxsec, "{0}_{1}".format(xsec_id_field, etid))
            arcpy.analysis.Select(output_fc_temp, line_by_xs_file, '"{0}" = \'{1}\''.format(xsec_id_field, etid))
            printit("Writing 2D geometry for xsec {0}.".format(etid))
            with arcpy.da.SearchCursor(line_by_xs_file, ['SHAPE@', unique_id_field]) as cursor:
                for feature in cursor:
                    unique_id = feature[1]
                    #empty pointlist for storing 2D points
                    pointlist = []
                    # measure 2D x coordinate for first point
                    first_pt = feature[0].firstPoint
                    first_x_2d_meters = xsln_geometry.measureOnLine(first_pt)
                    first_x_2d_feet = first_x_2d_meters/0.3048
                    first_x_2d = first_x_2d_feet/vertical_exaggeration
                    #measure 2D x coordinate for last point
                    last_pt = feature[0].lastPoint
                    last_x_2d_meters = xsln_geometry.measureOnLine(last_pt)
                    last_x_2d_feet = last_x_2d_meters/0.3048
                    last_x_2d = last_x_2d_feet/vertical_exaggeration
                    #create points for corners of rectangle in 2D space
                    pt1 = arcpy.Point(first_x_2d, y_2d_1)
                    pt2 = arcpy.Point(first_x_2d, y_2d_2)
                    pt3 = arcpy.Point(last_x_2d, y_2d_2)
                    pt4 = arcpy.Point(last_x_2d, y_2d_1)
                    #add points to list and create array and polygon geometry
                    pointlist.append(pt1)
                    pointlist.append(pt2)
                    pointlist.append(pt3)
                    pointlist.append(pt4)
                    array = arcpy.Array(pointlist)
                    geometry = arcpy.Polygon(array)
                    #create geometry into output file
                    with arcpy.da.InsertCursor(output_poly_geom, ['SHAPE@', unique_id_field, xsec_id_field]) as cursor2d:
                        cursor2d.insertRow([geometry, unique_id, etid])

    printit("Deleting temporary feature dataset {0}".format(lines_byxsec))
    try: arcpy.management.Delete (lines_byxsec)
    except: printit("Unable to delete temporary feature dataset")

#%% 
# 8 Dissolve and Join fields from original polygon file
arcpy.env.overwriteOutput = True
# dissolve by unique id and xsec ID
#output_poly_diss = os.path.join(output_dir, output_name + "_diss")
output_poly_fc = os.path.join(output_dir, output_name)
#set derived output parameter for script tool
if run_location == "Pro":
    arcpy.SetParameterAsText(6, output_poly_fc)

printit("Dissolving output and joining attributes.")
arcpy.management.Dissolve(output_poly_geom, output_poly_fc, [unique_id_field, xsec_id_field], '', 'SINGLE_PART')

#create empty list for storing names of fields to join
join_fields = []
#list all fields in original polygons
input_fields = arcpy.ListFields(intersect_polys)
for field in input_fields:
    name = field.name
    join_fields.append(name)

#remove redundant fields from list
if "mn_et_id" in join_fields:
    join_fields.remove("mn_et_id")
if "unique_id" in join_fields:
    join_fields.remove("unique_id")
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


#join unit field using the unique id
arcpy.management.JoinField(output_poly_fc, unique_id_field, intersect_polys, unique_id_field, join_fields)

#%% 
# 9 Delete temporary files and fields

printit("Deleting temporary line files.")
try: arcpy.management.Delete(output_fc_temp_multi)
except: printit("Unable to delete temporary file {0}".format(output_fc_temp_multi))
try: arcpy.management.Delete(output_fc_temp)
except: printit("Unable to delete temporary file {0}".format(output_fc_temp))
try: arcpy.management.Delete(output_poly_geom)
except: printit("Unable to delete temporary file {0}".format(output_poly_geom))

try: arcpy.management.DeleteField(intersect_polys, unique_id_field)
except: printit("Unable to delete temporary uniqueid field from original polygons.")
try: arcpy.management.DeleteField(output_poly_fc, unique_id_field)
except: printit("Unable to delete temporary uniqueid field from output.")

# %% 
# 10 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))

# %%
