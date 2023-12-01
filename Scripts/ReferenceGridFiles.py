#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Cross Section Reference Grid Files
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: November 2023
'''
This script will create reference files for cross section view in stacked or
traditional display. For traditional display, it will create an elevation line
reference file and a UTMX line reference file. Elevation will be the same for all
cross sections, and UTMX lines will be attributed with a cross section ID. For
stacked display, it will create a reference grid and polygons. The reference grid
will have both elevation and UTMX lines. The polygon file will have mn_et_id 
and et_id attributes that can be used to join cross section number with cross 
section data in the stacked system. The outputline files will have "rank" 
and "label" fields. "Rank" field will be populated with "major" or "minor", and 
"label" will be populated with the elevation or UTMX value for the line. The
stacked reference line file will also have a "type" field which specifies if
the line is an elevation or UTMX line.
'''

# %% 
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
    #variable = arcpy.GetParameterAsText(0)
    xsln_file = arcpy.GetParameterAsText(0) #mapview cross section line file
    xsln_id_field = arcpy.GetParameterAsText(1) #must be text data type
    output_dir = arcpy.GetParameterAsText(2)
    min_z = int(arcpy.GetParameterAsText(3)) # minimum elevation for ref lines
    max_z = int(arcpy.GetParameterAsText(4)) #maximum elevation for ref lines
    major_vert_interval = int(arcpy.GetParameterAsText(5)) #feet
    minor_vert_interval = int(arcpy.GetParameterAsText(6)) #feet
    major_horiz_interval = int(arcpy.GetParameterAsText(7)) #meters
    minor_horiz_interval = int(arcpy.GetParameterAsText(8)) #meters
    display_system = arcpy.GetParameterAsText(9) #traditional or stacked
    #VE parameter only appears if display system is traditional
    vertical_exaggeration_in = arcpy.GetParameter(10)
    light_or_dark = arcpy.GetParameter(11)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    xsln_file = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\xsln' #mapview cross section line file
    xsln_id_field = 'et_id' #must be text data type
    output_dir = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb'
    min_z = 50 # minimum elevation for ref lines
    max_z = 2300 #maximum elevation for ref lines
    major_vert_interval = 50 #feet
    minor_vert_interval = 10 #feet
    major_horiz_interval = 1000 #meters
    minor_horiz_interval = 250 #meters
    display_system = "stacked" #traditional or stacked
    #VE parameter only appears if display system is traditional
    vertical_exaggeration_in = 50
    light_or_dark = "light" # "light" or "dark"
    printit("Variables set with hard-coded parameters for testing.")

#%% 
# 3 Set vertical exaggeration and county relief for stacked
#DO NOT edit these, except in special cases
if display_system == "stacked":
    vertical_exaggeration = 50
    county_relief = 700
    #check that mn_et_id field exists
    FieldExists(xsln_file, 'mn_et_id')
if display_system == "traditional":
    vertical_exaggeration = int(vertical_exaggeration_in)

#%% 
# 4 set min and max extents
if display_system == "traditional":
    #get maximum cross section line length from xsln file
    #set starting max length value of 0 
    max_length = 0
    #use search cursor to read length field and find the maximum length
    with arcpy.da.SearchCursor(xsln_file, ['SHAPE@LENGTH', xsln_id_field]) as cursor:
        for row in cursor:
            line = row[1]
            length = row[0]
            if length > max_length:
                max_length = length

    printit("Maximum line length is {0}.".format(max_length))
    #set min and max x for output display
    min_x_trad = 0
    #convert from meters to feet and divide by VE factor to squish coordinates
    max_x_trad = int((max_length/0.3048)/vertical_exaggeration)

#get min and max utmx extent from xsln file
xsln_desc = arcpy.Describe(xsln_file)
utmx_min_raw = int(xsln_desc.Extent.XMin)
utmx_max_raw = int(xsln_desc.Extent.XMax)

#Round above to the nearest 1000
#round down for utmx min
utmx_min_raw_sub = utmx_min_raw - major_horiz_interval
utmx_min = round(utmx_min_raw_sub, -3)
#round up for utmx max
utmx_max_raw_add = utmx_max_raw + major_horiz_interval
utmx_max = round(utmx_max_raw_add, -3)

#%% 4 Create empty line feature class with elevation field

arcpy.env.overwriteOutput = True

if display_system == "traditional":
    out_line_name = 'elevation_ref_lines' + "_" + str(vertical_exaggeration) + "x"
if display_system == "stacked":
    out_line_name = "ref_grid"

if light_or_dark == "light":
    line_symbol = r'J:\ArcGIS_scripts\ArcPro\MGS_CrossSectionTools\Symbology\reference_grid_light.lyrx'
