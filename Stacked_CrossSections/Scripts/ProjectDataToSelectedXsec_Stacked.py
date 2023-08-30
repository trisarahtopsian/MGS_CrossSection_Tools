#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Project Data to All Xsec (Stacked)
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: July 2023
'''
This tool takes data that was created in one cross section in the
stacked system and makes a copy of the data on defined cross section in the
project, based on mn_et_id numbers in the cross section line file. It works
with point, line, or polygon data, and transfers all attributes to the output
feature class. 
'''

# %% 1 Import modules

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

# Define file exists function and field exists function

def FileExists(file):
    if not arcpy.Exists(file):
        printerror("!!ERROR!!: {0} does not exist.".format(os.path.basename(file)))
    #else: printit("{0} found.".format(os.path.basename(file)))
    
def FieldExists(dataset, field_name):
    if field_name in [field.name for field in arcpy.ListFields(dataset)]:
        return True
    else:
        printerror("!!ERROR!!: {0} field does not exist in {1}."
                .format(field_name, os.path.basename(dataset)))

# %% 2 Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):    
    xsln_fc = arcpy.GetParameterAsText(0) #used to list all mn_et_id values
    xs_id_field = arcpy.GetParameterAsText(1) #field that has xs numbers, usually et_id
    in_fc = arcpy.GetParameterAsText(2)  #input fc with data drawn on one cross section
    input_xs_num = arcpy.GetParameter(3) #single value from xs_id_field
    output_xs_nums = arcpy.GetParameter(4) #multiple values from xs_id_field
    out_gdb = arcpy.GetParameterAsText(5)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    xsln_fc = r'D:\Cross_Section_Programming\Project_Data_to_Xsec_Scripting\test_pipestone.gdb\xsln' #used to list all mn_et_id values
    xs_id_field = 'et_id'
    in_fc = r'D:\Cross_Section_Programming\Project_Data_to_Xsec_Scripting\test_pipestone.gdb\strat_all_dan_join' #input fc with data drawn on at least one cross section
    input_xs_num = "27" #single value from xs_id_field
    output_xs_nums = ["26"] #multiple values from xs_id_field
    out_gdb = r'D:\Cross_Section_Programming\Project_Data_to_Xsec_Scripting\test_output.gdb' #output gdb for storing output

    printit("Variables set with hard-coded parameters for testing.")


#%% Let user know that tool will delete any outputs with the same name

input_file_name = os.path.basename(in_fc)
out_fc_name = input_file_name + "_" + input_xs_num
out_fc = os.path.join(out_gdb, out_fc_name)

if arcpy.Exists(out_fc):
    printwarning("!!WARNING!! Output feature class {0} already exists. This tool will overwrite it. Cancel NOW to prevent this from happening.".format(out_fc_name))

#%% 3 Set additional parameters and data qc

vertical_exaggeration = 50
county_relief = 700
desc = arcpy.Describe(in_fc)
shape = desc.shapeType
printit("Feature geometry is {0}.".format(shape))

#check that xsln file has mn_et_id
FieldExists(xsln_fc, 'mn_et_id')

#%% Check that input xs nums match nums in the xsln file
#make a list of et_ids in xsln

full_xs_num_list = []

#empty list of output mn_et_id values
out_mn_et_id_list = []

with arcpy.da.SearchCursor(xsln_fc, [xs_id_field, 'mn_et_id']) as cursor:
    for line in cursor:
        etid = line[0]
        #grab mn_et_id value for input xs num
        if etid == input_xs_num:
            in_mn_et_id = line[1]
        #grab mn_et_id values for output xs num
        if etid in output_xs_nums:
            out_mn_et_id = line[1]
            out_mn_et_id_list.append(out_mn_et_id)
        if etid not in full_xs_num_list:
            full_xs_num_list.append(etid)

#compare input values (for both input and output xs nums) to make sure all have a matching value in the xsln file
if input_xs_num not in full_xs_num_list:
    printerror("!!ERROR!! Cross section number {0} does not exist in cross section line file. Make sure the input value you type in exactly matches the line number, including any zeroes.".format(input_xs_num))
