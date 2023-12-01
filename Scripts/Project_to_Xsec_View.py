#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Project to Xsec View
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: November 2023
'''
This script creates vertical lines or points in cross section view where 
mapview polygons, lines, or points intersect cross section lines. The 
output lines contain attributes from the input feature class. Output can 
be in stacked or traditional display.
'''

# %% Import modules and define functions

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

# %% Set parameters to work in testing and compiled geopocessing tool

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
    xsln = arcpy.GetParameterAsText(0)#mapview xsln file
    xsec_id_field = arcpy.GetParameterAsText(1) #et_id in xsln
    intersect_fc = arcpy.GetParameterAsText(2) #point, line, or polygon file to intersect with xsln. county boundary, faults, papg, etc.
    output_dir = arcpy.GetParameterAsText(3)
    display_system = arcpy.GetParameterAsText(4) #"stacked" or "traditional"
    output_type = arcpy.GetParameterAsText(5) #point or line
    #parameter below only appears if output type is point
    profile_2d = arcpy.GetParameterAsText(6)#2d xsec view profiles where output point should display
    #parameter below only appears if display system is traditional
    vertical_exaggeration_in = arcpy.GetParameter(7)
else:
    # hard-coded parameters used for testing
    xsln = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\xsln' #mapview xsln file
    xsec_id_field = 'et_id' #et_id in xsln
    intersect_fc = r'D:\Cross_Section_Programming\112123\script_testing\demo_data_steele.gdb\Bedrock_polys_Mz' #point, line, or polygon file to intersect with xsln. county boundary, faults, papg, etc.
    output_dir = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb'
    display_system = "stacked" #"stacked" or "traditional"
    output_type = "point" #point or line
    #parameter below only appears if output type is point
    profile_2d = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\bedrock_topo_dem_30m_profiles2d' #2d xsec view profiles where output point should display
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

#%% 
# 4 Read shape type of intersect_fc

desc = arcpy.Describe(intersect_fc)
input_shape = desc.shapeType

#%% 
# 5 Intersect 
arcpy.env.overwriteOutput = True

printit("Intersecting with xsln and creating temporary file.")

#get filename of line output
if display_system == "stacked":
    line_output_name = os.path.basename(intersect_fc)  + "_line_2d"
if display_system == "traditional":
    line_output_name = os.path.basename(intersect_fc) + "_line_2d_" + str(vertical_exaggeration) + "x"

#add temp to line name if final output will be point
#this way, if the user wants both line and point, the line 
#file won't get deleted if the tool is run twice on the same data.
if output_type == "point":
    line_output_name = line_output_name + "_temp3"

#define variable for output file
line_output_fc = os.path.join(output_dir, line_output_name)
if output_type == "line":
    #set derived output parameter for script tool
    if run_location == "Pro":
        arcpy.SetParameterAsText(8, line_output_fc)

#create name and path for temp output
output_fc_temp_multi = os.path.join(output_dir, line_output_name + "_temp_multi")

#create temporary 3D intersect file
if input_shape == "Polygon":
    arcpy.analysis.Intersect([xsln, intersect_fc], output_fc_temp_multi, 'ALL', '', 'LINE')
elif input_shape == "Polyline":
    arcpy.analysis.Intersect([xsln, intersect_fc], output_fc_temp_multi, 'ALL', '', 'POINT')
elif input_shape == "Point":
    arcpy.analysis.Intersect([xsln, intersect_fc], output_fc_temp_multi, 'ALL', '', 'POINT')
else:
    printerror("Input intersect file has invalid shape type.")

#convert multipart to singlepart
output_fc_temp1 = os.path.join(output_dir, line_output_name + "_temp1")
arcpy.management.MultipartToSinglepart(output_fc_temp_multi, output_fc_temp1)

#%% 
# 6 Dissolve
#dissolve by all fields so that there is only one line segment inside a polygon
#no multipart features

#list all attribute fields
fields_list = arcpy.ListFields(output_fc_temp1)
field_name_list = []
#remove unnecessary fields
for field in fields_list:
    if field.name == "OBJECTID":
        fields_list.remove(field)
    elif field.name == "Shape":
        fields_list.remove(field)
    elif field.name == "FID":
        fields_list.remove(field)
    elif field.name == "Shape_Length":
        fields_list.remove(field)
    else: field_name_list.append(field.name)

output_fc_temp2 = os.path.join(output_dir, line_output_name + "_temp2")
arcpy.management.Dissolve(output_fc_temp1, output_fc_temp2, field_name_list, '', "SINGLE_PART")

#%% 
# 7 Create unique id field for join later

arcpy.env.overwriteOutput = True

printit("Adding temporary join field.")
unique_id_field = 'unique_id'

try:
    arcpy.management.AddField(output_fc_temp2, unique_id_field, 'LONG')
