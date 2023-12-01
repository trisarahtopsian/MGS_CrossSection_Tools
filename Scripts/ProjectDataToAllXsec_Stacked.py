#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Project Data to All Xsec (Stacked)
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: October 2022, updated November 2023
'''
This tool takes data that was created in one or more cross sections in the
stacked system and makes a copy of the data on every cross section in the
project, based on mn_et_id numbers in the cross section line file. It works
with point, line, or polygon data, and transfers all attributes to the output
feature class. 
'''

#%% 
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
    in_fc = arcpy.GetParameterAsText(0) #input fc with data drawn on one cross section
    xsln_fc = arcpy.GetParameterAsText(1) #used to list all mn_et_id values
    out_gdb = arcpy.GetParameterAsText(2)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    in_fc = r'D:\QuatStrat_Editing\Stacked_Testing\project_to_all_xsec.gdb\poly_original_test' #input fc with data drawn on one cross section
    xsln_fc = r'D:\QuatStrat_Editing\Stacked_Testing\project_to_all_xsec.gdb\xsln' #used to list all mn_et_id values
    out_gdb = r''
    printit("Variables set with hard-coded parameters for testing.")

#%% 
# 3 Create projected data feature dataset inside editing gdb
#only create if it does not already exist
out_fd = os.path.join(out_gdb, "projected_xsec_data")
printit("Output feature dataset is {0}".format(out_fd))

if not arcpy.Exists(out_fd):
    printit("Projected data feature dataset does not exist. Creating.")
    arcpy.management.CreateFeatureDataset(out_gdb, "projected_xsec_data")

#%% 
# 4 Set additional parameters and data qc

vertical_exaggeration = 50
county_relief = 700
desc = arcpy.Describe(in_fc)
shape = desc.shapeType
printit("Feature geometry is {0}.".format(shape))

#check that xsln file has mn_et_id
FieldExists(xsln_fc, 'mn_et_id')

#%% 
# 5 Create temporary polygon file for attaching mn_et_id to input data. Save output as temp_fc

printit("Creating temporary polygon file in memory to join mn_et_id.")
#statewide stacked xs parameters
min_x = 160000
max_x = 775000
min_z = 0
max_z = 2300
county_relief = 700
vertical_exaggeration = 50

# Create temp polygon file in memory and add mn_et_id field
polygon_file = r'memory\poly_ref_stacked'
arcpy.management.CreateFeatureclass('memory', 'poly_ref_stacked', 'POLYGON')
arcpy.management.AddField(polygon_file, 'mn_et_id', "TEXT")

#make list based on statewide mn_et_id
id_list = [i for i in range(661)]

# Create polygon geometry      
for mn_et_id in id_list:
    #define string version of mn_et_id
    mn_et_id_str = str(mn_et_id)
    #calculate coordinates of four corners of rectangle for this cross section
    min_y = (((min_z * 0.3048) - (county_relief * mn_et_id)) * vertical_exaggeration) + 23100000
    max_y = (((max_z * 0.3048) - (county_relief * mn_et_id)) * vertical_exaggeration) + 23100000
    #define four corners of rectangle based on above calculations
    #min and max x coordinates are the same for all rectangles
    pt1 = arcpy.Point(min_x, max_y)
    pt2 = arcpy.Point(max_x, max_y)
    pt3 = arcpy.Point(max_x, min_y)
    pt4 = arcpy.Point(min_x, min_y)
    #create pointlist and array to define geometry object
    pointlist = [pt1, pt2, pt3, pt4]
    array = arcpy.Array(pointlist)
    poly_geom = arcpy.Polygon(array)
    #insert row into polygon file with the geometry and add mn_et_id_str as attribute
    with arcpy.da.InsertCursor(polygon_file, ['SHAPE@', 'mn_et_id']) as cursor:
        cursor.insertRow([poly_geom, mn_et_id_str])

#%% 
# 6 Join mn_et_id to in_fc using temporary polygon file
printit("Joining mn_et_id fields to output.")
temp_fc = r'memory\temp_fc'
arcpy.analysis.SpatialJoin(in_fc, polygon_file, temp_fc)