for num in output_xs_nums:
    if num not in full_xs_num_list:
        printerror("!!ERROR!! Cross section number {0} does not exist in cross section line file. Make sure the value you type in exactly matches the line number, including any zeroes.".format(num))


#%% 4 Create temporary polygon file for attaching mn_et_id to input data. Save output as temp_fc

# maybe just make one single polygon for the input et_id, that way it's possible
#to grab the data from the input xs num without requiring that the et_id attribute 
#is already attached


#create a single poly ref based on the input mn_et_id
printit("Creating temporary polygon file in memory to clip input data")
#statewide stacked xs parameters
min_x = 160000
max_x = 775000
min_z = 0
max_z = 2300

# Create temp polygon file in memory and add mn_et_id field
polygon_file = r'memory\poly_ref_stacked'
arcpy.management.CreateFeatureclass('memory', 'poly_ref_stacked', 'POLYGON')
arcpy.management.AddField(polygon_file, 'mn_et_id', "TEXT")
arcpy.management.AddField(polygon_file, xs_id_field, "TEXT")


in_mn_et_id_int = int(in_mn_et_id)
#calculate coordinates of four corners of rectangle for this cross section
min_y = (((min_z * 0.3048) - (county_relief * in_mn_et_id_int)) * vertical_exaggeration) + 23100000
max_y = (((max_z * 0.3048) - (county_relief * in_mn_et_id_int)) * vertical_exaggeration) + 23100000
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
with arcpy.da.InsertCursor(polygon_file, ['SHAPE@', 'mn_et_id', xs_id_field]) as cursor:
    cursor.insertRow([poly_geom, in_mn_et_id, input_xs_num])

#%% 5 Join mn_et_id to in_fc using temporary polygon file

#Clip temporary fc using temporary polygon file.
#this keeps only the data that the user wants to project
temp_fc_clip = r'memory\temp_fc_clip'
arcpy.analysis.Clip(in_fc, polygon_file, temp_fc_clip)

#delete mn_et_id and xs_id_field from temporary fc, if they exist
if "mn_et_id" in [field.name for field in arcpy.ListFields(temp_fc_clip)]:
    printit("Deleting mn_et_id field from temp fc")
    arcpy.management.DeleteField(temp_fc_clip, "mn_et_id")
else:
    printit("mn_et_id field did not exist, nothing to delete.")
if xs_id_field in [field.name for field in arcpy.ListFields(temp_fc_clip)]:
    printit("Deleting {0} field from temp fc.".format(xs_id_field))
    arcpy.management.DeleteField(temp_fc_clip, xs_id_field)
else:
    printit("{0} field did not exist, nothing to delete.".format(xs_id_field))


# Join mn_et_id to in_fc using temporary polygon file
printit("Joining mn_et_id fields to output.")
temp_fc = r'memory\temp_fc'
arcpy.analysis.SpatialJoin(temp_fc_clip, polygon_file, temp_fc)

#delete temporary polygon reference file
printit("Deleting temporary polygon file.")
try: arcpy.management.Delete(polygon_file)
except: printit("Unable to delete temporary file {0}".format(polygon_file))

#delete temporary fc clip
printit("Deleting temporary file.")
try: arcpy.management.Delete(temp_fc_clip)
except: printit("Unable to delete temporary file {0}".format(temp_fc_clip))

#%% 6 Add unique ID field to temp_fc so join works correctly later
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
        
#%% 8 Make an output feature class and add fields
#name output based on input file name and original line number

arcpy.overwriteOutput = True

input_file_name = os.path.basename(in_fc)
out_fc_name = input_file_name + "_" + input_xs_num
out_fc = os.path.join(out_gdb, out_fc_name)

printit("Creating empty output feature class {0}.".format(out_fc))

arcpy.management.CreateFeatureclass(out_gdb, out_fc_name, shape)
arcpy.management.AddFields(out_fc, [[unique_id_field, 'LONG'], ['mn_et_id', 'TEXT']])

