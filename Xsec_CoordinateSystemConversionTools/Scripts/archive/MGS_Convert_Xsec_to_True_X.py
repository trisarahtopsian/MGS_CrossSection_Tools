#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# MGS Convert Xsec to True Y
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: June 2022
'''
This script takes any feature class that was created in the cross section 
"coordinate system" with true Y coordinates and converts the feature class
to the true X coordinate system. Vertical exaggeration is created by stretching
the y axis, and X coordinates will match mapview coordinates.
'''

# %% Import modules

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

# %% Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):
    in_fc = arcpy.GetParameterAsText(0)
    in_fc_etid_field = arcpy.GetParameterAsText(1)
    out_fc = arcpy.GetParameterAsText(2)
    xsln_fc = arcpy.GetParameterAsText(3)
    xsln_etid_field = arcpy.GetParameterAsText(4)
    vertical_exaggeration = int(arcpy.GetParameterAsText(5))
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    in_fc = r'D:\DakotaSandModel\TINmodel_091322\original_data.gdb\strat_all'
    in_fc_etid_field = "et_id"
    out_fc = r'D:\DakotaSandModel\TINmodel_091322\original_data.gdb\strat_all_trueX'
    xsln_fc = r'D:\DakotaSandModel\TINmodel_090822\SandModeling_TIN.gdb\xsln'
    xsln_etid_field = 'et_id'
    vertical_exaggeration = 50
    printit("Variables set with hard-coded parameters for testing.")

#%% Determine geometry of input feature class

desc = arcpy.Describe(in_fc)
shape = desc.shapeType
printit("Feature geometry is {0}.".format(shape))

#%% Add unique ID field to input so join works correctly later

unique_id_field = 'unique_id'

try:
    arcpy.management.AddField(in_fc, unique_id_field, 'LONG')
except:
    printit("Unable to add unique_id field. Field may already exist.")

if 'OBJECTID' in [field.name for field in arcpy.ListFields(in_fc)]:
    arcpy.management.CalculateField(in_fc, unique_id_field, "!OBJECTID!")
elif 'FID' in [field.name for field in arcpy.ListFields(in_fc)]:
    arcpy.management.CalculateField(in_fc, unique_id_field, "!FID!")
else:
    printerror("Error: input feature class does not contain OBJECTID or FID field. Conversion will not work without one of these fields.")                             

#%% Create a blank output feature class

filename = os.path.basename(out_fc)
filepath = os.path.dirname(out_fc)
arcpy.management.CreateFeatureclass(filepath, filename, shape)
#add etid field and unique id join field
arcpy.management.AddField(out_fc, in_fc_etid_field, 'TEXT')
arcpy.management.AddField(out_fc, unique_id_field, 'LONG')

