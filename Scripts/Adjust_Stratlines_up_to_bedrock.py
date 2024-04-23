#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Adjust Stratlines up to Bedrock
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: February 2024
'''
This is a cartographic tool that will move stratlines that
were drawn below bedrock to be exactly coincident with
the bedrock profile. Suggest running this tool for final
publication, after the sand model is already complete.
The tool splits the bedrock topography profile where it 
intersects stratlines and then assigns each line segment 
a unit based on the line that was drawn directly below it.
'''

# %%
# 1 Import modules and define functions

import arcpy
import os
import numpy
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
    bedtopo_profiles = arcpy.GetParameterAsText(0)
    stratlines = arcpy.GetParameterAsText(1)
    unit_field = arcpy.GetParameterAsText(2)
    poly_ref = arcpy.GetParameterAsText(3)
    output_fc = arcpy.GetParameterAsText(4)
    temp_gdb = arcpy.GetParameterAsText(5)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    bedtopo_profiles = r'D:\GLC_Xsec_Compilation\GLC_Xsec_Compilation_Working.gdb\btopo_profiles_phase1_4'
    stratlines = r'D:\GLC_Xsec_Compilation\GLC_Xsec_Compilation_Working.gdb\stratlines_phase1_4'
    unit_field = "original_unit"
    poly_ref = r'D:\GLC_Xsec_Compilation\GLC_Xsec_Compilation_Working.gdb\poly_ref_phase1_4'
    output_fc = r'D:\GLC_Xsec_Compilation\GLC_Xsec_Compilation_Working.gdb\stratlines_br_unit_phase1_4'
    temp_gdb = r''
    printit("Variables set with hard-coded parameters for testing.")

#%% 
#3 set county relief variable (controls distance between cross sections)
#DO NOT edit this value, except in special cases
county_relief = 700
vertical_exaggeration = 50

temp_file_list = []

#%% 
# 4 Feature to line to combine bedtopo profiles and stratlines
#and split the lines at their intersections
printit("Using feature to line to split lines where they intersect.")
arcpy.env.overwriteOutput = True
feat_to_line = os.path.join(temp_gdb, "feat_to_line")
temp_file_list.append(feat_to_line)
arcpy.management.FeatureToLine([bedtopo_profiles, stratlines], feat_to_line)

#%% 
# 5 Delete "mn_et_id" and "mn_et_id_1" fields if they exist
# helps to make sure fields combine correctly
printit("Re-joining mn_et_id field from reference polygon.")
if "mn_et_id" in [field.name for field in arcpy.ListFields(feat_to_line)]:
    arcpy.management.DeleteField(feat_to_line, "mn_et_id")
if "mn_et_id_1" in [field.name for field in arcpy.ListFields(feat_to_line)]:
    arcpy.management.DeleteField(feat_to_line, "mn_et_id_1")    

#%% 
# 6 Spatial Join with poly ref to re-attach mn_et_id field

feat_to_line_join = os.path.join(temp_gdb, "feat_to_line_join")
temp_file_list.append(feat_to_line_join)
arcpy.analysis.SpatialJoin(feat_to_line, poly_ref, feat_to_line_join)

#%% 
# 7 Add unique ID field to temp fc so join works correctly later
printit("Adding temporary join field.")
unique_id_field = 'unique_id'

try:
    arcpy.management.AddField(feat_to_line_join, unique_id_field, 'LONG')
except:
    printit("Unable to add unique_id field. Field may already exist.")

if 'OBJECTID' in [field.name for field in arcpy.ListFields(feat_to_line_join)]:
    arcpy.management.CalculateField(feat_to_line_join, unique_id_field, "!OBJECTID!")
elif 'FID' in [field.name for field in arcpy.ListFields(feat_to_line_join)]:
    arcpy.management.CalculateField(feat_to_line_join, unique_id_field, "!FID!")
else: printerror("Error: input feature class does not contain OBJECTID or FID field. Conversion will not work without one of these fields.") 
      

#%% 
# 8 Draw a vertical line below every bedrock segment
printit("Creating vertical lines that will identify unit below each bedrock segment.")
arcpy.env.overwriteOutput = True
#create temp vertical line file with attributes from feat_to_line_join
vert_line_temp = os.path.join(temp_gdb, "vert_line_temp")
temp_file_list.append(vert_line_temp)
arcpy.management.CreateFeatureclass(temp_gdb, "vert_line_temp", "POLYLINE")
fields_add = [[unique_id_field, "LONG"], ["mn_et_id", "TEXT"]]
arcpy.management.AddFields(vert_line_temp, fields_add)


