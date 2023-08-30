#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Create Well Stick Diagrams (Stacked)
# Coded by Sarah Francis, Minnesota Geological Survey
# Created Date: March 2022, updated October 2022
'''
This script creates polyline files that are used to visualize well lithologies
along defined cross sections. Outputs are: a well stick diagram file in 3D with
true x, y, and z coordinates, well stick diagram files (line and polygon format)
in 2D cross-section space to use for cross-section creation and editing, and a
well point file in 2D stacked cross-section space. Data is retrieved from a well 
point location feature class and a corresponding stratigraphy table with lithology 
and depth information. The two tables have a one-to-many relationship.
'''

# %% 1 Import modules

import arcpy
import os
import sys
import datetime

#%% 2 Define functions

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement functions for testing and compiled geoprocessing tool

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
      
# Define field exists function
    
def FieldExists(dataset, field_name):
    if field_name in [field.name for field in arcpy.ListFields(dataset)]:
        return True
    else:
        printerror("Error: {0} field does not exist in {1}."
                .format(field_name, os.path.basename(dataset)))

# %% 3 Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):
    # input parameters for geoprocessing tool
    workspace = arcpy.GetParameterAsText(0) #output gdb
    strat_table = arcpy.GetParameterAsText(1)
    wwpt_file_orig = arcpy.GetParameterAsText(2)
    xsln_file_orig = arcpy.GetParameterAsText(3)
    xsln_etid_field = arcpy.GetParameterAsText(4)
    wwpt_etid_field = arcpy.GetParameterAsText(5)
    strat_wellid_field = arcpy.GetParameterAsText(6)
    wwpt_wellid_field = arcpy.GetParameterAsText(7)
    xsln_spacing = int(arcpy.GetParameterAsText(8)) #used to calculate percent distance from xsln
    create_2d_points = arcpy.GetParameter(9)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    workspace = r'D:\DakotaSandModel\DakotaCrossSections\CrossSections.gdb' #output gdb
    strat_table = r'D:\DakotaSandModel\DakotaCrossSections\CrossSections.gdb\strat_qdi' #gdb table with stratigraphy info. Multiple records per well.
    wwpt_file_orig = r'D:\DakotaSandModel\DakotaCrossSections\CrossSections.gdb\qdipt' #point feature class with well location information
    xsln_file_orig = r'D:\DakotaSandModel\TINmodel_110122\SandModeling_TIN.gdb\xsln' #mapview cross section line feature class
    xsln_etid_field = 'et_id' #cross section ID field in cross section file
    wwpt_etid_field = 'et_id' #cross section ID field in well point file
    strat_wellid_field = 'relateid' #well ID number field in strat table
    wwpt_wellid_field = 'relateid' #well ID number field in well point file
    xsln_spacing = int(1000) #spacing between xsln in map view
    create_2d_points = False #True to create surface points at every well location
    printit("Variables set with hard-coded parameters for testing.")

#%% 4 set county relief and vertical exaggeration variables 
# county relief controls distance between cross sections
#DO NOT edit these values, except in special cases
county_relief = 700
vertical_exaggeration = int(50)

#%% 5  Set 3d spatial reference based on xsln file