printit("Deleting temporary polygon file.")
try: arcpy.management.Delete(polygon_file)
except: printit("Unable to delete temporary file {0}".format(polygon_file))

#%% 
# 7 Add unique ID field to temp_fc so join works correctly later
printit("Adding temporary join field.")
unique_id_field = 'unique_id'

try:
    arcpy.management.AddField(temp_fc, unique_id_field, 'LONG')
except:
    printit("Unable to add unique_id field. Field may already exist.")

if 'OBJECTID' in [field.name for field in arcpy.ListFields(temp_fc)]:
    arcpy.management.CalculateField(temp_fc, unique_id_field, "!OBJECTID!")
elif 'FID' in [field.name for field in arcpy.ListFields(temp_fc)]:
    arcpy.management.CalculateField(temp_fc, unique_id_field, "!FID!")
else:
    printerror("Error: input feature class does not contain OBJECTID or FID field. Conversion will not work without one of these fields.") 

#%% 
# 8 make a list of mn_et_id values based on xsln file. Integer data type.
printit("Listing cross section numbers.")
mn_et_id_list = []
with arcpy.da.SearchCursor(xsln_fc, ["mn_et_id"]) as cursor:
    for row in cursor:
        mn_et_id = int(row[0])
        if mn_et_id not in mn_et_id_list:
            mn_et_id_list.append(mn_et_id)

#%% 
# 9 Make an output feature class and add fields
printit("Creating empty output feature class.")
#get directory where output will be saved
output_dir = os.path.dirname(out_fd)
#get filename of output

output_name = os.path.basename(in_fc + "_projected_to_all")
out_fc = os.path.join(out_fd, output_name)

#set output parameter so the output will be added to current map
if run_location == "Pro":
    arcpy.SetParameterAsText(3, out_fc)

arcpy.management.CreateFeatureclass(out_fd, output_name, shape)
arcpy.management.AddFields(out_fc, [[unique_id_field, 'LONG'], ['mn_et_id', 'TEXT']])

#%% 
# 10 Point data, create copy of every point in every cross section
if shape == "Point":
    printit("Creating copies of all points in all cross sections and adding to output feature class.")
    with arcpy.da.SearchCursor(temp_fc, ['SHAPE@X', 'SHAPE@Y','mn_et_id', unique_id_field]) as cursor:
        for point in cursor:
            #define variables for x and y coordinates
            x = point[0]
            y = point[1]
            #define string and integer type of mn_et_id
            mn_et_id = point[2]
            mn_et_id_int = int(point[2])
            #record unique id number, used for field join later
            in_fc_oid = point[3]
            if in_fc_oid == None:
                printerror("ERROR: Unique ID field did not calculate correctly. Make sure input file has field OBJECTID or FID.")
            #calculate true z coordinate
            z = ((y - 23100000) /(vertical_exaggeration * 0.3048) + ((county_relief * mn_et_id_int) / 0.3048))
            #create a copy of the point in every cross section based on mn_et_id list
            for xs_num in mn_et_id_list:
                xs_num_str = str(xs_num)
                new_y = (((z * 0.3048) - (county_relief * xs_num)) * vertical_exaggeration) + 23100000
                with arcpy.da.InsertCursor(out_fc, ['SHAPE@X', 'SHAPE@Y','mn_et_id', unique_id_field]) as insert_cursor:
                    insert_cursor.insertRow([x, new_y, xs_num_str, in_fc_oid])