#Loop through all line features where unit field == ""
where_clause =  "{0}='{1}'".format(unit_field, "")
with arcpy.da.SearchCursor(feat_to_line_join, ["SHAPE@", 'mn_et_id', unique_id_field], where_clause) as cursor:
    for line in cursor:
        mn_et_id = line[1]
        mn_et_id_int = int(mn_et_id)
        unique_id = line[2]
        #make a list of all the vertices in the line
        pointlist = []
        for vertex in line[0].getPart(0):
            point = arcpy.Point(vertex.X, vertex.Y)
            pointlist.append(point)
        #vertex 1 = midpoint of the line
        vertex_num = len(pointlist)
        mid_index = int(vertex_num/2)
        midpoint = pointlist[mid_index]
        #vertex 2 = x coordinate of midpoint, lowest y coordinate on current mn_et_id
        x_base = midpoint.X
        y_base = (((50 * 0.3048) - (county_relief * mn_et_id_int)) * vertical_exaggeration) + 23100000
        basepoint = arcpy.Point(x_base, y_base)
        geom_array = arcpy.Array([midpoint, basepoint])
        geom = arcpy.Polyline(geom_array)
        with arcpy.da.InsertCursor(vert_line_temp, ["SHAPE@", 'mn_et_id', unique_id_field]) as ins_cursor:
            ins_cursor.insertRow([geom, mn_et_id, unique_id])

#%% 
# 9 Intersect vertical lines with stratlines
# it will only intersect with lines drawn below bedrock
printit("Intersecting vertical lines with stratlines.")
arcpy.env.overwriteOutput = True
intersect = os.path.join(temp_gdb, 'intersect')
temp_file_list.append(intersect)
arcpy.analysis.Intersect([vert_line_temp, feat_to_line_join], intersect, '', '', 'POINT')
intersect_sp = os.path.join(temp_gdb, 'intersect_sp')
temp_file_list.append(intersect_sp)
arcpy.management.MultipartToSinglepart(intersect, intersect_sp)

#delete unnecessary fields
arcpy.management.DeleteField(intersect_sp, [unique_id_field, unit_field, "mn_et_id"], "KEEP_FIELDS")

#%% 
# 10 Delete lines from feat_to_line_join that intersect intersect_sp
#Use original bedrock lines to create above_polys
printit("Creating above polys to clip data.")
arcpy.env.overwriteOutput = True
above_polys_temp = os.path.join(temp_gdb, "above_polys_temp")
temp_file_list.append(above_polys_temp)
arcpy.management.CreateFeatureclass(temp_gdb, "above_polys_temp", 'POLYGON')
arcpy.management.AddField(above_polys_temp, 'mn_et_id', 'TEXT')

bedtopo_profiles_sp = os.path.join(temp_gdb, "bedtopo_profiles_sp")
temp_file_list.append(bedtopo_profiles_sp)
arcpy.management.MultipartToSinglepart(bedtopo_profiles, bedtopo_profiles_sp)

with arcpy.da.SearchCursor(bedtopo_profiles_sp, ['SHAPE@', 'mn_et_id']) as cursor:
    for row in cursor:
        mn_et_id = row[1]
        mn_et_id_int = int(mn_et_id)
        polyline = row[0]
        first_pt = polyline.firstPoint
        last_pt = polyline.lastPoint
        x_list = []
        #pointlist = []
        vertex_list = []
        for vertex in row[0].getPart(0): #for each vertex in array of point objects
            x = vertex.X
            x_list.append(x)
            y = vertex.Y
            #y_list.append(y)
            point = arcpy.Point(vertex.X, vertex.Y)
            vertex_list.append(point) 

        #get first and last x coordinates from x list
        first_x = x_list[0]
        last_x = x_list[-1]
        #pointlist.append(first_pt)
        #pointlist.append(last_pt)
        
        #add top two points using first and last x, and maximum y based on mn_et_id
        max_y = (((2300 * 0.3048) - (county_relief * mn_et_id_int)) * vertical_exaggeration) + 23100000
        base_pt_1 = arcpy.Point(last_x, max_y)
        base_pt_2 = arcpy.Point(first_x, max_y)
        vertex_list.append(base_pt_1)
        vertex_list.append(base_pt_2)
        #create polygon geometry object using all vertices along the line, plus the two extra vertices
        array = arcpy.Array(vertex_list)
        poly_geometry = arcpy.Polygon(array)
        with arcpy.da.InsertCursor(above_polys_temp, ['SHAPE@']) as poly_cursor:
            poly_cursor.insertRow([poly_geometry])