#%% 9 Point data, create copy of every point in every cross section
if shape == "Point":
    printit("Creating copies of all points and adding to output feature class.")
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
            for xs_num in out_mn_et_id_list:
                #printit("Working on mn_et_id number {0}".format(xs_num))
                xs_num_int = int(xs_num)
                new_y = (((z * 0.3048) - (county_relief * xs_num_int)) * vertical_exaggeration) + 23100000
                with arcpy.da.InsertCursor(out_fc, ['SHAPE@X', 'SHAPE@Y','mn_et_id', unique_id_field]) as insert_cursor:
                    insert_cursor.insertRow([x, new_y, xs_num, in_fc_oid])

#%% 10 Line data, create copy of every line in every cross section
if shape == "Polyline":
    printit("Creating copies of all lines and adding to output feature class.")
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
            for xs_num in out_mn_et_id_list:
                #printit("Working on mn_et_id number {0}".format(xs_num))
                #make an integer version of xs_num
                xs_num_int = int(xs_num)
                vertex_list = []
                for vertex in line[0].getPart(0):
                    x = vertex.X
                    y = vertex.Y
                    #calculate true z coordinate using mn_et_id of original line
                    z = ((y - 23100000) /(vertical_exaggeration * 0.3048) + ((county_relief * mn_et_id_int) / 0.3048))
                    #calculate new y coordinate using mn_et_id in for loop list (xs_num)
                    new_y = (((z * 0.3048) - (county_relief * xs_num_int)) * vertical_exaggeration) + 23100000
                    #create a point vertex object from original x and new y
                    point = arcpy.Point(x, new_y)
                    #add the vertex point to a list
                    vertex_list.append(point)
                #convert to geometry object
                array = arcpy.Array(vertex_list)
                line_geometry = arcpy.Polyline(array)
                #add the line to the output fc
                with arcpy.da.InsertCursor(out_fc, ['SHAPE@', 'mn_et_id', unique_id_field]) as insert_cursor:
                    insert_cursor.insertRow([line_geometry, xs_num, in_fc_oid])

#%% 11 Polygon data, create copy of every polygon in every cross section
if shape == "Polygon":
    printit("Creating copies of all polygons and adding to output feature class.")
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
            for xs_num in out_mn_et_id_list:
                #printit("Working on mn_et_id number {0}".format(xs_num))
                #make an integer version of xs_num
                xs_num_int = int(xs_num)
                vertex_list = []
                for vertex in poly[0].getPart(0):
                    x = vertex.X
                    y = vertex.Y
                    #calculate true z coordinate using mn_et_id of original polygon
                    z = ((y - 23100000) /(vertical_exaggeration * 0.3048) + ((county_relief * mn_et_id_int) / 0.3048))
                    #calculate new y coordinate using mn_et_id in for loop list (xs_num)
                    new_y = (((z * 0.3048) - (county_relief * xs_num_int)) * vertical_exaggeration) + 23100000
                    #create a point vertex object from original x and new y
                    point = arcpy.Point(x, new_y)
                    #add the vertex point to a list
                    vertex_list.append(point)
                #convert to geometry object
                array = arcpy.Array(vertex_list)
                poly_geometry = arcpy.Polygon(array)
                #add the line to the output fc
                with arcpy.da.InsertCursor(out_fc, ['SHAPE@', 'mn_et_id', unique_id_field]) as insert_cursor:
                    insert_cursor.insertRow([poly_geometry, xs_num, in_fc_oid])

#%% 12 Join input fc fields to output
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

#%% 13 Delete join field and temp file
printit("Deleting join fields from output.")

try: arcpy.management.DeleteField(out_fc, unique_id_field)
except: printit("Unable to delete unique id field from output feature class.")

printit("Deleting temporary file.")
try: arcpy.management.Delete(temp_fc)
except: printit("Unable to delete temp file stored in memory.")


#%% 14 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))