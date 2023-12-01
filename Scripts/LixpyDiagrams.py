#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Create Well Stick Diagrams
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: November 2023
'''
This script creates polyline files that are used to visualize well lithologies
along defined cross sections. Outputs are: a well stick diagram file in 3D with
true x, y, and z coordinates, well stick diagram files (line and polygon format)
in 2D cross-section space to use for cross-section creation and editing, and a
well point file in 2D cross-section space. Data is retrieved from a well 
point location feature class and a corresponding stratigraphy table with lithology 
and depth information. The two tables have a one-to-many relationship. The script
will output data in the stacked or traditional display.
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
    workspace = arcpy.GetParameterAsText(0) #output gdb
    strat_table = arcpy.GetParameterAsText(1) #gdb table with stratigraphy info. Multiple records per well.
    wwpt_file_orig = arcpy.GetParameterAsText(2) #point feature class with well location information
    xsln_file_orig = arcpy.GetParameterAsText(3) #mapview cross section line feature class
    xsln_etid_field = arcpy.GetParameterAsText(4) #cross section ID field in cross section file, text data type
    wwpt_etid_field = arcpy.GetParameterAsText(5) #cross section ID field in well point file
    strat_wellid_field = arcpy.GetParameterAsText(6) #well ID number field in strat table
    wwpt_wellid_field = arcpy.GetParameterAsText(7) #well ID number field in well point file
    buffer_dist = int(arcpy.GetParameterAsText(8))
    display_system = arcpy.GetParameterAsText(9) #"stacked" or "traditional"
    #parameter below only appears if display_system is "traditional"
    vertical_exaggeration_in = arcpy.GetParameter(10)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    workspace = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb' #output gdb
    strat_table = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\strat_cwi' #gdb table with stratigraphy info. Multiple records per well.
    wwpt_file_orig = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\wwpt' #point feature class with well location information
    xsln_file_orig = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\xsln' #mapview cross section line feature class
    xsln_etid_field = 'et_id' #cross section ID field in cross section file, text data type
    wwpt_etid_field = 'et_id' #cross section ID field in well point file
    strat_wellid_field = 'relateid' #well ID number field in strat table
    wwpt_wellid_field = 'relateid' #well ID number field in well point file
    buffer_dist = 500 
    display_system = "stacked" #"stacked" or "traditional"
    #parameter below only appears if display_system is "traditional"
    vertical_exaggeration_in = 50
    printit("Variables set with hard-coded parameters for testing.")

#%% 
# 3 set county relief and vertical exaggeration variables for stacked display
# county relief controls distance between cross sections
#DO NOT edit these values, except in special cases
if display_system == "stacked":
    county_relief = 700
    vertical_exaggeration = int(50)
if display_system == "traditional":
    vertical_exaggeration = int(vertical_exaggeration_in)

#%% 
# 4 Set 3d spatial reference based on xsln file

spatialref = arcpy.Describe(xsln_file_orig).spatialReference
if spatialref.name == "Unknown":
    printerror("{0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(xsln_file_orig)))
else:
    printit("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(xsln_file_orig)))

#%% 
# 5 Add mn_et_id field to wwpt file if it doesn't exist, for stacked only
#strat table does not need et_id or mn_et_id for this code to work.
#it will get these numbers and assign them based on matching well point.
#therefore, well point file must have mn_et_id
#this code will add mn_et_id to well points if it doesn't have it already
if display_system == "stacked":
    #first, check that xsln file has mn_et_id
    FieldExists(xsln_file_orig, 'mn_et_id')

    #check that well point file has mn_et_id and join the field if it doesn't
    if 'mn_et_id' in [field.name for field in arcpy.ListFields(wwpt_file_orig)]:
        printit("Good, mn_et_id field already exists in well point file.")
    else:
        printit("Adding mn_et_id field to well point file based on et_id in xsln file.")
        arcpy.management.JoinField(wwpt_file_orig, wwpt_etid_field, xsln_file_orig, xsln_etid_field, ['mn_et_id'])

# %% 
# 6 Data QC

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

#%% 7 Data QC
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
  
# %% 
# 9 List fields that are used in 3d line, 2d line, and 2d point

# set field type of well id so code correctly handles text vs. numeric
if wellid_is_numeric:
    well_id_field_type = 'DOUBLE'
elif not wellid_is_numeric:
    well_id_field_type = 'TEXT'

# fields needed in all output files    
fields_base = [[strat_wellid_field, well_id_field_type], [xsln_etid_field, 'TEXT', '', 3], 
               ['x_coord', 'DOUBLE'], ['y_coord', 'DOUBLE']]
#add mn_et_id field for stacked display
if display_system == "stacked":
    fields_base.append(['mn_et_id', 'TEXT', '', 5])

# fields needed in polyline/polygon output files (both 2d and 3d versions)
fields_strat = [['strat_oid', 'DOUBLE'], ['z_top', 'DOUBLE'], ['z_bot', 'DOUBLE']] 

# fields only needed in 2d files (point, polyline, and polygon)
fields_2d = [['distance', 'FLOAT'], ['pct_dist', 'FLOAT']]


# %% 
# 10 Create empty 3d polyline file

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

# %% 
# 11 Create empty 2d polyline file

arcpy.env.overwriteOutput = True
#create polyline shapefile, spatial ref defined above
printit("Creating empty 2d polyline file for well stick diagrams.")
if display_system == "stacked":
    output_name = "lixpys_2d_line"
if display_system == "traditional":
    output_name = "lixpys_2d_line_" + str(vertical_exaggeration) + "x"

arcpy.management.CreateFeatureclass(workspace, output_name, "POLYLINE", '', 'DISABLED', 'DISABLED')
#set polyline shapefile filepath variable
polylinefile_2d = os.path.join(workspace, output_name)

if run_location == "Pro":
    # define derived output parameter. This is necessary to reference the output to apply the right symbology
    arcpy.SetParameterAsText(11, polylinefile_2d)

#define field names and types: base fields, strat fields, and 2d fields
polyline_2d_fields = fields_base + fields_strat + fields_2d

#Add fields to 2D polyline file
arcpy.management.AddFields(polylinefile_2d, polyline_2d_fields)

#%% 
# 12 Create feature dataset to store wwpt files by xs
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

#%% 12 Add fields to temporary wwpt point feature class
# These fields will be populated by near analysis and measure on line functions

wwpt_fields = [["NEAR_FID", "LONG"], ["NEAR_DIST", "DOUBLE"], ["NEAR_X", "DOUBLE"], 
               ["NEAR_Y", "DOUBLE"]]
#add online distance field, necessary for plotting in the traditional display
if display_system == "traditional":
    wwpt_fields.append(["OnLine_DIST", "FLOAT"])

for newfield in wwpt_fields:
    if newfield[0] in [field.name for field in arcpy.ListFields(wwpt_file_temp)]:
        printit("{0} field already exists in well point file. Tool will overwrite data in this field.".format(newfield[0]))
    else:
        printit("Adding {0} field to well point file.".format(newfield[0]))
        arcpy.management.AddField(wwpt_file_temp, newfield[0], newfield[1])

#%% 
# 13 Create a temporary xsln file and extend the lines equal to buffer distance
    # The extended xsln file is used to define 2d x coordinates of wells
    # to ensure that wells beyond the xsln plot correctly
# Create temporary xsln file (empty for now)
xsln_temp = os.path.join(workspace, "xsln_temp")
arcpy.management.CreateFeatureclass(workspace, "xsln_temp", "POLYLINE", '', 'DISABLED', 'DISABLED', spatialref)

# add et_id and mn_et_id (stacked only) fields to temp xsln file
arcpy.management.AddField(xsln_temp, xsln_etid_field, "TEXT")
if display_system == "stacked":
    arcpy.management.AddField(xsln_temp, 'mn_et_id', "TEXT")
printit("Creating temporary xsln file to ensure wells beyond xsln endpoints plot correctly.")
# Read geometries of original xsln file and create new geometry in temp xsln file
# Temp xsln file will have the first and last segments extended equal to xsln spacing
# This is to ensure that near analysis function will find the correct point for
# wells beyond the from and to nodes of the cross section line.

#cursor fields will include mn_et_id for stacked, not necessary for traditional
if display_system == "traditional":
    cursor_fields = ['SHAPE@', xsln_etid_field]
if display_system == "stacked":
    cursor_fields = ['SHAPE@', xsln_etid_field, "mn_et_id"]

with arcpy.da.SearchCursor(xsln_file_orig, cursor_fields) as xsln:
    for line in xsln:
        et_id = line[1]
        if display_system == "stacked":
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
        # Calculate new beginning and end points based on angle of segment and buffer distance
        # extending lines equal to buffer distance should capture all of the points
        new_beg = beg_pt.pointFromAngleAndDistance(beg_angle, buffer_dist, method='PLANAR')
        new_end = end_pt.pointFromAngleAndDistance(end_angle, buffer_dist, method='PLANAR')
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
        with arcpy.da.InsertCursor(xsln_temp, cursor_fields) as cursor:
            # Create geometry and fill in field values
            if display_system == "traditional":
                cursor.insertRow([new_xsln_geometry, et_id])
            if display_system == "stacked":
                cursor.insertRow([new_xsln_geometry, et_id, mn_et_id])

#%% 
# 14 Populate near analysis fields in wwpt file
# This is populating fields in wwpt file that are used later to create geometry
arcpy.env.overwriteOutput = True
starttime = datetime.datetime.now()
# Loop through each xsln_temp and create a geometry object for each line
with arcpy.da.SearchCursor(xsln_temp, ['SHAPE@', xsln_etid_field]) as xsln:
    for line in xsln:
        et_id = line[1]
        pointlist = []
        for vertex in line[0].getPart(0):
            # Creates a polyline geometry object from xsln_temp vertex points.
            # Necessary for near analysis
            point = arcpy.Point(vertex.X, vertex.Y)
            pointlist.append(point)
        array = arcpy.Array(pointlist)
        xsln_geometry = arcpy.Polyline(array)
        # Create a new wwpt file with only points associated with current xsln
        printit("Calculating well locations in cross section view for line {0} out of {1}.".format(et_id, xsln_count))
        wwpt_by_xs_file = os.path.join(wwpt_by_xs_fd, "wwpt_{0}".format(et_id))
        arcpy.analysis.Select(wwpt_file_temp, wwpt_by_xs_file, '"{0}" = \'{1}\''.format(wwpt_etid_field, et_id))
        # Do near analysis on wwpt file to populate near x, near y, and near dist fields
        # Near x and y are the coordinates of the point along the xsln that are closest to the well
        # "dist" is the distance between the well and the nearest point on the line
        arcpy.analysis.Near(wwpt_by_xs_file, xsln_geometry, '', 'LOCATION', '', 'PLANAR')

        # Calculate distance along line for traditional display
        if display_system == "traditional":
            with arcpy.da.UpdateCursor(wwpt_by_xs_file, ['OID@', 'NEAR_X', 'NEAR_Y', 'OnLine_DIST']) as wellpts:
                for well in wellpts:
                    index = well[0]
                    x =  well[1]
                    y = well[2]
                    # Create point geometry object from nearest point on the xsln
                    point = arcpy.Point(x, y)
                    # Measure distance from start of xsln geometry object to defined point
                    # This is the "OnLine_DIST" which turns into 2d x coordinate after vertical exaggeration calculation
                    n = arcpy.Polyline.measureOnLine(xsln_geometry, point)
                    #subtract extended line distance so points before start nodes will have negative values
                    well[3] = n - buffer_dist 
                    # Update field values in wwpt table to track near x, y, and OnLine dist
                    wellpts.updateRow(well)
        
endtime = datetime.datetime.now()
elapsed = endtime - starttime
printit('Near analysis and line measuring completed at {0}. Elapsed time: {1}'.format(endtime, elapsed))

#%% 
# 15 Delete wwpt_temp from feature dataset

arcpy.management.Delete(wwpt_file_temp)

#%% 
# 16 Merge together wwpt by xs files into one file

arcpy.env.workspace = wwpt_by_xs_fd
wwpt_list = arcpy.ListFeatureClasses()
printit("Creating mapview well point file with cross section locations calculated.")
wwpt_list_paths = []
for file in wwpt_list:
    path = os.path.join(wwpt_by_xs_fd, file)
    wwpt_list_paths.append(path)

wwpt_merge = os.path.join(workspace, "wwpt_merge")
arcpy.management.Merge(wwpt_list_paths, wwpt_merge)

#%%
# 17 Create 3D and 2D polyline geometry from strat and wwpt tables
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
        if real_z_top == None:
            printit("Error: Strat record {0} has no value in elev_top field. Skipping.".format(strat_oid))
            continue
        if real_z_bot == None:
            printit("Error: Strat record {0} has no value in elev_bot field. Skipping.".format(strat_oid))
            continue
       
        # Define two where_clauses for wwpt file query to handle numeric or text
        where_clause = "{0}={1}".format(wwpt_wellid_field, wellid) #where clause for numeric data type (default)
        if not wellid_is_numeric:
            where_clause = "{0}='{1}'".format(wwpt_wellid_field, wellid) #redefine where clause for string data type
        index_int = int(strat_oid)
        if index_int % 1000 == 0: #print statement every 1000th record to track progress
            printit('Creating polylines for strat record {0} out of {1}'.format(strat_oid, strat_count))
        
        # Find well location that matches strat record well id and get coordinates and et_id information
        if display_system == "stacked":
            #mn_et_id needed for stacked
            cursor_fields = ['SHAPE@X', 'SHAPE@Y', 'NEAR_DIST', wwpt_etid_field, 'mn_et_id']
        if display_system == "traditional":
            #OnLine_DIST needed for traditional
            cursor_fields = ['SHAPE@X', 'SHAPE@Y', 'NEAR_DIST', wwpt_etid_field, 'OnLine_DIST']
        with arcpy.da.SearchCursor(wwpt_merge, cursor_fields, where_clause) as wwpt:
            i = 0 #index used to track if there are any well points that match the strat record
            for well in wwpt:
                i += 1
                # Define x and y coordinate variables
                real_x = well[0] # true well coordinate
                real_y = well[1] # true well coordinate
                dist = well[2]
                et_id = well[3]
                pct_dist = dist/buffer_dist*200        
                #calculate x coordinate for 2d display
                #calculation is different for each type of display
                if display_system == "stacked":
                    x_coord = real_x #2d x coordinate = true x coordinate
                    mn_et_id = well[4]
                    mn_etid_int = int(mn_et_id)
                if display_system == "traditional":
                    #Divide distance along line by vertical exaggeration 
                    # to squish x axis for vertical exaggeration
                    x_coord_meters = well[4]
                    x_coord_feet = x_coord_meters/0.3048
                    x_coord = x_coord_feet/vertical_exaggeration
            if i == 0: #if there is no matching well point, move to the next strat record
                nomatch_list.append(wellid)
                continue
        # Create 2 point objects (top and bottom, in true coordinates) from x, y, and z coordinates
        real_pointA = arcpy.Point(real_x, real_y, real_z_top)
        real_pointB = arcpy.Point(real_x, real_y, real_z_bot)
        real_pointlist = [real_pointA, real_pointB]
        real_array = arcpy.Array(real_pointlist)
        # Turn 2 point objects into endpoints of a polyline segment
        real_polyline_geometry = arcpy.Polyline(real_array, spatialref, True)
        # Create insert cursor object to write geometry
        insert_cursor_fields = ['SHAPE@', strat_wellid_field, xsln_etid_field, 'x_coord', 'y_coord', 
                                'z_top', 'z_bot', 'strat_oid']
        if display_system == "stacked":
            insert_cursor_fields.append("mn_et_id")
        with arcpy.da.InsertCursor(polylinefile_3d, insert_cursor_fields) as cursor3d:
            # Create geometry and fill in field values
            if display_system == "traditional":
                cursor3d.insertRow([real_polyline_geometry, wellid, et_id, real_x, real_y, real_z_top, real_z_bot, strat_oid])
            if display_system == "stacked":
                cursor3d.insertRow([real_polyline_geometry, wellid, et_id, real_x, real_y, real_z_top, real_z_bot, strat_oid, mn_et_id])
        
        # Create 2 point objects (top and bottom) from x and y coordinates for 2d geometry
        #first, calculate y coordinate in 2d space for each display system
        if display_system == "traditional":
            # y coordinate is the same as true z coordinate
            y_top = real_z_top
            y_bot = real_z_bot
        if display_system == "stacked":
            # y coordinate is calculated using true z coordinate
            y_top = (((real_z_top * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000 #elevation with VE and meters conversion
            y_bot = (((real_z_bot * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000 #elevation with VE and meters conversion

        pointA = arcpy.Point(x_coord, y_top)
        pointB = arcpy.Point(x_coord, y_bot)
        pointlist = [pointA, pointB]
        array = arcpy.Array(pointlist)
        # Turn 2 point objects into endpoints of a polyline segment
        polyline_geometry = arcpy.Polyline(array)

        # Create insert cursor object 
        insert_cursor_fields_2d = ['SHAPE@', strat_wellid_field, xsln_etid_field, 'x_coord','y_coord',
                                   'z_top', 'z_bot', 'strat_oid', 'distance', 'pct_dist']
        if display_system == "stacked":
            # stacked version includes mn_et_id
            insert_cursor_fields_2d.append('mn_et_id')
        with arcpy.da.InsertCursor(polylinefile_2d, insert_cursor_fields_2d) as cursor2d:
            # Create geometry and fill in field values, saving true coordinates in attribute
            # stacked version includes mn_et_id
            if display_system == "stacked":
                cursor2d.insertRow([polyline_geometry, wellid, et_id, real_x, real_y,
                                    real_z_top, real_z_bot, strat_oid, dist, pct_dist, mn_et_id])
            if display_system == "traditional":
                cursor2d.insertRow([polyline_geometry, wellid, et_id, real_x, real_y,
                                    real_z_top, real_z_bot, strat_oid, dist, pct_dist])

endtime = datetime.datetime.now()
elapsed = endtime - starttime
if len(nomatch_list) > 0:
    printit("Could not find matching well point for {0} stratigraphy table records. These strat records were skipped.".format(len(nomatch_list)))
printit('Polyline geometry completed at {0}. Elapsed time: {1}'.format(endtime, elapsed))

#%% 
# 18 Create list of stratigraphy fields based on which fields exist and which are relevant

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

#%% 
# 19 Join stratigraphy fields to 2d and 3d polyline feature classes

printit("Joining relevant stratigraphy fields to 3d polyline file.")
arcpy.management.JoinField(polylinefile_3d, 'strat_oid', strat_table, 'OBJECTID', relevant_strat_fields)
printit("Joining relevant stratigraphy fields to 2d polyline file.")
arcpy.management.JoinField(polylinefile_2d, 'strat_oid', strat_table, 'OBJECTID', relevant_strat_fields)

#%% 
# 20 Create 2d polygon lixpys from 2d lines
arcpy.env.overwriteOutput = True
printit('Creating 2D lixpy polygons from 2D lines.')

# Set width of polygon proportional to vertical exaggeration
#since traditional display has the x axis squished, the equation is different for each display
if display_system == "traditional":
    bufferdist = (130/vertical_exaggeration) + 0.5
if display_system == "stacked":
    bufferdist = (vertical_exaggeration * 0.15) + 40

# Set file path for new unsorted polygon file
temp_polygon_file = os.path.join(workspace, 'lixpys_2d_poly_temp')
# Create polygon feature class using buffer tool
arcpy.analysis.Buffer(polylinefile_2d, temp_polygon_file, bufferdist, '', 'FLAT', '', '', 'PLANAR')

# Set file path for new sorted polygon file
if display_system == "stacked":
    polygon_file = os.path.join(workspace, 'lixpys_2d_poly')
if display_system == "traditional":
    polygon_file = os.path.join(workspace, 'lixpys_2d_poly_' + str(vertical_exaggeration) + "x")

if run_location == "Pro":
    # define derived output parameter. This is necessary to reference the output to apply the right symbology
    arcpy.SetParameterAsText(12, polygon_file)

# Sort polygon feature by well id (so that ArcGIS draws them in the correct order)
arcpy.management.Sort(temp_polygon_file, polygon_file, strat_wellid_field)

printit('Create 2D lixpy polygons completed.')

#%% 
# 21 Delete temporary files/fields

printit("Deleting temporary files from output geodatabase.")
try:
    arcpy.management.Delete(temp_polygon_file)
    arcpy.management.Delete(wwpt_by_xs_fd)
    arcpy.management.Delete(wwpt_merge)
    arcpy.management.Delete(xsln_temp)
except:
    printit("Warning: unable to delete all temporary files.")                          
                             
#%% 
# 22 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Lixpy tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))



# %%