#clip feat_to_line_join with above_polys
stratlines_above_bedrock = os.path.join(temp_gdb, "stratlines_above_bedrock_temp")
temp_file_list.append(stratlines_above_bedrock)
arcpy.analysis.Clip(feat_to_line_join, above_polys_temp, stratlines_above_bedrock)

#delete unnecessary fields
arcpy.management.DeleteField(stratlines_above_bedrock, [unit_field, "mn_et_id"], "KEEP_FIELDS")

#%%
# 11 remove bedrock lines (they have nothing in the unit attribute)
printit("Removing lines with blank unit attribute.")
with arcpy.da.UpdateCursor(stratlines_above_bedrock, [unit_field]) as cursor:
    for row in cursor:
        unit = row[0]
        unit_strip = unit.strip()
        if len(unit_strip) < 1:
            cursor.deleteRow()

#%% 
# 12 Delete intersect points that have blank unit field
printit("Removing intersect points with blank unit attributes.")
with arcpy.da.UpdateCursor(intersect_sp, [unit_field]) as cursor:
    for row in cursor:
        unit = row[0]
        unit_strip = unit.strip()
        if len(unit_strip) < 1:
            cursor.deleteRow()

#%% 
# 13 Make a list of unique id's that have more than one point
printit("Finding line segments with multiple intersect points and selecting a single intersect point for each bedrock segment based on which is the highest in elevation.")
unique_id_list = []
unique_id_duplicate_list = []
with arcpy.da.SearchCursor(intersect_sp, [unique_id_field]) as cursor:
    for row in cursor:
        num = row[0]
        if num in unique_id_list:
            unique_id_duplicate_list.append(num)
        unique_id_list.append(num)

#%% 
# 14 Keep only the point with the highest y coordinate per duplicate unique id

for num in unique_id_duplicate_list:
    #set starting lowest y value
    y_low = 0
    y_list = []
    where_clause = "{0}={1}".format(unique_id_field, num) 
    with arcpy.da.SearchCursor(intersect_sp, ["SHAPE@Y"], where_clause) as cursor:
        for row in cursor:
            #get y coordinate of point
            y_coord = row[0]
            y_list.append(y_coord)
    y_max = max(y_list)
    with arcpy.da.UpdateCursor(intersect_sp, ["SHAPE@Y"], where_clause) as cursor:
        for row in cursor:
            y_coord = row[0]
            if y_coord < y_max:
                cursor.deleteRow()

        
#%% 
# 15 Join unit field to original bedrock lines
printit("Joining unit field.")
arcpy.env.overwriteOutput = True
#get only bedrock lines from feat_to_line_join
temp_br_lines = os.path.join(temp_gdb, "temp_br_lines")
temp_file_list.append(temp_br_lines)

where_clause = "{0}='{1}'".format(unit_field, "")
arcpy.analysis.Select(feat_to_line_join, temp_br_lines, where_clause)

#remove unnecessary fields
arcpy.management.DeleteField(temp_br_lines, [unique_id_field, "mn_et_id"], "KEEP_FIELDS")

#join unit field
arcpy.management.JoinField(temp_br_lines, unique_id_field, intersect_sp, unique_id_field, unit_field)

#%% 
# 16 Merge temp bedrock lines
printit("Merging temp lines into single output file.")
arcpy.management.Merge([stratlines_above_bedrock, temp_br_lines], output_fc)

#%%
# 17 Delete temporary fields and files
printit("Deleting temporary files and fields.")
try: arcpy.management.DeleteField(output_fc, unique_id_field)
except: printit("Unable to delete unique id field from output.")

for file in temp_file_list:
    try: arcpy.management.Delete(file)
    except: printit("Unable to delete file {0}".format(file))

#%% 
# 18 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))