#%% 
# 11 Line data, create copy of every line in every cross section
if shape == "Polyline":
    printit("Creating copies of all lines in all cross sections and adding to output feature class.")
    with arcpy.da.SearchCursor(temp_fc, ['SHAPE@','mn_et_id', unique_id_field]) as cursor:
        for line in cursor:
            mn_et_id = line[1]
            mn_et_id_int = int(line[1])
            in_fc_oid = line[2]
            #check that unique id field calculated correctly
            if in_fc_oid == None:
                printerror("ERROR: Unique ID field did not calculate correctly. Make sure input file has field OBJECTID or FID.")
            if line[0] == None:
                continue
            #create a matching line in every cross section by looping thru mn_et_id list
            for xs_num in mn_et_id_list:
                #make a text string version of xs_num
                xs_num_str = str(xs_num)
                vertex_list = []
                for vertex in line[0].getPart(0):
                    x = vertex.X
                    y = vertex.Y
                    #calculate true z coordinate using mn_et_id of original line
                    z = ((y - 23100000) /(vertical_exaggeration * 0.3048) + ((county_relief * mn_et_id_int) / 0.3048))
                    #calculate new y coordinate using mn_et_id in for loop list (xs_num)
                    new_y = (((z * 0.3048) - (county_relief * xs_num)) * vertical_exaggeration) + 23100000
                    #create a point vertex object from original x and new y
                    point = arcpy.Point(x, new_y)
                    #add the vertex point to a list
                    vertex_list.append(point)
                #convert to geometry object
                array = arcpy.Array(vertex_list)
                line_geometry = arcpy.Polyline(array)
                #add the line to the output fc
                with arcpy.da.InsertCursor(out_fc, ['SHAPE@', 'mn_et_id', unique_id_field]) as insert_cursor:
                    insert_cursor.insertRow([line_geometry, xs_num_str, in_fc_oid])

#%% 
# 12 Polygon data, create copy of every polygon in every cross section
if shape == "Polygon":
    printit("Creating copies of all polygons in all cross sections and adding to output feature class.")
    with arcpy.da.SearchCursor(temp_fc, ['SHAPE@','mn_et_id', unique_id_field]) as cursor:
        for poly in cursor:
            mn_et_id = poly[1]
            mn_et_id_int = int(poly[1])
            in_fc_oid = poly[2]
            #check that unique id field calculated correctly
            if in_fc_oid == None:
                printerror("ERROR: Unique ID field did not calculate correctly. Make sure input file has field OBJECTID or FID.")
            if poly[0] == None:
                continue
            #create a matching line in every cross section by looping thru mn_et_id list
            for xs_num in mn_et_id_list:
                #make a text string version of xs_num
                xs_num_str = str(xs_num)
                vertex_list = []
                for vertex in poly[0].getPart(0):
                    x = vertex.X
                    y = vertex.Y
                    #calculate true z coordinate using mn_et_id of original polygon
                    z = ((y - 23100000) /(vertical_exaggeration * 0.3048) + ((county_relief * mn_et_id_int) / 0.3048))
                    #calculate new y coordinate using mn_et_id in for loop list (xs_num)
                    new_y = (((z * 0.3048) - (county_relief * xs_num)) * vertical_exaggeration) + 23100000
                    #create a point vertex object from original x and new y
                    point = arcpy.Point(x, new_y)
                    #add the vertex point to a list
                    vertex_list.append(point)
                #convert to geometry object
                array = arcpy.Array(vertex_list)
                poly_geometry = arcpy.Polygon(array)
                #add the line to the output fc
                with arcpy.da.InsertCursor(out_fc, ['SHAPE@', 'mn_et_id', unique_id_field]) as insert_cursor:
                    insert_cursor.insertRow([poly_geometry, xs_num_str, in_fc_oid])

#%% 
# 13 Join input fc fields to output
printit("Joining fields from input to output.")
# list fields in input feature class
join_fields = []
in_fc_fields_all = arcpy.ListFields(temp_fc)
for field in in_fc_fields_all:
    name = field.name
    join_fields.append(name)

#remove redundant fields from list
join_fields.remove('mn_et_id')
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

arcpy.management.JoinField(out_fc, unique_id_field, temp_fc, unique_id_field, join_fields)

#%% 
# 14 Delete join field and temp file
printit("Deleting join fields from output.")

try: arcpy.management.DeleteField(out_fc, unique_id_field)
except: printit("Unable to delete unique id field from output feature class.")

printit("Deleting temporary file.")
try: arcpy.management.Delete(temp_fc)
except: printit("Unable to delete temp file stored in memory.")


#%% 
# 15 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))