#%% Convert point data
if shape == "Point":
    printit("Converting point data to true X coordinates.")
    with arcpy.da.SearchCursor(xsln_fc, ['SHAPE@', xsln_etid_field]) as xsln_cursor:
        for line in xsln_cursor:
            etid = line[1]
            printit("Working on xsln {0}".format(etid))
            y_pointlist = []
            x_pointlist = []
            for vertex in line[0].getPart(0):
                # Creates a polyline geometry object from xsln_temp vertex points.
                xsln_y = vertex.Y
                xsln_x = vertex.X
                y_pointlist.append(xsln_y)
                x_pointlist.append(xsln_x)
            if len(y_pointlist) > 2:
                printit("Warning: xsln {0} has more than 2 vertices. It may not be straight East/West, and points will not convert correctly".format(etid))
            first_y = y_pointlist[0]
            last_y = y_pointlist[-1]
            if first_y != last_y:
                printerror("Error: xsln {0} vertices do not have the same y coordinate. Points will not plot correctly.".format(etid))
            #minimum (westernmost) x UTM coordinate will be subtracted from original x.
            min_x = min(x_pointlist)
            where_clause = "{0}='{1}'".format(in_fc_etid_field, etid)
            #search through strat vertex points along current xsln
            with arcpy.da.SearchCursor(in_fc, ['SHAPE@X', 'SHAPE@Y', unique_id_field], where_clause) as point_cursor:
                for point in point_cursor:
                    if point == None:
                        continue
                    #unsquish the x axis and stretch the y axis
                    #remove VE squishing & unit conversion from x axis,
                    #then add westernmost UTM to x coordinate
                    #stretch y axis and convert to feet
                    x = point[0]
                    y = point[1]
                    in_fc_oid = point[2]
                    #check that unique id field calculated correctly
                    if in_fc_oid == None:
                        printerror("ERROR: Unique ID field did not calculate correctly. Make sure input file has field OBJECTID or FID.")
                    #unsquish the x axis and convert to meters
                    new_x_raw = x * 0.3048 * vertical_exaggeration
                    #add westernmost xsln x coordinate to raw x to put into true x coordinate
                    new_x = new_x_raw + min_x
                    #stretch the y axis and convert to feet
                    new_y = y * 0.3048 * vertical_exaggeration
                    new_point = arcpy.Point(new_x, new_y)
                    with arcpy.da.InsertCursor(out_fc, ['SHAPE@', in_fc_etid_field, unique_id_field]) as output_point_cursor:
                        output_point_cursor.insertRow([new_point, etid, in_fc_oid])

    #update extent of new file
    printit("Finished converting point data. Updating feature class extent.")
    arcpy.management.RecalculateFeatureClassExtent(out_fc)

#%% Convert line data
if shape == "Polyline":
    printit("Converting polyline data to true X coordinates.")
    with arcpy.da.SearchCursor(xsln_fc, ['SHAPE@', xsln_etid_field]) as xsln_cursor:
        for xsln_line in xsln_cursor:
            etid = xsln_line[1]
            printit("Working on xsln {0}".format(etid))
            y_pointlist = []
            x_pointlist = []
            for vertex in xsln_line[0].getPart(0):
                # Creates a polyline geometry object from xsln_temp vertex points.
                xsln_y = vertex.Y
                xsln_x = vertex.X
                y_pointlist.append(xsln_y)
                x_pointlist.append(xsln_x)
            if len(y_pointlist) > 2:
                printit("Warning: xsln {0} has more than 2 vertices. It may not be straight East/West, and points will not convert correctly".format(etid))
            first_y = y_pointlist[0]
            last_y = y_pointlist[-1]
            if first_y != last_y:
                printerror("Error: xsln {0} vertices do not have the same y coordinate. Points will not plot correctly.".format(etid))
            #minimum (westernmost) x UTM coordinate will be subtracted from original x.
            min_x = min(x_pointlist)
            where_clause = "{0}='{1}'".format(in_fc_etid_field, etid)
            #search through strat vertex points along current xsln
            with arcpy.da.SearchCursor(in_fc, ['SHAPE@', unique_id_field], where_clause) as line_cursor:
                for line in line_cursor:
                    vertex_list = []
                    if line[0] == None:
                        continue
                    in_fc_oid = line[1]
                    #check that unique id field calculated correctly
                    if in_fc_oid == None:
                        printerror("ERROR: Unique ID field did not calculate correctly. Make sure input file has field OBJECTID or FID.")
                    for vertex in line[0].getPart(0):
                        x = vertex.X
                        y = vertex.Y
                        #unsquish the x axis and convert to meters
                        new_x_raw = x * 0.3048 * vertical_exaggeration
                        #add westernmost xsln x coordinate to raw x to put into true x coordinate
                        new_x = new_x_raw + min_x
                        #stretch the y axis and convert to feet
                        new_y = y * 0.3048 * vertical_exaggeration
                        point = arcpy.Point(new_x, new_y)
                        vertex_list.append(point)
                    array = arcpy.Array(vertex_list)
                    new_geometry = arcpy.Polyline(array)
                    with arcpy.da.InsertCursor(out_fc, ['SHAPE@', in_fc_etid_field, unique_id_field]) as output_line_cursor:
                        output_line_cursor.insertRow([new_geometry, etid, in_fc_oid])
                    
    printit("Finished converting line data. Updating feature class extent.")
    arcpy.management.RecalculateFeatureClassExtent(out_fc)

