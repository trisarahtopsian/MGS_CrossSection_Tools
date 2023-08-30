#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# MGS Convert Xsec to True Y (Traditional)
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: September 2022, updated October 2022
'''
This script takes any feature class that was created in the "stacked"
cross section systems and converts the feature class to the true elevation 
coordinate system. Vertical exaggeration is created by compressing the x axis 
instead of stretching the y axis, the left extent of the cross sections will 
start at zero.
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

#%% 2 Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):
    in_fc = arcpy.GetParameterAsText(0) #feature class to convert
    in_fc_etid_field = arcpy.GetParameterAsText(1) #attribute field that contains cross section ID number
    out_fc = arcpy.GetParameterAsText(2) #output feature class
    xsln_fc = arcpy.GetParameterAsText(3) #cross section line feature class (mapview)
    xsln_etid_field = arcpy.GetParameterAsText(4) #attribute field in cross section lines that contains ID number
    in_vertical_exaggeration = int(arcpy.GetParameterAsText(5)) #vertical exaggeration of input feature class
    out_vertical_exaggeration = int(arcpy.GetParameterAsText(6)) #vertical exaggeration of output feature class
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    in_fc = r'D:\LincolnStratlines\Lincoln.gdb\test2stacked'
    in_fc_etid_field = "et_id"
    out_fc = r'D:\LincolnStratlines\Lincoln.gdb\test2traditional'
    xsln_fc = r'D:\LincolnStratlines\Lincoln.gdb\xsln'
    xsln_etid_field = 'et_id'
    in_vertical_exaggeration = 50
    out_vertical_exaggeration = 50
    printit("Variables set with hard-coded parameters for testing.")

#%% 3 Determine geometry of input feature class 

desc = arcpy.Describe(in_fc)
shape = desc.shapeType
printit("Feature geometry is {0}.".format(shape))

county_relief = 700

#%% 4 Check for mn_et_id field 

xsln_mn_id = True
in_fc_et_id = True

if 'mn_et_id' not in [field.name for field in arcpy.ListFields(xsln_fc)]:
    xsln_mn_id = False
if 'mn_et_id' not in [field.name for field in arcpy.ListFields(in_fc)]:
    in_fc_et_id = False
        
if xsln_mn_id == True and in_fc_et_id == True:
    printit("Good, cross section line and input file both have mn_et_id field.")
elif xsln_mn_id == True and in_fc_et_id == False:
    printit("Input file does not have mn_et_id. Joining from cross section line file.")
    arcpy.management.JoinField(in_fc, in_fc_etid_field, xsln_fc, xsln_etid_field, ['mn_et_id'])
elif xsln_mn_id == False and in_fc_et_id == True:
    printit("Cross section line file does not have mn_et_id field. Joining from input file.")
    arcpy.management.JoinField(xsln_fc, xsln_etid_field, in_fc, in_fc_etid_field, ['mn_et_id'])
else:
    if xsln_mn_id == False and in_fc_et_id == False:
        printerror("!!ERROR!!: cross section line file and input file do not have mn_et_id field. Add it to at least one of them and try again.")


#%% 5 Add unique ID field to input so join works correctly later

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

#%% 6 Create a blank output feature class

arcpy.env.overwriteOutput = True
filename = os.path.basename(out_fc)
filepath = os.path.dirname(out_fc)
arcpy.management.CreateFeatureclass(filepath, filename, shape)
#add etid field and unique id join field
arcpy.management.AddField(out_fc, in_fc_etid_field, 'TEXT')
arcpy.management.AddField(out_fc, unique_id_field, 'LONG')

arcpy.management.AddField(out_fc, 'mn_et_id', "TEXT")

#%% 7 Convert point data
if shape == "Point":
    printit("Converting point data to true elevation coordinates.")
    #define fields for search cursor, adding mn_et_id 

    xsln_cursor_fields = ['SHAPE@', xsln_etid_field, 'mn_et_id']
    
    with arcpy.da.SearchCursor(xsln_fc, xsln_cursor_fields) as xsln_cursor:
        for line in xsln_cursor:
            etid = line[1]
            mn_et_id = line[2]
            if mn_et_id == None:
                continue
            mn_et_id_int = int(mn_et_id)
            printit("Working on xsln {0}".format(etid))
            y_pointlist = []
            x_pointlist = []
            for vertex in line[0].getPart(0):
                # Creates a polyline geometry object from xsln_temp vertex points.
                xsln_y = vertex.Y
                xsln_x = vertex.X
                y_pointlist.append(xsln_y)
                x_pointlist.append(xsln_x)
            
            #verify that cross sections are straight east/west
            if len(y_pointlist) > 2:
                printit("Warning: xsln {0} has more than 2 vertices. It may not be straight East/West, and points will not convert correctly".format(etid))
            first_y = y_pointlist[0]
            last_y = y_pointlist[-1]
            if first_y != last_y:
                printerror("Error: xsln {0} vertices do not have the same y coordinate. Points will not plot correctly.".format(etid))
            
            #define minimum (westernmost) x UTM coordinate that will be subtracted from original x
            min_x = min(x_pointlist)
            where_clause = "{0}='{1}'".format(in_fc_etid_field, etid)
            
            #search through strat vertex points along current xsln
            with arcpy.da.SearchCursor(in_fc, ['SHAPE@X', 'SHAPE@Y', unique_id_field], where_clause) as point_cursor:
                for point in point_cursor:
                    if point == None:
                        continue
                    x = point[0]
                    y = point[1]
                    in_fc_oid = point[2]
                    #check that unique id field calculated correctly
                    if in_fc_oid == None:
                        printerror("ERROR: Unique ID field did not calculate correctly. Make sure input file has field OBJECTID or FID.")
                    
                    #define new coordinates based on input cross section system
                    #new x coordinate will be the same whether it's starting in stacked or true X system
                    new_x_raw = x - min_x
                    #convert x coordinate to feet and divide by VE
                    new_x = new_x_raw / out_vertical_exaggeration * 3.280839895

                    #calculate true z coordinate by reversing the equation below
                    #y_2d = ((vertex.Z * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration
                    new_y = ((y - 23100000) /(in_vertical_exaggeration * 0.3048) + ((county_relief * mn_et_id_int) / 0.3048))
                    
                    #make point object from new x and y coordinates
                    new_point = arcpy.Point(new_x, new_y)
                    
                    #insert point into new file
                    with arcpy.da.InsertCursor(out_fc, ['SHAPE@', in_fc_etid_field, unique_id_field, "mn_et_id"]) as output_point_cursor:
                        output_point_cursor.insertRow([new_point, etid, in_fc_oid, mn_et_id])
                            
    #update extent of new file
    printit("Finished converting point data. Updating feature class extent.")
    arcpy.management.RecalculateFeatureClassExtent(out_fc)

#%% 8 Convert line data
if shape == "Polyline":
    printit("Converting polyline data to true elevation coordinates.")
    #define fields for search cursor, adding mn_et_id if original files are in the stacked system
    xsln_cursor_fields = ['SHAPE@', xsln_etid_field, 'mn_et_id']

        
    with arcpy.da.SearchCursor(xsln_fc, xsln_cursor_fields) as xsln_cursor:
        for xsln_line in xsln_cursor:
            etid = xsln_line[1]
            mn_et_id = xsln_line[2]
            if mn_et_id == None:
                continue
            mn_et_id_int = int(mn_et_id)
            printit("Working on xsln {0}".format(etid))
            y_pointlist = []
            x_pointlist = []
            for vertex in xsln_line[0].getPart(0):
                # Creates a polyline geometry object from xsln_temp vertex points.
                xsln_y = vertex.Y
                xsln_x = vertex.X
                y_pointlist.append(xsln_y)
                x_pointlist.append(xsln_x)
            
            #verify that cross sections are straight east/west    
            if len(y_pointlist) > 2:
                printit("Warning: xsln {0} has more than 2 vertices. It may not be straight East/West, and points will not convert correctly".format(etid))
            first_y = y_pointlist[0]
            last_y = y_pointlist[-1]
            if first_y != last_y:
                printerror("Error: xsln {0} vertices do not have the same y coordinate. Points will not plot correctly.".format(etid))
            
            #define minimum (westernmost) x UTM coordinate that will be subtracted from original x
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
                    try:    
                        for vertex in line[0].getPart(0):
                            x = vertex.X
                            y = vertex.Y
                            #define new coordinates based on input cross section system
                            #new x coordinate will be the same whether it's starting in stacked or true X system
                            new_x_raw = x - min_x
                            #convert x coordinate to feet and divide by VE
                            new_x = new_x_raw/out_vertical_exaggeration*3.280839895

                            #calculate true z coordinate by reversing the equation below
                            #y_2d = ((vertex.Z * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration
                            new_y = ((y - 23100000) /(in_vertical_exaggeration * 0.3048) + ((county_relief * mn_et_id_int) / 0.3048))
                            
                            #make point object from new x and y coordinates, then turn into array and geometry object
                            point = arcpy.Point(new_x, new_y)
                            vertex_list.append(point)
                        array = arcpy.Array(vertex_list)
                        new_geometry = arcpy.Polyline(array)
                        
                        #insert geometry object into new file
                        with arcpy.da.InsertCursor(out_fc, ['SHAPE@', in_fc_etid_field, unique_id_field, "mn_et_id"]) as output_line_cursor:
                            output_line_cursor.insertRow([new_geometry, etid, in_fc_oid, mn_et_id])
                    except:
                        continue
                    
    printit("Finished converting line data. Updating feature class extent.")
    arcpy.management.RecalculateFeatureClassExtent(out_fc)

#%% 9 Convert polygon data
if shape == "Polygon":
    printit("Converting polygon data to true elevation coordinates.")
    #define fields for search cursor, adding mn_et_id

    xsln_cursor_fields = ['SHAPE@', xsln_etid_field, 'mn_et_id']

    with arcpy.da.SearchCursor(xsln_fc, xsln_cursor_fields) as xsln_cursor:
        for xsln_line in xsln_cursor:
            etid = xsln_line[1]
            mn_et_id = xsln_line[2]
            if mn_et_id == None:
                continue
            mn_et_id_int = int(mn_et_id)
            printit("Working on xsln {0}".format(etid))
            y_pointlist = []
            x_pointlist = []
            for vertex in xsln_line[0].getPart(0):
                # Creates a polyline geometry object from xsln_temp vertex points.
                xsln_y = vertex.Y
                xsln_x = vertex.X
                y_pointlist.append(xsln_y)
                x_pointlist.append(xsln_x)
            
            #verify that cross sections are straight east/west     
            if len(y_pointlist) > 2:
                printit("Warning: xsln {0} has more than 2 vertices. It may not be straight East/West, and points will not convert correctly".format(etid))
            first_y = y_pointlist[0]
            last_y = y_pointlist[-1]
            if first_y != last_y:
                printerror("Error: xsln {0} vertices do not have the same y coordinate. Points will not plot correctly.".format(etid))
            
            #define minimum (westernmost) x UTM coordinate that will be subtracted from original x
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
                    try:
                        for vertex in poly[0].getPart(0):
                            x = vertex.X
                            y = vertex.Y
                            #define new coordinates based on input cross section system
                            #new x coordinate will be the same whether it's starting in stacked or true X system
                            new_x_raw = x - min_x
                            #convert x coordinate to feet and divide by VE
                            new_x = new_x_raw/out_vertical_exaggeration*3.280839895
                            
                            #calculate true z coordinate by reversing the equation below
                            #y_2d = ((vertex.Z * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration
                            new_y = ((y - 23100000) /(in_vertical_exaggeration * 0.3048) + ((county_relief * mn_et_id_int) / 0.3048))
    
                            #make point object from new x and y coordinates, then turn into array and geometry object
                            point = arcpy.Point(new_x, new_y)
                            vertex_list.append(point)
                        array = arcpy.Array(vertex_list)
                        new_geometry = arcpy.Polygon(array)
                        
                        #insert geometry object into new file
                        with arcpy.da.InsertCursor(out_fc, ['SHAPE@', in_fc_etid_field, unique_id_field, 'mn_et_id']) as output_poly_cursor:
                            output_poly_cursor.insertRow([new_geometry, etid, in_fc_oid, mn_et_id])
                    except:
                        continue
                    
    printit("Finished converting polygon data. Updating feature class extent.")
    arcpy.management.RecalculateFeatureClassExtent(out_fc)

#%% 10 Join input fc fields to output
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

#%% 11 Delete join fields from input and output
printit("Deleting join fields from input and output.")
try:
    arcpy.management.DeleteField(in_fc, unique_id_field)
except:
    printit("Unable to delete unique id field from input feature class.")
try:
    arcpy.management.DeleteField(out_fc, unique_id_field)
except:
    printit("Unable to delete unique id field from output feature class.")

#%% 12 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))