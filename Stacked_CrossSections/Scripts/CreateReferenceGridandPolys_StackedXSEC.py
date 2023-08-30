#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Create Reference Grid for Stacked Cross Section View
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: October 2022
'''
This script will create a reference grid and polygons. The grid lines can be 
used to view elevations and UTM lines in stacked cross section view. The output
line file will have "rank" and "label" fields. "Rank" field will be populated with
"major" or "minor", and "label" will be populated with the elevation or UTM value
for the line. The polygon file will have mn_et_id and et_id attributes that can
be used to join cross section number with cross section data in the stacked
system. 
'''

#%% 1 Import modules

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
    vertical_exaggeration = arcpy.GetParameter(0)
    major_vert_interval = arcpy.GetParameter(1) #feet
    minor_vert_interval = arcpy.GetParameter(2) #feet
    major_horiz_interval = arcpy.GetParameter(3) #meters
    minor_horiz_interval = arcpy.GetParameter(4) #meters
    #elevation of county
    min_z = arcpy.GetParameter(5) # minimum bedrock elevation
    max_z = arcpy.GetParameter(6) #maximum surface topo elevation
    county_relief = arcpy.GetParameter(7) #DO NOT edit this except in special cases. Controls how far apart cross sections are spaced.
    xsln_file = arcpy.GetParameterAsText(8) #mapview cross section line file
    xsln_id_field = arcpy.GetParameterAsText(9) #cross section id field, normally et_id
    output_dir = arcpy.GetParameterAsText(10)
    #out_line_fc = arcpy.GetParameterAsText(11) #output line file
    #out_poly_fc = arcpy.GetParameterAsText(12) #output polygon file
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    vertical_exaggeration = 50 #DO NOT edit this except in special cases.
    major_vert_interval = 50 #feet
    minor_vert_interval = 10 #feet
    major_horiz_interval = 1000 #meters
    minor_horiz_interval = 250 #meters
    #elevation of county
    min_z = 50 # minimum bedrock elevation
    max_z = 2500 #maximum surface topo elevation
    county_relief = 700 #DO NOT edit this except in special cases. Controls how far apart cross sections are spaced.
    xsln_file = r'D:\Cross_Section_Programming\QC_tool_testing\qc_tool_testing.gdb\xsln' #mapview cross section line file
    xsln_id_field = 'et_id' #normally et_id
    output_dir = r''
    #out_line_fc = r'D:\Cross_Section_Programming\QC_tool_testing\qc_tool_testing.gdb\grid_ref' #output line file
    #out_poly_fc = r'D:\Cross_Section_Programming\QC_tool_testing\qc_tool_testing.gdb\poly_ref'
    printit("Variables set with hard-coded parameters for testing.")

#%% 3 set min and max extents based on entire state

#x coordinates (statewide)
min_x = 160000
max_x = 775000

min_z_state = 50
max_z_state = 2300
xsln_etid_field = 'mn_et_id'

#%% 4 Create empty line feature class with elevation field

out_line_fc = os.path.join(output_dir, 'ref_grid')

#get filename of output
output_name = "ref_grid"