spatialref = arcpy.Describe(xsln_file_orig).spatialReference
if spatialref.name == "Unknown":
    printerror("{0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(xsln_file_orig)))
else:
    printit("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(xsln_file_orig)))

#%% 6 Add mn_et_id field to wwpt file if it doesn't exist
#strat table does not need et_id or mn_et_id for this code to work.
#it will get these numbers and assign them based on matching well point.
#therefore, well point file must have mn_et_id
#this code will add mn_et_id to well points if it doesn't have it already

#first, check that xsln file has mn_et_id
FieldExists(xsln_file_orig, 'mn_et_id')

#check that well point file has mn_et_id and join the field if it doesn't
if 'mn_et_id' in [field.name for field in arcpy.ListFields(wwpt_file_orig)]:
    printit("Good, mn_et_id field already exists in well point file.")
else:
    printit("Adding mn_et_id field to well point file based on et_id in xsln file.")
    arcpy.management.JoinField(wwpt_file_orig, wwpt_etid_field, xsln_file_orig, xsln_etid_field, ['mn_et_id'])

# %% 7 Data QC

#determine if input cross section lines have multipart features
multipart = False
with arcpy.da.SearchCursor(xsln_file_orig, ["SHAPE@"]) as cursor:
    for row in cursor:
        if row[0].isMultipart:
            multipart = True
            break
if multipart:
    printerror("Warning: cross section file contains multipart features. Continuing may result in errors.")

#determine if  input tables have the correct matching fields (function defined above)
printit("Checking that data tables have correct fields.")
FieldExists(strat_table, "elev_top")
FieldExists(strat_table, "elev_bot")
FieldExists(strat_table, "OBJECTID")
FieldExists(wwpt_file_orig, "elevation")

# Count number of rows in input parameters
strat_count_result = arcpy.management.GetCount(strat_table)
strat_count = int(strat_count_result[0])
if strat_count == 0:
    printerror("Warning: stratigraphy table is empty. Tool will not run correctly.")

wwpt_count_result = arcpy.management.GetCount(wwpt_file_orig)
wwpt_count = int(wwpt_count_result[0])
if wwpt_count == 0:
    printerror("Warning: well location point file is empty. Tool will not run correctly.")

xsln_count_result = arcpy.management.GetCount(xsln_file_orig)
xsln_count = int(xsln_count_result[0])
if xsln_count == 0:
    printerror("Warning: cross section line file is empty. Tool will not run correctly.")

#%% 8 Check that strat table, well point file, and cross section file match

printit("Checking that stratigraphy table, well point file, and cross section line file all match.")

# Create empty lists to store well IDs and et_ids in each file
strat_wellid_list = []
wwpt_wellid_list = []
wwpt_etid_list = []
xsln_etid_list = []

# Populate strat table wellid and et_id lists

#with arcpy.da.SearchCursor(strat_table, [strat_wellid_field, strat_etid_field]) as strat_records:
with arcpy.da.SearchCursor(strat_table, [strat_wellid_field]) as strat_records:
    for row in strat_records:
        wellid = row[0]
        if wellid not in strat_wellid_list:
            strat_wellid_list.append(wellid)

# Populate well point file wellid and et_id lists
with arcpy.da.SearchCursor(wwpt_file_orig, [wwpt_wellid_field, wwpt_etid_field]) as wwpt_records:
    for row in wwpt_records:
        wellid = row[0]
        etid = row[1]
        if wellid not in wwpt_wellid_list:
            wwpt_wellid_list.append(wellid)
        if etid not in wwpt_etid_list:
            wwpt_etid_list.append(etid)

# Populate cross section line et_id list            
with arcpy.da.SearchCursor(xsln_file_orig, [xsln_etid_field]) as xsln_records:
    for line in xsln_records:
        etid = line[0]
        if etid not in xsln_etid_list:
            xsln_etid_list.append(etid)

# Print warning if strat record(s) have no matching well point(s).
listprint = []
for wellid in strat_wellid_list:
    if wellid not in wwpt_wellid_list:
        listprint.append(wellid)
listprint_len = len(listprint)
if listprint_len > 0:
    printit("Warning: {0} stratigraphy records have no matching well points. Well stick diagrams will not draw for these records.".format(listprint_len))

# Print warning if well point(s) have no matching stratigrapy records.
listprint = []
for wellid in wwpt_wellid_list:
    if wellid not in strat_wellid_list:
        listprint.append(wellid)
listprint_len = len(listprint)
if listprint_len > 0:
    printit("Warning: {0} well points have no matching stratigraphy records. Well stick diagrams will not draw for these wells.".format(listprint_len))

# Check that et_id fields in well point file have matching xsln et_id
listprint = []      
for etid in wwpt_etid_list:
    if etid not in xsln_etid_list:
        listprint.append(etid)
listprint_len = len(listprint)
if listprint_len > 0:
        printit("Warning: there are {0} et_id's in well point file that do not match any et_id's in cross section line file. Well point et_id's are: {1}".format(listprint_len, listprint))

# Check that all cross section lines have matching well points
listprint = []      
for etid in xsln_etid_list:
    if etid not in wwpt_etid_list:
        listprint.append(etid)
listprint_len = len(listprint)
if listprint_len > 0:
        printit("Warning: there are {0} cross section lines that do not have any associated well points. Cross section et_id's are: {1}".format(listprint_len, listprint))
    
# Check that well id in strat and well point files have the same data type
if type(strat_wellid_list[0]) != type(wwpt_wellid_list[0]):
    printerror("Warning: strat table and well point file have mismatched data types in the well id field. Wells and stratigraphy records will not be matched correctly.")

# Set boolean variable that stores data type of well id field (needed for defining Where Clause later)
wellid_is_numeric = True
if type(strat_wellid_list[0]) == str:
    wellid_is_numeric = False
    
# %% 9 List fields that are used in 3d line, 2d line, and 2d point

# set field type of well id so code correctly handles text vs. numeric
if wellid_is_numeric:
    well_id_field_type = 'DOUBLE'
elif not wellid_is_numeric:
    well_id_field_type = 'TEXT'

# fields needed in all output files    
fields_base = [[strat_wellid_field, well_id_field_type], ['et_id', 'TEXT', '', 3], 
               ['mn_et_id', 'TEXT', '', 5], ['x_coord', 'DOUBLE'], ['y_coord', 'DOUBLE']]

# fields needed in polyline/polygon output files (both 2d and 3d versions)
fields_strat = [['strat_oid', 'DOUBLE'], ['z_top', 'DOUBLE'], ['z_bot', 'DOUBLE']] 

# fields only needed in 2d files (point, polyline, and polygon)
fields_2d = [['distance', 'FLOAT'], ['pct_dist', 'FLOAT']]

# fields needed only in 2d point file
fields_2d_point = [['elevation', 'FLOAT']]

# %% 10 Create empty 3d polyline file

arcpy.env.overwriteOutput = True
#create polyline shapefile with 3d geometry enabled, spatial ref matches xsln file
printit("Creating empty 3d polyline file for well stick diagrams.")
arcpy.management.CreateFeatureclass(workspace, "lixpys_3d", "POLYLINE", '',
                                    'DISABLED', 'ENABLED', spatialref)

#set polyline shapefile filepath variable
polylinefile_3d = os.path.join(workspace, "lixpys_3d")

#define field names and types: base fields and stratigraphy fields
polyline_3d_fields = fields_base + fields_strat

# Add fields to 3D polyline file
arcpy.management.AddFields(polylinefile_3d, polyline_3d_fields)

# %% 11 Create empty 2d polyline file

arcpy.env.overwriteOutput = True
#create polyline shapefile, spatial ref defined above
printit("Creating empty 2d polyline file for well stick diagrams.")
arcpy.management.CreateFeatureclass(workspace, "lixpys_2d_line", "POLYLINE", '',
                                    'DISABLED', 'DISABLED')

#set polyline shapefile filepath variable
polylinefile_2d = os.path.join(workspace, "lixpys_2d_line")

#define field names and types: base fields, strat fields, and 2d fields
polyline_2d_fields = fields_base + fields_strat + fields_2d

#Add fields to 2D polyline file
arcpy.management.AddFields(polylinefile_2d, polyline_2d_fields)

# %% 12 Create empty 2d point file, to show well locations in cross section space

arcpy.env.overwriteOutput = True
if create_2d_points == True:
    #create point shapefile
    printit("Creating empty 2d point file to show well locations.")
    arcpy.management.CreateFeatureclass(workspace, "wwpt_2d_xsecview", "POINT", '',
                                        'DISABLED', 'DISABLED')
    
    #set point shapefile filepath variable
    pointfile = os.path.join(workspace, "wwpt_2d_xsecview")
    
    #define field names and types: base fields, 2d fields, and 2d point fields
    point_2d_fields = fields_base + fields_2d + fields_2d_point
    
    #Add fields to 2D point file
    arcpy.management.AddFields(pointfile, point_2d_fields)

#%% 13 Create feature dataset to store wwpt files by xs
# wwpt files need to be split by xs to ensure that each well is referencing the correct xsln
arcpy.env.overwriteOutput = True
printit("Creating feature dataset for temporary file storage and copying well point file.")
arcpy.management.CreateFeatureDataset(workspace, "wwpt_by_xs")
wwpt_by_xs_fd = os.path.join(workspace, "wwpt_by_xs")

# Make a temporary copy of the wwpt file and put it in the new feature dataset
# Code below will grab selected features from this temporary wwpt file.
# The temporary file will be deleted when geometry is completed.
wwpt_file_temp = os.path.join(wwpt_by_xs_fd, "wwpt_temp")
arcpy.management.CopyFeatures(wwpt_file_orig, wwpt_file_temp)

#%% 14 Add fields to temporary wwpt point feature class
# These fields will be populated by near analysis and measure on line functions

wwpt_fields = [["NEAR_FID", "LONG"], ["NEAR_DIST", "DOUBLE"], ["NEAR_X", "DOUBLE"], 
               ["NEAR_Y", "DOUBLE"]]

for newfield in wwpt_fields:
    if newfield[0] in [field.name for field in arcpy.ListFields(wwpt_file_temp)]:
        printit("{0} field already exists in well point file. Tool will overwrite data in this field.".format(newfield[0]))
    else:
        printit("Adding {0} field to well point file.".format(newfield[0]))
        arcpy.management.AddField(wwpt_file_temp, newfield[0], newfield[1])

#%% 15 Create a temporary xsln file and extend the lines equal to xsln spacing
    # The extended xsln file is used to define 2d x coordinates of wells
    # to ensure that wells beyond the xsln plot correctly
# Create temporary xsln file (empty for now)
xsln_temp = os.path.join(workspace, "xsln_temp")
arcpy.management.CreateFeatureclass(workspace, "xsln_temp", "POLYLINE", '', 'DISABLED', 'DISABLED', spatialref)

# add et_id and mn_et_id fields to temp xsln file
arcpy.management.AddField(xsln_temp, xsln_etid_field, "TEXT")
arcpy.management.AddField(xsln_temp, 'mn_et_id', "TEXT")
printit("Creating temporary xsln file to ensure wells beyond xsln endpoints plot correctly.")
# Read geometries of original xsln file and create new geometry in temp xsln file
# Temp xsln file will have the first and last segments extended equal to xsln spacing
# This is to ensure that near analysis function will find the correct point for
# wells beyond the from and to nodes of the cross section line.

with arcpy.da.SearchCursor(xsln_file_orig, ['SHAPE@', xsln_etid_field, 'mn_et_id']) as xsln:
    for line in xsln:
        et_id = line[1]
        mn_et_id = line[2]
        geompointlist = []
        # Fill geompoint list with list of vertices in the xsln as point geometry objects
        for vertex in line[0].getPart(0): #for each vertex in array of point objects
            point = arcpy.PointGeometry(arcpy.Point(vertex.X, vertex.Y))
            geompointlist.append(point) 
        # Set variables to define first two points
        beg_pt = geompointlist[0]
        beg_pt2 = geompointlist[1]
        # Calculate angle of beginning line segment from second point to beginning
        beg_angle_and_dist = beg_pt2.angleAndDistanceTo(beg_pt, "PLANAR")
        beg_angle = beg_angle_and_dist[0] 
        # Set variables to define last two points
        end_pt = geompointlist[-1]
        end_pt2 = geompointlist[-2]
        # Calculate angle of end line segment
        end_angle_and_dist = end_pt2.angleAndDistanceTo(end_pt, "PLANAR")
        end_angle = end_angle_and_dist[0] 
        # Calculate new beginning and end points based on angle of segment and xsln spacing
        # xsln spacing is an arbitrary length to extend the lines that should capture all of the points
        new_beg = beg_pt.pointFromAngleAndDistance(beg_angle, xsln_spacing, method='PLANAR')
        new_end = end_pt.pointFromAngleAndDistance(end_angle, xsln_spacing, method='PLANAR')
        # Change first and last coordinate values in geompointlist to use in creating temporary xsln file
        geompointlist[0] = new_beg
        geompointlist[-1] = new_end
        # Turn geompointlist into point object list instead of point geometry objects
        pointlist = []
        for vertex in geompointlist:
            newpt = vertex[0]
            pointlist.append(newpt)
        # Create arcpy array for writing geometry
        xsln_array = arcpy.Array(pointlist)
        # Turn array of point vertices into polyline object
        new_xsln_geometry = arcpy.Polyline(xsln_array, spatialref, True)
        with arcpy.da.InsertCursor(xsln_temp, ['SHAPE@', xsln_etid_field, 'mn_et_id']) as cursor:
            # Create geometry and fill in field values
            cursor.insertRow([new_xsln_geometry, et_id, mn_et_id])

#%% 16 Populate near analysis fields in wwpt file
# This is populating fields in wwpt file that are used later to create geometry
arcpy.env.overwriteOutput = True
starttime = datetime.datetime.now()
# Loop through each xsln_temp and create a geometry object for each line
with arcpy.da.SearchCursor(xsln_temp, ['SHAPE@', xsln_etid_field, 'mn_et_id']) as xsln:
    for line in xsln:
        et_id = line[1]
        mn_et_id = line[2]
        pointlist = []
        for vertex in line[0].getPart(0):
            # Creates a polyline geometry object from xsln_temp vertex points.
            # Necessary for near analysis
            point = arcpy.Point(vertex.X, vertex.Y)
            pointlist.append(point)
        array = arcpy.Array(pointlist)
        xsln_geometry = arcpy.Polyline(array)
        # Create a new wwpt file with only points associated with current xsln
        printit("Calculating well locations in cross section view for xsln {0} out of {1}.".format(et_id, xsln_count))
        wwpt_by_xs_file = os.path.join(wwpt_by_xs_fd, "wwpt_{0}".format(et_id))
        arcpy.analysis.Select(wwpt_file_temp, wwpt_by_xs_file, '"{0}" = \'{1}\''.format(wwpt_etid_field, et_id))
        # Do near analysis on wwpt file to populate near x, near y, and near dist fields
        # Near x and y are the coordinates of the point along the xsln that are closest to the well
        # "dist" is the distance between the well and the nearest point on the line
        arcpy.analysis.Near(wwpt_by_xs_file, xsln_geometry, '', 'LOCATION', '', 'PLANAR')
                
endtime = datetime.datetime.now()
elapsed = endtime - starttime
printit('Near analysis and line measuring completed at {0}. Elapsed time: {1}'.format(endtime, elapsed))

#%% 17 Delete wwpt_temp from feature dataset

arcpy.management.Delete(wwpt_file_temp)

#%% 18 Merge together wwpt by xs files into one file

arcpy.env.workspace = wwpt_by_xs_fd
wwpt_list = arcpy.ListFeatureClasses()
printit("Creating mapview well point file with cross section locations calculated.")
wwpt_list_paths = []
for file in wwpt_list:
    path = os.path.join(wwpt_by_xs_fd, file)
    wwpt_list_paths.append(path)

wwpt_merge = os.path.join(workspace, "wwpt_merge")
arcpy.management.Merge(wwpt_list_paths, wwpt_merge)

#%% 19 Create 2d well point geometry from merged wwpt file
if create_2d_points == True:
    starttime = datetime.datetime.now()
    printit('2D point geometry creation started at {0}'.format(starttime))
    
    with arcpy.da.SearchCursor(wwpt_merge, ['OID@', wwpt_wellid_field, wwpt_etid_field, 
                                            'NEAR_DIST', 'SHAPE@X', 'SHAPE@Y', 'elevation', 'mn_et_id']) as wwpt:
        for well in wwpt:
            index = well[0]
            wellid = well[1]
            et_id = well[2]
            mn_et_id = well[7]
            mn_etid_int = int(mn_et_id)
            dist = well[3] #NEAR_DIST field
            pct_dist = dist / xsln_spacing * 200 #percent distance
            real_x = well[4] #true x coordinate of well
            real_y = well[5] #true y coordinate of well
            real_z = well[6]
            if real_z == None:
                printit("Error: Well number {0} is null in elevation field. Skipping.".format(wellid))
                continue
            x_coord = real_x #2d x coordinate = true x coordinate

            y_coord = (((real_z * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
            index_int = int(index)
            if index_int % 5000 == 0: #Print statement every 5000th well to track progress
                printit('Working on well number {0} out of {1}'.format(index, wwpt_count))
                
            point_geometry = arcpy.Point(x_coord, y_coord)
            
            with arcpy.da.InsertCursor(pointfile, ['SHAPE@', strat_wellid_field, 'et_id', 'x_coord', 
                                                   'y_coord', 'distance', 'elevation', 'pct_dist', 'mn_et_id']) as cursor:
                # Create geometry and fill in field values, saving true coordinates in attribute
                cursor.insertRow([point_geometry, wellid, et_id, real_x, real_y, dist, real_z, pct_dist, mn_et_id])
    
    endtime = datetime.datetime.now()
    elapsed = endtime - starttime
    printit('2D point geometry completed at {0}. Elapsed time: {1}'.format(endtime, elapsed))

#%% 20 Create 3D and 2D polyline geometry from strat and wwpt tables
starttime = datetime.datetime.now()
printit('Polyline geometry creation started at {0}'.format(starttime))
nomatch_list = [] #list to store well id's from the strat table with no matching well point

# Define variables in search cursor object
with arcpy.da.SearchCursor(strat_table, ['OID@', strat_wellid_field, 'elev_top',
                                         'elev_bot']) as strat_records:
    for row in strat_records:
        strat_oid = row[0]
        wellid = row[1] 
        real_z_top = row[2] #true elevation
        real_z_bot = row[3] #true elevation
        #et_id = row[4]
        #etid_int = int(et_id)
        if real_z_top == None:
            printit("Error: Strat record number {0} has no value in elev_top field. Skipping.".format(strat_oid))
            continue
        if real_z_bot == None:
            printit("Error: Strat record number {0} has no value in elev_bot field. Skipping.".format(strat_oid))
            continue
       
        # Define two where_clauses for wwpt file query to handle numeric or text
        where_clause = "{0}={1}".format(wwpt_wellid_field, wellid) #where clause for numeric data type (default)
        if not wellid_is_numeric:
            where_clause = "{0}='{1}'".format(wwpt_wellid_field, wellid) #redefine where clause for string data type
        index_int = int(strat_oid)
        if index_int % 1000 == 0: #print statement every 1000th record to track progress
            printit('Working on creating polylines for strat record number {0} out of {1}'.format(strat_oid, strat_count))
        
        # Find well location that matches strat record well id and get coordinates and et_id information
        with arcpy.da.SearchCursor(wwpt_merge, ['SHAPE@X', 'SHAPE@Y', 'NEAR_DIST', wwpt_etid_field, 'mn_et_id'], where_clause) as wwpt:
            i = 0 #index used to track if there are any well points that match the strat record
            for well in wwpt:
                i += 1 
                # Define x and y coordinate variables
                real_x = well[0] # true well coordinate
                real_y = well[1] # true well coordinate
                x_coord = real_x #2d x coordinate = true x coordinate
                dist = well[2] # distance from xsln
                pct_dist = dist / xsln_spacing * 200 #percent distance
                et_id = well[3]
                #etid_int = int(et_id)
                mn_et_id = well[4]
                mn_etid_int = int(mn_et_id)
            if i == 0: #if there is no matching well point, move to the next strat record
                nomatch_list.append(wellid)
                continue
        # Create 2 point objects (top and bottom, in true coordinates) from x, y, and z coordinates
        z_top = (((real_z_top * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000 #elevation with VE and meters conversion
        z_bot = (((real_z_bot * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000 #elevation with VE and meters conversion
        real_pointA = arcpy.Point(real_x, real_y, real_z_top)
        real_pointB = arcpy.Point(real_x, real_y, real_z_bot)
        real_pointlist = [real_pointA, real_pointB]
        real_array = arcpy.Array(real_pointlist)
        # Turn 2 point objects into endpoints of a polyline segment
        real_polyline_geometry = arcpy.Polyline(real_array, spatialref, True)
        # Create insert cursor object to write geometry

        with arcpy.da.InsertCursor(polylinefile_3d, ['SHAPE@', strat_wellid_field, 'et_id', 'x_coord',
                                                     'y_coord', 'z_top', 'z_bot', 'strat_oid', 'mn_et_id']) as cursor3d:
            # Create geometry and fill in field values
            cursor3d.insertRow([real_polyline_geometry, wellid, et_id, real_x, real_y, real_z_top, real_z_bot, strat_oid, mn_et_id])
            
        # Create 2 point objects (top and bottom) from x and y coordinates for 2d geometry
        pointA = arcpy.Point(x_coord, z_top)
        pointB = arcpy.Point(x_coord, z_bot)
        pointlist = [pointA, pointB]
        array = arcpy.Array(pointlist)
        # Turn 2 point objects into endpoints of a polyline segment
        polyline_geometry = arcpy.Polyline(array)
        # Create insert cursor object 

        with arcpy.da.InsertCursor(polylinefile_2d, ['SHAPE@', strat_wellid_field, 'et_id', 'x_coord',
                                                     'y_coord','z_top', 'z_bot', 'strat_oid', 'distance', 'pct_dist', 'mn_et_id']) as cursor2d:
            # Create geometry and fill in field values, saving true coordinates in attribute
            cursor2d.insertRow([polyline_geometry, wellid, et_id, real_x, real_y,
                                real_z_top, real_z_bot, strat_oid, dist, pct_dist, mn_et_id])
            
endtime = datetime.datetime.now()
elapsed = endtime - starttime
if len(nomatch_list) > 0:
    printit("Could not find matching well point for {0} stratigraphy table records. These strat records were skipped.".format(len(nomatch_list)))
printit('Polyline geometry completed at {0}. Elapsed time: {1}'.format(endtime, elapsed))

#%% 21 Create list of stratigraphy fields based on which fields exist and which are relevant

printit("Finding relevant stratigraphy data fields to join to output files.")

strat_table_fields_all = arcpy.ListFields(strat_table)
relevant_strat_fields = []
for field in strat_table_fields_all:
    name = field.name
    relevant_strat_fields.append(name)

# List fields that do not contain relevant stratigraphy information
# These fields will not be joined to the output lixpys
fields_not_to_join = ['OBJECTID','Join_Count','TARGET_FID', 'JOIN_FID', 'c5st_seq_no', 'relateid', 'depth_top',
                      'depth_bot', 'wellid', 'elev_top', 'elev_bot', 'bdrkelev', 'depth2bdrk', 'first_bdrk',
                      'last_strat', 'ohtopunit', 'ohtopelev', 'ohbotunit', 'ohbotelev', 'botholelev', 'aquifer',
                      'Join_Count_1', 'TARGET_FID_1', 'et_id', 'utmn', 'utme_min', 'utme_max', 'mn_et_id',
                      'BUFF_DIST', 'ORIG_FID', 'strat_orig', 'GlobalID']

# By picking out fields NOT to join, the tool will automatically join fields unless the code tells it not to.
# This means that by default, extra fields will be joined, rather than the other way around.

# Remove fields from list that do not contain relevant stratigraphy information
for field in fields_not_to_join:
    if field in relevant_strat_fields:
        relevant_strat_fields.remove(field)


#%% 22 Join stratigraphy fields to 2d and 3d polyline feature classes

printit("Joining relevant stratigraphy fields to 3d polyline file.")
arcpy.management.JoinField(polylinefile_3d, 'strat_oid', strat_table, 'OBJECTID', relevant_strat_fields)
printit("Joining relevant stratigraphy fields to 2d polyline file.")
arcpy.management.JoinField(polylinefile_2d, 'strat_oid', strat_table, 'OBJECTID', relevant_strat_fields)

#%% 23 Create 2d polygon lixpys from 2d lines

printit('Creating 2D lixpy polygons from 2D lines.')

# Set width of polygon proportional to vertical exaggeration
bufferdist = (vertical_exaggeration * 0.15) + 40

# Set file path for new unsorted polygon file
temp_polygon_file = os.path.join(workspace, 'lixpys_2d_poly_temp')
# Create polygon feature class using buffer tool
arcpy.analysis.Buffer(polylinefile_2d, temp_polygon_file, bufferdist, '', 'FLAT', '', '', 'PLANAR')

# Set file path for new sorted polygon file
polygon_file = os.path.join(workspace, 'lixpys_2d_poly')
# Sort polygon feature by well id (so that ArcGIS draws them in the correct order)
arcpy.management.Sort(temp_polygon_file, polygon_file, strat_wellid_field)

printit('Create 2D lixpy polygons completed.')

#%% 24 Delete temporary files/fields

printit("Deleting temporary files from output geodatabase.")
try:
    arcpy.management.Delete(temp_polygon_file)
    arcpy.management.Delete(wwpt_by_xs_fd)
    arcpy.management.Delete(wwpt_merge)
    arcpy.management.Delete(xsln_temp)
except:
    printit("Warning: unable to delete all temporary files.")                          
                             
#%% 25 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Lixpy tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))