if light_or_dark == "dark":
    line_symbol = r'J:\ArcGIS_scripts\ArcPro\MGS_CrossSectionTools\Symbology\reference_grid_dark.lyrx'

out_line_fc = os.path.join(output_dir, out_line_name)
if run_location == "Pro":
    # define derived output parameter. This is necessary to reference the output to apply the right symbology
    arcpy.SetParameterAsText(12, out_line_fc)
    arcpy.SetParameterSymbology(12, line_symbol)

#get filename of output
#output_name = 'elevation_ref_lines' + "_" + str(vertical_exaggeration) + "x"

printit("Creating empty line file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, out_line_name, 'POLYLINE')

#%% 5 add fields
label_field = "label"
arcpy.management.AddField(out_line_fc, label_field, 'LONG')

rank_field = "rank" #populated with "major" or "minor"
arcpy.management.AddField(out_line_fc, rank_field, "TEXT")

if display_system == "stacked":
    #since elevation and utmx lines are in the same file, add a type field
    type_field = "type" # populated with "utmx" or "elevation"
    arcpy.management.AddField(out_line_fc, type_field, "TEXT")
    type_rank_field = "type_rank" #concatenated of above fields
    arcpy.management.AddField(out_line_fc, type_rank_field, "TEXT")
    #mn_et_id field
    arcpy.management.AddField(out_line_fc, 'mn_et_id', "TEXT")

#%% 6 Create list of elevations
major_elevations_raw = list(range(min_z, max_z, major_vert_interval))
minor_elevations_raw = list(range(min_z, max_z, minor_vert_interval))

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

#%% 
# 9 Create list of mn_et_id values from xsln file
if display_system == "stacked":      
    mn_etid_list = []

    with arcpy.da.SearchCursor(xsln_file, ['mn_et_id']) as cursor:
        for row in cursor:
            mn_etid = row[0]
            if mn_etid == None:
                continue
            mn_etid_list.append(mn_etid)
    mn_etid_list.sort()

#create a list with only one item for the traditional display
#since elevation lines only have to be created once for traditional
#they are the same for every xsec
if display_system == "traditional":
    mn_etid_list = ["01"]

#%% 
# 10 Create elevation geometry
printit("Creating geometry for elevation lines.")
for mn_etid in mn_etid_list:
    mn_etid_int = int(mn_etid)
    for ele in major_elevations:
        pointlist = []
        line_rank = "major"
        if display_system == "stacked":
            line_type = "elevation"
            type_rank = line_type + line_rank
            #calculate display elevation for stacked based on mn_et_id
            ele_disp = (((ele * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
            #min and max width of elevation line equal to min and max extent of xsln
            min_x = utmx_min
            max_x = utmx_max
            #define fields for insert cursor below
            fields = ['SHAPE@', label_field, rank_field, type_field, type_rank_field, 'mn_et_id']
        if display_system == "traditional":
            #display elevation = true elevation in traditional display
            ele_disp = ele
            #use calculated max line length adjusted for VE for min and max width of elevation line
            min_x = min_x_trad
            max_x = max_x_trad
            #define fields for insert cursor below
            fields = ['SHAPE@', label_field, rank_field]
        #use min and max x as well as display elevations to create point objects
        pt1 = arcpy.Point(min_x, ele_disp)
        pt2 = arcpy.Point(max_x, ele_disp)
        #add points to pointlist
        pointlist.append(pt1)
        pointlist.append(pt2)
        #turn into array and create geometry object
        array = arcpy.Array(pointlist)
        geom = arcpy.Polyline(array)
        with arcpy.da.InsertCursor(out_line_fc, fields) as cursor:
            if display_system == "stacked":
                cursor.insertRow([geom, ele, line_rank, line_type, type_rank, mn_etid])
            if display_system == "traditional":
                cursor.insertRow([geom, ele, line_rank])

    #printit("Creating geometry for minor elevation lines.")
    for ele in minor_elevations:
        pointlist = []
        line_rank = "minor"
        if display_system == "stacked":
            line_type = "elevation"
            type_rank = line_type + line_rank
            #calculate display elevation for stacked based on mn_et_id
            ele_disp = (((ele * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
            #min and max width of elevation line equal to min and max extent of xsln
            min_x = utmx_min
            max_x = utmx_max
            #define fields for insert cursor below
            fields = ['SHAPE@', label_field, rank_field, type_field, type_rank_field, 'mn_et_id']
        if display_system == "traditional":
            #display elevation = true elevation in traditional display
            ele_disp = ele
            #use calculated max line length adjusted for VE for min and max width of elevation line
            min_x = min_x_trad
            max_x = max_x_trad
            #define fields for insert cursor below
            fields = ['SHAPE@', label_field, rank_field]
        #use min and max x as well as display elevations to create point objects
        pt1 = arcpy.Point(min_x, ele_disp)
        pt2 = arcpy.Point(max_x, ele_disp)
        #add points to pointlist
        pointlist.append(pt1)
        pointlist.append(pt2)
        #turn into array and create geometry object
        array = arcpy.Array(pointlist)
        geom = arcpy.Polyline(array)
        with arcpy.da.InsertCursor(out_line_fc, fields) as cursor:
            if display_system == "stacked":
                cursor.insertRow([geom, ele, line_rank, line_type, type_rank, mn_etid])
            if display_system == "traditional":
                cursor.insertRow([geom, ele, line_rank])
    
#%%
# 11 Create list of UTMX lines

major_utmx = list(range(utmx_min,utmx_max,major_horiz_interval))
minor_utmx = list(range(utmx_min,utmx_max,minor_horiz_interval))

#remove major utmx from minor list
for utmx in minor_utmx:
    if utmx in major_utmx:
        minor_utmx.remove(utmx)
     
#%%
# 12 Create UTMX lines in stacked reference grid file
if display_system == "stacked":
    printit("Creating line geometry for major utmx.")
    #create geometry
    for utmx in major_utmx:
        pointlist = []
        line_type = "utmx"
        line_rank = "major"
        type_rank = line_type + "_" + line_rank
        #calculate display elevation 
        smallest_etid = int(mn_etid_list[0])
        largest_etid = int(mn_etid_list[-1])
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

    #Create line geometry for minor utmx
    printit("Creating line geometry for minor utmx.")
    #create geometry
    for utmx in minor_utmx:
        pointlist = []
        line_type = "utmx"
        line_rank = "minor"
        type_rank = line_type + "_" + line_rank
        #calculate display elevation 
        smallest_etid = int(mn_etid_list[0])
        largest_etid = int(mn_etid_list[-1])
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

#%% 
# 13 Create empty feature classes for storing UTMX reference files
#for traditional only
if display_system == "traditional":
    #create line feature class for storing output utmx reference files
    printit("Creating x coordinate reference line feature class")
    fc_name = "xcoord_ref_lines" + "_" + str(vertical_exaggeration) + "x"

    arcpy.management.CreateFeatureclass(output_dir, fc_name, 'POLYLINE')
    out_fc = os.path.join(output_dir, fc_name)
    
    if run_location == "Pro":
        # define derived output parameter. This is necessary to reference the output to apply the right symbology
        arcpy.SetParameterAsText(13, out_fc)
        arcpy.SetParameterSymbology(13, line_symbol)
    #add fields
    fields_list = [["label", 'LONG'], ['rank', 'TEXT'], [xsln_id_field, 'TEXT']]
    arcpy.management.AddFields(out_fc, fields_list)


#%% 
# 14 Create line geometry for major utmx
#traditional only
if display_system == "traditional":
    printit("Creating line geometry for x coordinate divisions.")

    #vertical lines: same x coordinate, diferent y coordinates
    #y coordinates will be min and max elevation
    #x coordinate will be measured from start of line to specified utmx, then VE factor calculated

    #loop thru xsln one line at a time
    with arcpy.da.SearchCursor(xsln_file, ['SHAPE@', xsln_id_field]) as xsln:
        for line in xsln:
            xsec = line[1]
            printit("Working on major divisions for line {0}".format(xsec))
            pointlist = []
            for vertex in line[0].getPart(0):
                # Creates a polyline geometry object from xsln vertex points.
                # Necessary for MeasureOnLine method used later.
                point = arcpy.Point(vertex.X, vertex.Y)
                pointlist.append(point)
            array = arcpy.Array(pointlist)
            xsln_geometry = arcpy.Polyline(array)
            #create a vertical line for each major utmx
            for utmx in major_utmx:
                label = int(utmx)
                rank = "major"
                #find the point (x,y) along the xsln line that has the matching utmx coordinate
                #create geometry object for utmx line covering whole state of MN
                utmx_pointlist = []
                utmx_pt1 = arcpy.Point(utmx, 4800000)
                utmx_pt2 = arcpy.Point(utmx, 5500000)
                utmx_pointlist.append(utmx_pt1)
                utmx_pointlist.append(utmx_pt2)
                utmx_array = arcpy.Array(utmx_pointlist)
                utmx_geometry = arcpy.Polyline(utmx_array)
                #check to see if this utmx intersects the xsln
                disjoint = arcpy.Polyline.disjoint(utmx_geometry, xsln_geometry)
                if disjoint: 
                    #printit("no intersection at {0}. Continuing to next utmx".format(utmx))
                    continue
                #find intersection of utmx_geometry and xsln_geometry
                intersect_pt_mp = arcpy.Polyline.intersect(utmx_geometry, xsln_geometry, 1)
                #returns multipoint object. Should make two utmx lines if the xsln intersects the same utmx twice
                #iterate through the multipoint object
                for intersect_point in intersect_pt_mp.getPart():
                    intersect_pt = arcpy.Point(intersect_point.X, intersect_point.Y)
                    #use measure along line to find the distance to it, then calculate VE
                    x_raw = arcpy.Polyline.measureOnLine(xsln_geometry, intersect_pt)
                    #convert meters to feet and divide by VE factor
                    x = (x_raw/0.3048)/vertical_exaggeration
                    #create top and bottom points for vertical line
                    geom_pointlist = []
                    pt1 = arcpy.Point(x, min_z)
                    pt2 = arcpy.Point(x, max_z)
                    geom_pointlist.append(pt1)
                    geom_pointlist.append(pt2)
                    geom_array = arcpy.Array(geom_pointlist)
                    geom = arcpy.Polyline(geom_array)
                    #insert geometry into output file for the current line
                    with arcpy.da.InsertCursor(out_fc, ["SHAPE@", 'label', 'rank', xsln_id_field]) as insert_cursor:
                        insert_cursor.insertRow([geom, label, rank, xsec])
            #good job! Now do the minor divisions.
            printit("Working on minor divisions for line {0}".format(xsec))          
            for utmx in minor_utmx:
                label = int(utmx)
                rank = "minor"
                #find the point (x,y) along the xsln line that has the matching utmx coordinate
                #create geometry object for utmx line covering whole state of MN
                utmx_pointlist = []
                utmx_pt1 = arcpy.Point(utmx, 4800000)
                utmx_pt2 = arcpy.Point(utmx, 5500000)
                utmx_pointlist.append(utmx_pt1)
                utmx_pointlist.append(utmx_pt2)
                utmx_array = arcpy.Array(utmx_pointlist)
                utmx_geometry = arcpy.Polyline(utmx_array)
                #check to see if this utmx intersects the xsln
                disjoint = arcpy.Polyline.disjoint(utmx_geometry, xsln_geometry)
                if disjoint: 
                    #printit("no intersection at {0}. Continuing to next utmx".format(utmx))
                    continue
                #find intersection of utmx_geometry and xsln_geometry
                intersect_pt_mp = arcpy.Polyline.intersect(utmx_geometry, xsln_geometry, 1)
                #returns multipoint object. Should make two utmx lines if the xsln intersects the same utmx twice
                #iterate through the multipoint object
                for intersect_point in intersect_pt_mp.getPart():
                    intersect_pt = arcpy.Point(intersect_point.X, intersect_point.Y)
                    #use measure along line to find the distance to it, then calculate VE
                    x_raw = arcpy.Polyline.measureOnLine(xsln_geometry, intersect_pt)
                    #convert meters to feet and divide by VE factor
                    x = (x_raw/0.3048)/vertical_exaggeration
                    #create top and bottom points for vertical line
                    geom_pointlist = []
                    pt1 = arcpy.Point(x, min_z)
                    pt2 = arcpy.Point(x, max_z)
                    geom_pointlist.append(pt1)
                    geom_pointlist.append(pt2)
                    geom_array = arcpy.Array(geom_pointlist)
                    geom = arcpy.Polyline(geom_array)
                    #insert geometry into output file for the current line
                    with arcpy.da.InsertCursor(out_fc, ["SHAPE@", 'label', 'rank', xsln_id_field]) as insert_cursor:
                        insert_cursor.insertRow([geom, label, rank, xsec])
                
#%%
# 15 Create polygon reference file for stacked
if display_system == "stacked":
    printit("Creating reference polygon for stacked display.")
    out_poly_fc = os.path.join(output_dir, 'ref_poly')
    #filename of output
    output_name ="ref_poly"

    if run_location == "Pro":
        poly_symbol = r'J:\ArcGIS_scripts\ArcPro\MGS_CrossSectionTools\Symbology\ref_poly.lyrx'
        # define derived output parameter. This is necessary to reference the output to apply the right symbology
        arcpy.SetParameterAsText(14, out_poly_fc)
        arcpy.SetParameterSymbology(14, poly_symbol)

    printit("Creating empty polygon file for geometry creation.")
    arcpy.management.CreateFeatureclass(output_dir, output_name, 'POLYGON')
    arcpy.management.AddField(out_poly_fc, 'mn_et_id', "TEXT")

    printit("Creating polygon geometry.")

    for mn_et_id in mn_etid_list:
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

    printit("Joining cross section id field to output.")
    arcpy.management.JoinField(out_poly_fc, 'mn_et_id', xsln_file, 'mn_et_id', [xsln_id_field])

#%% 12 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))
# %%
