#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Create Reference Grid for Stacked Cross Section View
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: October 2022
'''
This script will create a reference grid that can be used to view elevations and
UTM lines in stacked cross section view. The grid file will work statewide, as 
long as vertical exaggeration and "county relief" stays consistent. The output
file will have "rank" and "label" fields. "Rank" field will be populated with
"major" or "minor", and "label" will be populated with the elevation or UTM value
for the line.
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
    out_fc = arcpy.GetParameterAsText(9) #output line file
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
    xsln_file = r'D:\QuatStrat_Editing\Stacked_Testing\Statewide_xsln.gdb\xsln' #mapview cross section line file
    out_fc = r'D:\QuatStrat_Editing\Stacked_Testing\Statewide_xsln.gdb\statewide_grid_ref_abovezero' #output line file
    printit("Variables set with hard-coded parameters for testing.")


xsln_etid_field = 'mn_et_id'

#%% 3 set min and max extents based on entire state

#x coordinates (statewide)
min_x = 160000
max_x = 775000

min_z_state = 0
max_z_state = 2300


#%% 4 Create empty line feature class with elevation field

#get directory where output will be saved
output_dir = os.path.dirname(out_fc)
#get filename of output
output_name = os.path.basename(out_fc)

printit("Creating empty line file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POLYLINE')

#%% 5 add fields
label_field = "label"
arcpy.management.AddField(out_fc, label_field, 'LONG')

type_field = "type" # populated with "utmx" or "elevation"
arcpy.management.AddField(out_fc, type_field, "TEXT")

rank_field = "rank" #populated with "major" or "minor"
arcpy.management.AddField(out_fc, rank_field, "TEXT")

type_rank_field = "type_rank" #concatenated of above fields
arcpy.management.AddField(out_fc, type_rank_field, "TEXT")

arcpy.management.AddField(out_fc, xsln_etid_field, "TEXT")

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
        with arcpy.da.InsertCursor(out_fc, [label_field, 'SHAPE@', type_field, 
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
        with arcpy.da.InsertCursor(out_fc, [label_field, 'SHAPE@', type_field, 
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
    with arcpy.da.InsertCursor(out_fc, [label_field, 'SHAPE@', type_field, 
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
    with arcpy.da.InsertCursor(out_fc, [label_field, 'SHAPE@', type_field, 
                                        rank_field, type_rank_field]) as cursor:
        cursor.insertRow([utmx, geom, line_type, line_rank, type_rank])


#%% 13 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))