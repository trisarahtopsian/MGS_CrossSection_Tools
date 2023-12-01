#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Check Strat Order and Line Angles (Stacked)
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: November 2022, updated November 2023
'''
This is a quality control tool used to ensure that cross section stratlines
were drawn with the correct unit order. It will also check that lines are not
drawn on top of each other at an angle. Outputs are: 1. a line file that highlights
lines that are incorrectly ordered and 2. a point file that hightlights line 
vertices where a line is drawn on top of itself. Intermediate files are saved
in memory workspace. Output will be automatically added to the active map and
symbolized.
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
    #variable = arcpy.GetParameterAsText(0)
    stratlines_original = arcpy.GetParameterAsText(0) #input fc with data drawn on one cross section
    stratline_unit_field = arcpy.GetParameterAsText(1)
    unitlist_txt = arcpy.GetParameterAsText(2)
    poly_ref = arcpy.GetParameterAsText(3)
    input_directory = arcpy.GetParameterAsText(4) #location for storing output
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    stratlines_original = r'D:\Pipestone_CrossSections\Troubleshoot_022823.gdb\all_strat' #input fc with data drawn on one cross section
    stratline_unit_field = 'unit'
    unitlist_txt = r'D:\Pipestone_CrossSections\unitlist.txt'
    poly_ref = r'D:\Pipestone_CrossSections\Troubleshoot_022823.gdb\poly_ref'
    input_directory = r'' #location for storing output
    printit("Variables set with hard-coded parameters for testing.")

#temp_dir = r'D:\Cross_Section_Programming\QC_tool_testing\scratch.gdb'
temp_dir = r'in_memory' 
#temp_dir = input_directory
#input_directory = os.path.dirname(stratlines_original)

county_relief = 700
vertical_exaggeration = 50

#%% 
# 3 Set up unit list
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

#%% 
# 4 Dissolve stratlines by unit, no multipart features

arcpy.env.overwriteOutput = True
#this ensures all stratlines are single part, reducing the number of polys that need to be made
printit("Dissolving stratlines by unit and storing as temporary file.")
stratlines_temp1 = os.path.join(temp_dir, 'stratlines_temp1')
arcpy.management.Dissolve(stratlines_original, stratlines_temp1, stratline_unit_field, '', 'SINGLE_PART')

#%% 
# 5 spatial join with mn_et_id polys
arcpy.env.overwriteOutput = True
printit("Joining mn_et_id to temp stratline file")
stratlines_temp2 = os.path.join(temp_dir, 'stratlines_temp2')
arcpy.analysis.SpatialJoin(stratlines_temp1, poly_ref, stratlines_temp2)
#arcpy.analysis.SpatialJoin(stratlines_temp1, poly_ref, stratlines_temp2, '', '', '', 'WITHIN')

#%% 
# 6 Create empty above polys for each stratline

arcpy.env.overwriteOutput = True
#create empty output polygon file and add unit field
above_polys = os.path.join(temp_dir, 'above_polys')
arcpy.management.CreateFeatureclass(temp_dir, 'above_polys', 'POLYGON')
arcpy.management.AddField(above_polys, stratline_unit_field, 'TEXT')

#%% 
# 7 Create empty angle errors point output for geometry creation

printit("Creating empty angle error point file.")
arcpy.management.CreateFeatureclass(input_directory, 'line_angle_errors', 'POINT')
point_out_fc = os.path.join(input_directory, 'line_angle_errors')

if run_location == "Pro":
# define derived output parameter. This is necessary to reference the output to apply the right symbology
    arcpy.SetParameterAsText(6, point_out_fc)


arcpy.management.AddField(point_out_fc, stratline_unit_field, 'TEXT')

#%% 
# 8 Create empty order errors line file

printit("Creating empty order error line file.")
arcpy.management.CreateFeatureclass(input_directory, 'strat_order_errors', 'POLYLINE')
line_out_fc = os.path.join(input_directory,"strat_order_errors")

if run_location == "Pro":
    # define derived output parameter. This is necessary to reference the output to apply the right symbology
    arcpy.SetParameterAsText(5, line_out_fc)


arcpy.management.AddField(line_out_fc, stratline_unit_field, 'TEXT')

#%% 
# 9 Create geometry for "above_polys" and check for angle errors
printit("Creating temporary polygons for stratlines and finding angle errors.")
with arcpy.da.SearchCursor(stratlines_temp2, ['SHAPE@', stratline_unit_field, 'mn_et_id']) as line_cursor:
    for row in line_cursor:
        unit = row[1]
        mn_et_id = row[2]
        mn_et_id_int = int(mn_et_id)
        #make empty lists for storing all vertices and x coordinates
        vertex_list = []
        x_list = []
        y_list = []
        angle_error_pointlist = []
        #make list of vertices in stratline, populate x list
        for vertex in row[0].getPart(0): #for each vertex in array of point objects
            x = vertex.X
            x_list.append(x)
            y = vertex.Y
            y_list.append(y)
            point = arcpy.Point(vertex.X, vertex.Y)
            vertex_list.append(point) 
        #get first and last x coordinates from x list
        #used to determine if line was drawn left to right or right to left
        first_x = x_list[0]
        last_x = x_list[-1]
        
        #get index of minimum y coordinate
        #this may be a list if there are multiple point at with the exact same y value
        min_index_list = numpy.where(y_list == numpy.min(y_list))[0]
        
        #if line was drawn left to right
        if first_x < last_x:
            #check the points to the LEFT of minimum
            #find the index of the point with the minimum y value. If there are
            #multiple points with the same y value, choose the SMALLEST index.
            min_index = min(min_index_list)
            #store the point object with the minimum y, calling it "previous point"
            previous_point = vertex_list[min_index]
            #loop through all of the points in the list whose indices are LESS
            #than the the minimum index, starting with the one right next to it
            for i in range(min_index - 1, -1, -1):
                current_point = vertex_list[i]
                #if the x value is GREATER than the x value of the previous point
                if current_point.X > previous_point.X:
                    printit("Appending angle error point on unit {0}. Line drawn left to right, error is left of center.".format(unit))
                    #append the point to the angle error pointlist
                    angle_error_pointlist.append(current_point)
                    #append the previous point to the angle error pointlist too
                    angle_error_pointlist.append(previous_point)
                #reset the previous point value to the current point for the next loop iteration
                previous_point = current_point
                
            #check the points to the RIGHT of minimum
            #find the index of the point with the minimum y value. If there are
            #multiple points with the same y value, choose the LARGEST index.
            min_index = max(min_index_list)
            #store the point object with the minimum y, calling it "previous point"
            previous_point = vertex_list[min_index]
            #loop through all of the points in the list whose indices are GREATER
            #than the the minimum index, starting with the one right next to it
            for i in range(min_index + 1, len(vertex_list), 1):
                current_point = vertex_list[i]
                #if the x value is LESS than the x value of the previous point
                if current_point.X < previous_point.X:
                    printit("Appending angle error point on unit {0}. Line drawn left to right, error is right of center.".format(unit))
                    #append the point to the angle error pointlist
                    angle_error_pointlist.append(current_point)
                    #append the previous point to the angle error pointlist too
                    angle_error_pointlist.append(previous_point)
                #reset the previous point value to the current point for the next loop iteration
                previous_point = current_point
            
        #if line was drawn right to left
        if first_x > last_x:
            #check the points to the RIGHT of minimum
            #find the index of the point with the minimum y value. If there are
            #multiple points with the same y value, choose the SMALLEST index.
            min_index = min(min_index_list)
            #store the point object with the minimum y, calling it "previous point"
            previous_point = vertex_list[min_index]
            #loop through all of the points in the list whose indices are LESS
            #than the the minimum index, starting with the one right next to it
            for i in range(min_index - 1, -1, -1):
                current_point = vertex_list[i]
                #if the x value is LESS than the x value of the previous point
                if current_point.X < previous_point.X:
                    printit("Appending angle error point on unit {0}. Line drawn right to left, error is right of center.".format(unit))
                    #append the point to the angle error pointlist
                    angle_error_pointlist.append(current_point)
                    #append the previous point to the angle error pointlist too
                    angle_error_pointlist.append(previous_point)
                #reset the previous point value to the current point for the next loop iteration
                previous_point = current_point
                
            #check the points to the LEFT of minimum
            #find the index of the point with the minimum y value. If there are
            #multiple points with the same y value, choose the LARGEST index.
            min_index = max(min_index_list)
            #store the point object with the minimum y, calling it "previous point"
            previous_point = vertex_list[min_index]
            #loop through all of the points in the list whose indices are GREATER
            #than the the minimum index, starting with the one right next to it
            for i in range(min_index + 1, len(vertex_list), 1):
                current_point = vertex_list[i]
                #if the x value is GREATER than the x value of the previous point
                if current_point.X > previous_point.X:
                    printit("Appending angle error point on unit {0}. Line drawn right to left, error is left of center.".format(unit))
                    #append the point to the angle error pointlist
                    angle_error_pointlist.append(current_point)
                    #append the previous point to the angle error pointlist too
                    angle_error_pointlist.append(previous_point)
                #reset the previous point value to the current point for the next loop iteration
                previous_point = current_point
        
        
        #add points into angle error file
        for error in angle_error_pointlist:
            with arcpy.da.InsertCursor(point_out_fc, ['SHAPE@', stratline_unit_field]) as point_cursor:
                point_cursor.insertRow([error, unit])
                    
        #add top two points using first and last x, and maximum y based on mn_et_id
        max_y = (((2300 * 0.3048) - (county_relief * mn_et_id_int)) * vertical_exaggeration) + 23100000
        base_pt_1 = arcpy.Point(last_x, max_y)
        base_pt_2 = arcpy.Point(first_x, max_y)
        vertex_list.append(base_pt_1)
        vertex_list.append(base_pt_2)
        #create polygon geometry object using all vertices along the line, plus the two extra vertices
        array = arcpy.Array(vertex_list)
        poly_geometry = arcpy.Polygon(array)
        #insert cursor into polygon feature class. make sure to add unit attribute
        with arcpy.da.InsertCursor(above_polys, ['SHAPE@', stratline_unit_field]) as poly_cursor:
            poly_cursor.insertRow([poly_geometry, unit])

#%% 
# 10 Make temp feature layer of stratlines. Will be used to loop thru and delete

strat_lyr = "strat_lyr"
arcpy.management.MakeFeatureLayer(stratlines_temp2, strat_lyr)

#%% 
# 11 Make temp stratline files
printit("Making temp stratline files. Time is {0}.".format(datetime.datetime.now()))

arcpy.env.overwriteOutput = True
for unit in unitlist:
    #select all lines in temp stratline feature layer where 'unit' field == unit
    where_clause = "{0}='{1}'".format(stratline_unit_field, unit)
    arcpy.management.SelectLayerByAttribute(strat_lyr, '', where_clause)
    #delete selected features
    arcpy.management.DeleteFeatures(strat_lyr)
    #export copy as "above_" + unit
    arcpy.conversion.FeatureClassToFeatureClass(strat_lyr, temp_dir, "below_" + unit)

arcpy.management.Delete(strat_lyr)

#%% 
# 12 Clip below unit files using polygon feature classes
arcpy.env.overwriteOutput = True
printit("Clipping temp stratline files. Time is {0}.".format(datetime.datetime.now()))
for unit in unitlist: 
    #Create feature layer of above polys for the unit
    where_clause = "{0}='{1}'".format(stratline_unit_field, unit)
    unit_polys = unit + "_polys"
    arcpy.management.MakeFeatureLayer(above_polys, unit_polys, where_clause)
    #find corresponding below lines file
    below_line_file = os.path.join(temp_dir, "below_" + unit)
    #clip below lines file with strat poly feature layer
    #save as unit + "_order_error"
    unit_order_error = os.path.join(temp_dir, unit + "_order_error")
    arcpy.analysis.Clip(below_line_file, unit_polys, unit_order_error)
    #multipart to singlepart
    unit_order_error_split = os.path.join(temp_dir, unit + "_order_error_split")
    arcpy.management.MultipartToSinglepart(unit_order_error, unit_order_error_split)
    #append features to output order error fc
    arcpy.management.Append(unit_order_error_split, line_out_fc, 'NO_TEST')
    arcpy.management.Delete(below_line_file)
    arcpy.management.Delete(unit_order_error)
    arcpy.management.Delete(unit_order_error_split)

#%% 
# 13 Delete tiny features

printit("Deleting unnecessary line segments.")
with arcpy.da.UpdateCursor(line_out_fc, ['Shape_Length']) as cursor:
    for row in cursor:
        length = row[0]
        if length < 1:
            cursor.deleteRow()

#%% 
# 14 Delete temporary files
try: arcpy.management.Delete(stratlines_temp1)
except: printit("Unable to delete temp file {0}".format(stratlines_temp1))

try: arcpy.management.Delete(stratlines_temp2)
except: printit("Unable to delete temp file {0}".format(stratlines_temp2))

try: arcpy.management.Delete(above_polys)
except: printit("Unable to delete temp file {0}".format(above_polys))

#%% 
# 15 Set symbology of output

line_symbol = r'J:\ArcGIS_scripts\ArcPro\MGS_CrossSectionTools\Symbology\strat_order_errors.lyrx'
point_symbol = r'J:\ArcGIS_scripts\ArcPro\MGS_CrossSectionTools\Symbology\line_angle_errors.lyrx'

try:
    arcpy.SetParameterSymbology(5, line_symbol)
    arcpy.SetParameterSymbology(6, point_symbol)
except:
    printit("Unable to apply symbology from layer. Check with GIS staff for help.")

#%% 
# 16 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))