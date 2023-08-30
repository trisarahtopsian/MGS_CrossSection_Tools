#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Check Strat Order (Stacked)
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: November 2022
'''

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
    #variable = arcpy.GetParameterAsText(0)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    stratlines_original = r'D:\Cross_Section_Programming\QC_tool_testing\qc_tool_testing2.gdb\all_strat_vertices' #input fc with data drawn on one cross section
    stratline_unit_field = 'unit'
    unitlist_txt = r'D:\Cross_Section_Programming\QC_tool_testing\unitlist.txt'
    poly_ref = r'D:\Cross_Section_Programming\QC_tool_testing\qc_tool_testing2.gdb\poly_ref'
    printit("Variables set with hard-coded parameters for testing.")

#temp_dir = r'D:\Cross_Section_Programming\QC_tool_testing\scratch.gdb'
temp_dir = r'in_memory' 
input_directory = os.path.dirname(stratlines_original)

county_relief = 700
vertical_exaggeration = 50

#%% Set up unit list
printit("Creating unit list from text file.")
txt_file = open(unitlist_txt).readlines()
#create empty list for appending unit names
unitlist = []
#remove "\n" line break from each unit name and add to empty list
for units in txt_file:
    replace = units.replace("\n", "")
    unitlist.append(replace)
#remove extra spaces and tabs from list items
i = 0
while i < len(unitlist):
    unitlist[i] = unitlist[i].strip()
    i += 1
#remove blank list items
while '' in unitlist:
    unitlist.remove('')

#check for duplicates in unit list
def duplicatecheck(list):
    if len(set(list)) == len(list):
        printit("There are no duplicates in text file.") 
    else:
        printerror("!!ERROR!! Unit list has duplicates. Please edit to remove and then retry.") #add error
        
duplicatecheck(unitlist)

#%% Dissolve stratlines by unit, no multipart features

arcpy.env.overwriteOutput = True
#this ensures all stratlines are single part, reducing the number of polys that need to be made
printit("Dissolving stratlines by unit and storing as temporary file.")
stratlines_temp1 = os.path.join(temp_dir, 'stratlines_temp1')
arcpy.management.Dissolve(stratlines_original, stratlines_temp1, stratline_unit_field, '', 'SINGLE_PART')

#%% spatial join with mn_et_id polys
arcpy.env.overwriteOutput = True
printit("Joining mn_et_id to temp stratline file")
stratlines_temp2 = os.path.join(temp_dir, 'stratlines_temp2')
arcpy.analysis.SpatialJoin(stratlines_temp1, poly_ref, stratlines_temp2)

#%% Create below polys for each stratline

arcpy.env.overwriteOutput = True
#create empty output polygon file and add unit field
below_polys = os.path.join(temp_dir, 'below_polys')
arcpy.management.CreateFeatureclass(temp_dir, 'below_polys', 'POLYGON')
arcpy.management.AddField(below_polys, stratline_unit_field, 'TEXT')

#%% Create empty angle errors point output for geometry creation

printit("Creating empty angle error point file.")
arcpy.management.CreateFeatureclass(input_directory, 'line_angle_errors', 'POINT')
point_out_fc = os.path.join(input_directory, 'line_angle_errors')
arcpy.management.AddField(point_out_fc, stratline_unit_field, 'TEXT')

#%% Create empty order errors line file

printit("Creating empty order error line file.")
arcpy.management.CreateFeatureclass(input_directory, 'strat_order_errors', 'POLYLINE')
line_out_fc = os.path.join(input_directory,"strat_order_errors")
arcpy.management.AddField(line_out_fc, stratline_unit_field, 'TEXT')

#%% Create geometry for "below_polys" and check for angle errors
printit("Creating temporary polygons for stratlines and finding angle errors.")
with arcpy.da.SearchCursor(stratlines_temp2, ['SHAPE@', stratline_unit_field, 'mn_et_id']) as line_cursor:
    for row in line_cursor:
        unit = row[1]
        mn_et_id = row[2]
        mn_et_id_int = int(mn_et_id)
        #make empty lists for storing all vertices and x coordinates
        vertex_list = []
        x_list = []
        angle_error_pointlist = []
        #make list of vertices in stratline, populate x list
        for vertex in row[0].getPart(0): #for each vertex in array of point objects
            x = vertex.X
            x_list.append(x)
            point = arcpy.Point(vertex.X, vertex.Y)
            vertex_list.append(point) 
        #get first and last x coordinates from x list
        first_x = x_list[0]
        last_x = x_list[-1]
        
        #find vertices that are above or below first and last x
        #this captures places where stratline is drawn on top of itself
        #if line was drawn left to right
        if first_x < last_x:
            for point in vertex_list:
                if point.X < first_x:
                    angle_error_pointlist.append(point)
                if point.X > last_x:
                    angle_error_pointlist.append(point)
        #if line was drawn right to left
        if first_x > last_x:
            for point in vertex_list:
                if point.X > first_x:
                    angle_error_pointlist.append(point)
                if point.X < last_x:
                    angle_error_pointlist.append(point)
        #add points into angle error file
        for error in angle_error_pointlist:
            with arcpy.da.InsertCursor(point_out_fc, ['SHAPE@', stratline_unit_field]) as point_cursor:
                point_cursor.insertRow([error, unit])
                    
        #add bottom two points using first and last x, and minimum y based on mn_et_id
        min_y = (((50 * 0.3048) - (county_relief * mn_et_id_int)) * vertical_exaggeration) + 23100000
        base_pt_1 = arcpy.Point(last_x, min_y)
        base_pt_2 = arcpy.Point(first_x, min_y)
        vertex_list.append(base_pt_1)
        vertex_list.append(base_pt_2)
        #create polygon geometry object using all vertices along the line, plus the two extra vertices
        array = arcpy.Array(vertex_list)
        poly_geometry = arcpy.Polygon(array)
        #insert cursor into polygon feature class. make sure to add unit attribute
        with arcpy.da.InsertCursor(below_polys, ['SHAPE@', stratline_unit_field]) as poly_cursor:
            poly_cursor.insertRow([poly_geometry, unit])

#%% Make temp feature layer of stratlines. Will be used to loop thru and delete

strat_lyr = "strat_lyr"
arcpy.management.MakeFeatureLayer(stratlines_temp2, strat_lyr)

#%% Make temp stratline files
printit("Making temp stratline files. Time is {0}.".format(datetime.datetime.now()))
#reverse the order of the unitlist
unitlist.reverse()
arcpy.env.overwriteOutput = True
for unit in unitlist:
    #select all lines in temp stratline feature layer where 'unit' field == unit
    where_clause = "{0}='{1}'".format(stratline_unit_field, unit)
    arcpy.management.SelectLayerByAttribute(strat_lyr, '', where_clause)
    #delete selected features
    arcpy.management.DeleteFeatures(strat_lyr)
    #export copy as "above_" + unit
    arcpy.conversion.FeatureClassToFeatureClass(strat_lyr, temp_dir, "above_" + unit)

arcpy.management.Delete(strat_lyr)

#%% Clip above unit files using polygon feature classes
arcpy.env.overwriteOutput = True
printit("Clipping temp stratline files. Time is {0}.".format(datetime.datetime.now()))
for unit in unitlist: #order doesn't matter, so it's okay that it's still reversed
    #Create feature layer of strat polys for the unit
    where_clause = "{0}='{1}'".format(stratline_unit_field, unit)
    unit_polys = unit + "_polys"
    arcpy.management.MakeFeatureLayer(below_polys, unit_polys, where_clause)
    #find corresponding above lines file
    above_line_file = os.path.join(temp_dir, "above_" + unit)
    #clip above lines file wiht strat poly feature layer
    #save as unit + "_order_error"
    unit_order_error = os.path.join(temp_dir, unit + "_order_error")
    arcpy.analysis.Clip(above_line_file, unit_polys, unit_order_error)
    #multipart to singlepart
    unit_order_error_split = os.path.join(temp_dir, unit + "_order_error_split")
    arcpy.management.MultipartToSinglepart(unit_order_error, unit_order_error_split)
    #append features to output order error fc
    arcpy.management.Append(unit_order_error_split, line_out_fc, 'NO_TEST')

#%% Delete tiny features

printit("Deleting unnecessary line segments.")
with arcpy.da.UpdateCursor(line_out_fc, ['Shape_Length']) as cursor:
    for row in cursor:
        length = row[0]
        if length < 1:
            cursor.deleteRow()

#%% 14 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))