printit("Creating empty line file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POLYLINE')

#%% 5 add fields
label_field = "label"
arcpy.management.AddField(out_line_fc, label_field, 'LONG')

type_field = "type" # populated with "utmx" or "elevation"
arcpy.management.AddField(out_line_fc, type_field, "TEXT")

rank_field = "rank" #populated with "major" or "minor"
arcpy.management.AddField(out_line_fc, rank_field, "TEXT")

type_rank_field = "type_rank" #concatenated of above fields
arcpy.management.AddField(out_line_fc, type_rank_field, "TEXT")

arcpy.management.AddField(out_line_fc, xsln_etid_field, "TEXT")

#%% 6 Create list of elevations
major_elevations_raw = list(range(min_z_state, max_z_state, major_vert_interval))
minor_elevations_raw = list(range(min_z_state, max_z_state, minor_vert_interval))

#remove major elevations from minor list
for elevation in minor_elevations_raw:
    if elevation in major_elevations_raw:
        minor_elevations_raw.remove(elevation)

#%% 7 Create new list of elevations that are not above county max or below county min

below_min_z = int(min_z - minor_vert_interval)
above_max_z = int(max_z + minor_vert_interval)
major_elevations = []
minor_elevations = []

for elevation in major_elevations_raw:
    if elevation < below_min_z:
        continue
    elif elevation > above_max_z:
        continue
    else:
        major_elevations.append(elevation)
    
for elevation in minor_elevations_raw:
    if elevation < below_min_z:
        continue
    elif elevation > above_max_z:
        continue
    else:
        minor_elevations.append(elevation)

printit("Major elevations are {0}.".format(major_elevations))
printit("Minor elevations are {0}.".format(minor_elevations))

#%% 8 Create list of utmx values
major_utmx = list(range(min_x,max_x,major_horiz_interval))
minor_utmx = list(range(min_x,max_x,minor_horiz_interval))

#remove major utmx from minor list
for utmx in minor_utmx:
    if utmx in major_utmx:
        minor_utmx.remove(utmx)

#%% 9 Create list of mn_et_id values from xsln file       
etid_list = []

with arcpy.da.SearchCursor(xsln_file, [xsln_etid_field]) as cursor:
    for row in cursor:
        etid = row[0]
        if etid == None:
            continue
        etid_list.append(etid)

etid_list.sort()

#%% 10 Create line geometry for major elevations
printit("Creating line geometry for elevations.")
#create geometry
for etid in etid_list:
    etid_int = int(etid)
    for ele in major_elevations:
        pointlist = []
        line_type = "elevation"
        line_rank = "major"
        type_rank = line_type + "_" + line_rank
        #calculate display elevation 
        #add 23.1 million to everything to keep all of the y coordinates above zero
        ele_disp = (((ele * 0.3048) - (county_relief * etid_int)) * vertical_exaggeration) + 23100000
        #ele_disp = ((ele * 0.3048) - (county_relief * etid_int)) * vertical_exaggeration
        #define endpoints as min and max x at display elevation
        pt1 = arcpy.Point(min_x, ele_disp)
        pt2 = arcpy.Point(max_x, ele_disp)
        #add points to pointlist
        pointlist.append(pt1)
        pointlist.append(pt2)
        #turn into array and create geometry object
        array = arcpy.Array(pointlist)
        geom = arcpy.Polyline(array)
        #insert geometry into output. Store true elevation in elevation attribute.
        with arcpy.da.InsertCursor(out_line_fc, [label_field, 'SHAPE@', type_field, 
                                            rank_field, type_rank_field, xsln_etid_field]) as cursor:
            cursor.insertRow([ele, geom, line_type, line_rank, type_rank, etid])

    # Create line geometry for minor elevations
    #printit("Creating line geometry for minor elevations.")
    #create geometry
    for ele in minor_elevations:
        pointlist = []
        line_type = "elevation"
        line_rank = "minor"
        type_rank = line_type + "_" + line_rank
        #calculate display elevation 
        #ele_disp = ((ele * 0.3048) - (county_relief * etid_int)) * vertical_exaggeration
        ele_disp = (((ele * 0.3048) - (county_relief * etid_int)) * vertical_exaggeration) + 23100000
        #define endpoints as min and max x at display elevation
        pt1 = arcpy.Point(min_x, ele_disp)
        pt2 = arcpy.Point(max_x, ele_disp)
        #add points to pointlist
        pointlist.append(pt1)
        pointlist.append(pt2)
        #turn into array and create geometry object
        array = arcpy.Array(pointlist)
        geom = arcpy.Polyline(array)
        #insert geometry into output. Store true elevation in elevation attribute.
        with arcpy.da.InsertCursor(out_line_fc, [label_field, 'SHAPE@', type_field, 
                                            rank_field, type_rank_field, xsln_etid_field]) as cursor:
            cursor.insertRow([ele, geom, line_type, line_rank, type_rank, etid])


#%% 11 Create line geometry for major utmx
printit("Creating line geometry for major utmx.")
#create geometry
for utmx in major_utmx:
    pointlist = []
    line_type = "utmx"
    line_rank = "major"
    type_rank = line_type + "_" + line_rank
    #calculate display elevation 
    smallest_etid = int(etid_list[0])
    largest_etid = int(etid_list[-1])
    #ele_disp_max = ((max_z * 0.3048) - (county_relief * smallest_etid)) * vertical_exaggeration
    #ele_disp_min = ((min_z * 0.3048) - (county_relief * largest_etid)) * vertical_exaggeration
    ele_disp_max = (((max_z * 0.3048) - (county_relief * smallest_etid)) * vertical_exaggeration) + 23100000
    ele_disp_min = (((min_z * 0.3048) - (county_relief * largest_etid)) * vertical_exaggeration) + 23100000
    #define endpoints as min and max x at display elevation
    pt1 = arcpy.Point(utmx, ele_disp_max)
    pt2 = arcpy.Point(utmx, ele_disp_min)
    #add points to pointlist
    pointlist.append(pt1)
    pointlist.append(pt2)
    #turn into array and create geometry object
    array = arcpy.Array(pointlist)
    geom = arcpy.Polyline(array)
    #insert geometry into output. Store true elevation in elevation attribute.
    with arcpy.da.InsertCursor(out_line_fc, [label_field, 'SHAPE@', type_field, 
                                        rank_field, type_rank_field]) as cursor:
        cursor.insertRow([utmx, geom, line_type, line_rank, type_rank])

#%% 12 Create line geometry for minor utmx
printit("Creating line geometry for minor utmx.")
#create geometry
for utmx in minor_utmx:
    pointlist = []
    line_type = "utmx"
    line_rank = "minor"
    type_rank = line_type + "_" + line_rank
    #calculate display elevation 
    smallest_etid = int(etid_list[0])
    largest_etid = int(etid_list[-1])
    ele_disp_max = (((max_z * 0.3048) - (county_relief * smallest_etid)) * vertical_exaggeration) + 23100000
    ele_disp_min = (((min_z * 0.3048) - (county_relief * largest_etid)) * vertical_exaggeration) + 23100000
    #ele_disp_max = ((max_z * 0.3048) - (county_relief * smallest_etid)) * vertical_exaggeration
    #ele_disp_min = ((min_z * 0.3048) - (county_relief * largest_etid)) * vertical_exaggeration
    #define endpoints as min and max x at display elevation
    pt1 = arcpy.Point(utmx, ele_disp_max)
    pt2 = arcpy.Point(utmx, ele_disp_min)
    #add points to pointlist
    pointlist.append(pt1)
    pointlist.append(pt2)
    #turn into array and create geometry object
    array = arcpy.Array(pointlist)
    geom = arcpy.Polyline(array)
    #insert geometry into output. Store true elevation in elevation attribute.
    with arcpy.da.InsertCursor(out_line_fc, [label_field, 'SHAPE@', type_field, 
                                        rank_field, type_rank_field]) as cursor:
        cursor.insertRow([utmx, geom, line_type, line_rank, type_rank])

#%% 13 Create polygon reference file

out_poly_fc = os.path.join(output_dir, 'ref_poly')
#get directory where output will be saved

#get filename of output
output_name ="ref_poly"

printit("Creating empty polygon file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POLYGON')
arcpy.management.AddField(out_poly_fc, 'mn_et_id', "TEXT")


#%% 14 Create geometry for polygon file

printit("Creating polygon geometry.")
for mn_et_id in etid_list:
    #define string version of mn_et_id
    mn_et_id_int = int(mn_et_id)
    #calculate coordinates of four corners of rectangle for this cross section
    min_y = (((min_z * 0.3048) - (county_relief * mn_et_id_int)) * vertical_exaggeration) + 23100000
    max_y = (((max_z * 0.3048) - (county_relief * mn_et_id_int)) * vertical_exaggeration) + 23100000
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
    with arcpy.da.InsertCursor(out_poly_fc, ['SHAPE@', 'mn_et_id']) as cursor:
        cursor.insertRow([poly_geom, mn_et_id])

#%% 15 Join et_id field

printit("Joining cross section id field to output.")
arcpy.management.JoinField(out_poly_fc, 'mn_et_id', xsln_file, 'mn_et_id', [xsln_id_field])

#%% 16 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))