#%% Convert polygon data
if shape == "Polygon":
    printit("Converting polygon data to true X coordinates.")
    with arcpy.da.SearchCursor(xsln_fc, ['SHAPE@', xsln_etid_field]) as xsln_cursor:
        for xsln_line in xsln_cursor:
            etid = xsln_line[1]
            printit("Working on xsln {0}".format(etid))
            y_pointlist = []
            x_pointlist = []
            for vertex in xsln_line[0].getPart(0):
                # Creates a polyline geometry object from xsln_temp vertex points.
                xsln_y = vertex.Y
                xsln_x = vertex.X
                y_pointlist.append(xsln_y)
                x_pointlist.append(xsln_x)
            if len(y_pointlist) > 2:
                printit("Warning: xsln {0} has more than 2 vertices. It may not be straight East/West, and points will not convert correctly".format(etid))
            first_y = y_pointlist[0]
            last_y = y_pointlist[-1]
            if first_y != last_y:
                printerror("Error: xsln {0} vertices do not have the same y coordinate. Points will not plot correctly.".format(etid))
            #minimum (westernmost) x UTM coordinate will be subtracted from original x.
            min_x = min(x_pointlist)
            where_clause = "{0}='{1}'".format(in_fc_etid_field, etid)
            #search through strat vertex points along current xsln
            with arcpy.da.SearchCursor(in_fc, ['SHAPE@', unique_id_field], where_clause) as poly_cursor:
                for poly in poly_cursor:
                    vertex_list = []
                    if poly[0] == None:
                        continue
                    in_fc_oid = poly[1]
                    #check that unique id field calculated correctly
                    if in_fc_oid == None:
                        printerror("ERROR: Unique ID field did not calculate correctly. Make sure input file has field OBJECTID or FID.")
                    for vertex in poly[0].getPart(0):
                        x = vertex.X
                        y = vertex.Y
                        #unsquish the x axis and convert to meters
                        new_x_raw = x * 0.3048 * vertical_exaggeration
                        #add westernmost xsln x coordinate to raw x to put into true x coordinate
                        new_x = new_x_raw + min_x
                        #stretch the y axis and convert to feet
                        new_y = y * 0.3048 * vertical_exaggeration
                        point = arcpy.Point(new_x, new_y)
                        vertex_list.append(point)
                    array = arcpy.Array(vertex_list)
                    new_geometry = arcpy.Polygon(array)
                    with arcpy.da.InsertCursor(out_fc, ['SHAPE@', in_fc_etid_field, unique_id_field]) as output_poly_cursor:
                        output_poly_cursor.insertRow([new_geometry, etid, in_fc_oid])
                    
    printit("Finished converting polygon data. Updating feature class extent.")
    arcpy.management.RecalculateFeatureClassExtent(out_fc)

#%% Join input fc fields to output
printit("Joining fields from input to output.")
# list fields in input feature class
join_fields = []
in_fc_fields_all = arcpy.ListFields(in_fc)
for field in in_fc_fields_all:
    name = field.name
    join_fields.append(name)

#remove redundant fields from list
if "Shape" in join_fields:
    join_fields.remove("Shape")
join_fields.remove(in_fc_etid_field)
join_fields.remove(unique_id_field)

if "OBJECTID" in join_fields:
    join_fields.remove("OBJECTID")
if "FID" in join_fields:
    join_fields.remove("FID")
if "Shape_Length" in join_fields:
    join_fields.remove("Shape_Length")
if "Shape_Area" in join_fields:
    join_fields.remove("Shape_Area")

arcpy.management.JoinField(out_fc, unique_id_field, in_fc, unique_id_field, join_fields)

#%% Delete join fields from input and output
printit("Deleting join fields from input and output.")
try:
    arcpy.management.DeleteField(in_fc, unique_id_field)
except:
    printit("Unable to delete unique id field from input feature class.")
try:
    arcpy.management.DeleteField(out_fc, unique_id_field)
except:
    printit("Unable to delete unique id field from output feature class.")
    
# %% Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))