except:
    printit("Unable to add unique_id field. Field may already exist.")

if 'OBJECTID' in [field.name for field in arcpy.ListFields(output_fc_temp2)]:
    arcpy.management.CalculateField(output_fc_temp2, unique_id_field, "!OBJECTID!")
elif 'FID' in [field.name for field in arcpy.ListFields(output_fc_temp2)]:
    arcpy.management.CalculateField(output_fc_temp2, unique_id_field, "!FID!")
else:
    printerror("Error: input feature class does not contain OBJECTID or FID field. Conversion will not work without one of these fields.") 


#%% 
# 8 Create empty line file and add fields

printit("Creating empty file for line geometry creation.")
fields = [[xsec_id_field, 'TEXT'], [unique_id_field, 'LONG']]
if display_system == "stacked":
    fields.append(["mn_et_id", 'TEXT'])

#create output for 2d line geometry
arcpy.management.CreateFeatureclass(output_dir, line_output_name, 'POLYLINE')
arcpy.management.AddFields(line_output_fc, fields)

#if output_type == "point":
    #arcpy.management.CreateFeatureclass(output_dir, output_name + "_line_temp", 'POLYLINE')
    #out_line_temp = os.path.join(output_dir, output_name + "_line_temp")
    #arcpy.management.AddFields(out_line_temp, fields)

#get shape type of temporary fc
desc = arcpy.Describe(output_fc_temp2)
temp_shape = desc.shapeType

#%% 
# 9 Convert geometry to cross section view and write to output file for stacked display

if display_system == "stacked":
    printit("Creating 2d line geometry in stacked display.")       

    #define fields for search cursor
    if temp_shape == 'Polyline':
        fields = [xsec_id_field, unique_id_field, 'mn_et_id', 'SHAPE@']
    if temp_shape == 'Point':
        fields = [xsec_id_field, unique_id_field, 'mn_et_id', 'SHAPE@X']

    with arcpy.da.SearchCursor(output_fc_temp2, fields) as cursor:
        for line in cursor:
            etid = line[0]
            #printit("etid is {0}".format(etid))
            unique_id = line[1]
            #printit("uniqueid is {0}".format(unique_id))
            mn_etid = line[2]
            #printit("mnetid is {0}".format(mn_etid))
            mn_etid_int = int(mn_etid)
            
            #set top and bottom y coordinates for every x
            y_2d_1 = (((50 * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
            y_2d_2 = (((2300 * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
            line1_pointlist = []
            if temp_shape == 'Polyline':
                line2_pointlist = []
                x_list = []
                for vertex in line[3].getPart(0):
                    #get x coordinate
                    x_2d = vertex.X
                    #make list of x coordinates in line
                    x_list.append(x_2d)
                #create 2 vertical lines, one at each endpoint of the line
                pt1 = arcpy.Point(x_list[0], y_2d_1)
                pt2 = arcpy.Point(x_list[0], y_2d_2)
                pt3 = arcpy.Point(x_list[-1], y_2d_1)
                pt4 = arcpy.Point(x_list[-1], y_2d_2)
            if temp_shape == "Point":
                #get mapview x coordinate, which is the same as stacked x coordinate
                x_mp = line[3]
                #make two points for the top and bottom of the vertical line
                pt1 = arcpy.Point(x_mp, y_2d_1)
                pt2 = arcpy.Point(x_mp, y_2d_2)
            #only one line is needed if input is point
            line1_pointlist.append(pt1)
            line1_pointlist.append(pt2)
            line1_array = arcpy.Array(line1_pointlist)
            line1_geometry = arcpy.Polyline(line1_array)
            #make a second line geometry if the input is a polyline
            if temp_shape == "Polyline":
                line2_pointlist.append(pt3)
                line2_pointlist.append(pt4)
                line2_array = arcpy.Array(line2_pointlist)
                line2_geometry = arcpy.Polyline(line2_array)
            #create geometry into output file
            #temp file if output is point, output fc if output is line
            '''
            if output_type == "point":
                with arcpy.da.InsertCursor(out_line_temp, ['SHAPE@', xsec_id_field, unique_id_field, 'mn_et_id']) as cursor2d:
                    cursor2d.insertRow([line1_geometry, etid, unique_id, mn_etid])
                    if shape == "Polyline":
                        cursor2d.insertRow([line2_geometry, etid, unique_id, mn_etid])
                        '''
            #if output_type == "line":
            with arcpy.da.InsertCursor(line_output_fc, ['SHAPE@', xsec_id_field, unique_id_field, 'mn_et_id']) as cursor2d:
                cursor2d.insertRow([line1_geometry, etid, unique_id, mn_etid])
                if temp_shape == "Polyline":
                    cursor2d.insertRow([line2_geometry, etid, unique_id, mn_etid])

#%% 
# 10 Convert geometry to cross section view and write to output file for traditional display
if display_system == "traditional":
    printit("Creating 2d line geometry in traditional display.")
    
    #set top and bottom y coordinates for every x
    #based on min and max elevations for the whole state
    y_2d_1 = 0
    y_2d_2 = 2500

    with arcpy.da.SearchCursor(xsln, ['SHAPE@', xsec_id_field]) as xsln_cursor:
        for line in xsln_cursor:
            xsec = line[1]
            #printit("Working on line {0}".format(xsec))
            pointlist = []
            for vertex in line[0].getPart(0):
                # Creates a polyline geometry object from xsln vertex points.
                # Necessary for MeasureOnLine method used later.
                point = arcpy.Point(vertex.X, vertex.Y)
                pointlist.append(point)
            array = arcpy.Array(pointlist)
            xsln_geometry = arcpy.Polyline(array)
            #search cursor to get geometry of 3D profile in this line
            if temp_shape == 'Polyline':
                fields = [unique_id_field, 'SHAPE@']
            if temp_shape == 'Point':
                fields = [unique_id_field, 'SHAPE@X', 'SHAPE@Y']
            with arcpy.da.SearchCursor(output_fc_temp2, fields, '"{0}" = \'{1}\''.format(xsec_id_field, xsec)) as cursor:
                for feature in cursor:
                    unique_id = feature[0]
                    x_list = []
                    line1_pointlist = []
                    if temp_shape == "Polyline":
                        line2_pointlist = []
                        #get geometry and convert to 2d space
                        for vertex in feature[1].getPart(0):
                            #mapview true coordinates
                            x_mp = vertex.X
                            y_mp = vertex.Y
                            xy_mp = arcpy.Point(x_mp, y_mp)    
                            #measure on line to find distance from start of xsln                    
                            x_2d_raw = arcpy.Polyline.measureOnLine(xsln_geometry, xy_mp)
                            #convert to feet and divide by vertical exaggeration to squish the x axis
                            x_2d = (x_2d_raw/0.3048)/vertical_exaggeration
                            #make list of x coordinates in line
                            x_list.append(x_2d)
                        #create 2 vertical lines, one at each endpoint of the line
                        pt1 = arcpy.Point(x_list[0], y_2d_1)
                        pt2 = arcpy.Point(x_list[0], y_2d_2)
                        pt3 = arcpy.Point(x_list[-1], y_2d_1)
                        pt4 = arcpy.Point(x_list[-1], y_2d_2)
                    if temp_shape == "Point":
                        #get mapview x coordinate, which is the same as stacked x coordinate
                        x_mp = feature[1]
                        y_mp = feature[2]
                        xy_mp = arcpy.Point(x_mp, y_mp)    
                        #measure on line to find distance from start of xsln                    
                        x_2d_raw = arcpy.Polyline.measureOnLine(xsln_geometry, xy_mp)
                        #convert to feet and divide by vertical exaggeration to squish the x axis
                        x_2d = (x_2d_raw/0.3048)/vertical_exaggeration
                        #create two points for the top and bottom of the vertical line
                        pt1 = arcpy.Point(x_2d, y_2d_1)
                        pt2 = arcpy.Point(x_2d, y_2d_2)
                    #only one line is needed if input is point
                    line1_pointlist.append(pt1)
                    line1_pointlist.append(pt2)
                    line1_array = arcpy.Array(line1_pointlist)
                    line1_geometry = arcpy.Polyline(line1_array)
                    #make a second line geometry if the input is a polyline
                    if temp_shape == "Polyline":
                        line2_pointlist.append(pt3)
                        line2_pointlist.append(pt4)
                        line2_array = arcpy.Array(line2_pointlist)
                        line2_geometry = arcpy.Polyline(line2_array)
                    '''
                    #create geometry 
                    if output_type == "point":
                        with arcpy.da.InsertCursor(out_line_temp, ['SHAPE@', xsec_id_field, unique_id_field]) as cursor2d:
                            cursor2d.insertRow([line1_geometry, xsec, unique_id])
                            if shape == "Polyline":
                                cursor2d.insertRow([line2_geometry, xsec, unique_id])
                                '''
                    #if output_type == "line":
                    with arcpy.da.InsertCursor(line_output_fc, ['SHAPE@', xsec_id_field, unique_id_field]) as cursor2d:
                        cursor2d.insertRow([line1_geometry, xsec, unique_id])
                        if temp_shape == "Polyline":
                            cursor2d.insertRow([line2_geometry, xsec, unique_id])

#%% 
# 11 Join fields

printit("Joining fields from input to output.")
# list fields in input feature class
join_fields = []
in_fc_fields_all = arcpy.ListFields(output_fc_temp2)
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
if xsec_id_field in join_fields:
    join_fields.remove(xsec_id_field)
if display_system == "stacked":
    if "mn_et_id" in join_fields:
        join_fields.remove("mn_et_id")

arcpy.management.JoinField(line_output_fc, unique_id_field, output_fc_temp2, unique_id_field, join_fields)

#%% 
# 12 Delete temporary files

printit("Deleting temporary files.")
try: arcpy.management.Delete(output_fc_temp_multi)
except: printit("Unable to delete temporary file {0}".format(output_fc_temp_multi))
try: arcpy.management.Delete(output_fc_temp2)
except: printit("Unable to delete temporary file {0}".format(output_fc_temp2))
try: arcpy.management.Delete(output_fc_temp1)
except: printit("Unable to delete temporary file {0}".format(output_fc_temp1))
#if output_type == "line":
try: arcpy.management.DeleteField(line_output_fc, unique_id_field)
except: printit("Unable to delete unique_id field.")
#if output_type == "point":
    #try: arcpy.management.DeleteField(out_line_temp, unique_id_field)
    #except: printit("Unable to delete unique_id field.")

#%%
# 13 If output type is point, intersect profiles with temp lines to create points
if output_type == "point":
    #define point output feature class
    if display_system == "stacked":
        point_output_name = os.path.basename(intersect_fc)  + "_point_2d"
    if display_system == "traditional":
        point_output_name = os.path.basename(intersect_fc) + "_point_2d_" + str(vertical_exaggeration) + "x"
    #define variable for output file and temp multipart file
    point_output_fc = os.path.join(output_dir, point_output_name)
    point_output_multi = os.path.join(output_dir, point_output_name + "_temp_multi")
    #set derived output parameter for script tool
    if run_location == "Pro":
        arcpy.SetParameterAsText(8, point_output_fc)

    #if it's in stacked display, a simple intersect will do the trick
    if display_system == "stacked":
        arcpy.analysis.Intersect([line_output_fc, profile_2d], point_output_multi, 'ALL', '', 'POINT')
        #multipart to singlepart
        #arcpy.management.MultipartToSinglepart(point_output_multi, point_output_fc)
    #if it's in traditional display, intersect will need to loop thru by xsec id
    if display_system == "traditional":
        #create temp feature dataset for intersect points
        printit("Converting lines to points.")
        arcpy.management.CreateFeatureDataset(output_dir, "temp_intersect_points")
        temp_point_fd = os.path.join(output_dir, "temp_intersect_points")
        #create list of xsec ids
        id_list = []
        with arcpy.da.SearchCursor(profile_2d, [xsec_id_field]) as cursor:
            for line in cursor:
                xsec_id = line[0]
                if xsec_id not in id_list:
                    id_list.append(xsec_id)
        #loop thru xsec id list and intersect vertical lines and profiles
        for xsec_id in id_list:
            printit("Working on line {0}".format(xsec_id))
            #define where clause for making feature layers
            where_clause = "{0}='{1}'".format(xsec_id_field, xsec_id)
            #make feature layer of vertical lines
            vert_line_layer = "temp_vert_line_" + str(xsec_id)
            arcpy.management.MakeFeatureLayer(line_output_fc, vert_line_layer, where_clause)
            #make feature layer of profile lines
            profile_line_layer = "temp_profile_line_" + str(xsec_id)
            arcpy.management.MakeFeatureLayer(profile_2d, profile_line_layer, where_clause)
            #intersect them and store in intersect point feature dataset
            temp_intersect_points = os.path.join(temp_point_fd, "temp_pt_" + str(xsec_id))
            arcpy.analysis.Intersect([vert_line_layer, profile_line_layer], temp_intersect_points, 'ALL', '', 'POINT')
            #delete temp feature layers
            arcpy.management.Delete(vert_line_layer)
            arcpy.management.Delete(profile_line_layer)
        #merge together temp point files
        arcpy.env.workspace = temp_point_fd
        temp_pt_list = arcpy.ListFeatureClasses()
        arcpy.management.Merge(temp_pt_list, point_output_multi)
    #multipart to singlepart
    arcpy.management.MultipartToSinglepart(point_output_multi, point_output_fc)
    
#%%
# 14 Delete temp point feature dataset and vertical line file
if output_type == "point":
    try:arcpy.management.Delete(line_output_fc)
    except: printit("Unable to delete temp line file {0}".format(line_output_fc))
    try:arcpy.management.Delete(point_output_multi)
    except:printit("Unable to delete temp multipoint file {0}".format(point_output_multi))
    if display_system == "traditional":
        try: arcpy.management.Delete(temp_point_fd)
        except: printit("Unable to delete temp feature dataset {0}".format(temp_point_fd))
#%% 
# 15 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))

# %%
