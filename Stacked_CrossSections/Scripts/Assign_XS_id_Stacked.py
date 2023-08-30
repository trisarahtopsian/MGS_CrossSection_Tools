#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Add Cross Section ID to Stacked XS Data
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: October 2022
'''
This script will automatically join mn_et_id number to data created by geologists
in the stacked cross section system. If the user also inputs a xsln file, it
can also join the et_id field. 
'''

# %% 1 Import modules

import arcpy
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

# %% 2 Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):
    #variable = arcpy.GetParameterAsText(0)
    in_fc = arcpy.GetParameterAsText(0)
    out_fc = arcpy.GetParameterAsText(1)
    join_etid = arcpy.GetParameter(2) #checkbox
    xsln_fc = arcpy.GetParameterAsText(3) #option only available if user checks above box
    etid_field = arcpy.GetParameterAsText(4) #option only available if user checks above box
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    in_fc = r'D:\QuatStrat_Editing\Stacked_Testing\assign_etid.gdb\strat_all'
    out_fc = r'D:\QuatStrat_Editing\Stacked_Testing\assign_etid.gdb\strat_all_join5'
    join_etid = True #checkbox
    xsln_fc = r'D:\QuatStrat_Editing\Stacked_Testing\assign_etid.gdb\xsln' #option only available if user checks above box
    etid_field = 'et_id' #option only available if user checks above box
    printit("Variables set with hard-coded parameters for testing.")

#%% 3 Data QC

#check that mn_et_id field exists in xsln_fc and that it is text data type
#only check this if the user wishes to join et_id field

if join_etid == True:
    exists = False
    text = False

    for field in arcpy.ListFields(xsln_fc):
        if field.name == "mn_et_id":
            printit("Good, mn_et_id field exists.")
            exists = True
            if field.type == 'String':
                printit("Good, mn_et_id is text data type.")
                text = True
                break

    if exists == False:
        printerror("!!ERROR!! mn_et_id field does not exist in xsln file. Tool will be unable to join id field.")
    if text == False:
        printerror("!!ERROR!! mn_et_id field is not text data type. Join will not work correctly")

# %% 4 statewide stacked xs parameters

min_x = 160000
max_x = 775000
min_z = 0
max_z = 2300
county_relief = 700
vertical_exaggeration = 50

#%% 5 Create temp polygon file in memory and add mn_et_id field

polygon_file = r'in_memory\poly_ref_stacked'
arcpy.management.CreateFeatureclass('in_memory', 'poly_ref_stacked', 'POLYGON')
arcpy.management.AddField(polygon_file, 'mn_et_id', "TEXT")

#%% 6 create a list of mn_et_id 

#make list based on statewide mn_et_id if user doesn't provide a xsln feature class
if join_etid == False:
    id_list = [i for i in range(661)]

#make list based on xsln feature class if it's provided by the user
if join_etid == True:
    id_list = []
    with arcpy.da.SearchCursor(xsln_fc, ['mn_et_id']) as cursor:
        for row in cursor:
            mn_et_id = int(row[0])
            if mn_et_id not in id_list:
                id_list.append(mn_et_id)

#%% 7 Create polygon geometry      
printit("Creating polygon geometry.")

for mn_et_id in id_list:
    #define string version of mn_et_id
    mn_et_id_str = str(mn_et_id)
    #calculate coordinates of four corners of rectangle for this cross section
    min_y = (((min_z * 0.3048) - (county_relief * mn_et_id)) * vertical_exaggeration) + 23100000
    max_y = (((max_z * 0.3048) - (county_relief * mn_et_id)) * vertical_exaggeration) + 23100000
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
    with arcpy.da.InsertCursor(polygon_file, ['SHAPE@', 'mn_et_id']) as cursor:
        cursor.insertRow([poly_geom, mn_et_id_str])

#%% 8 Join mn_et_id to in_fc, join et_id if user selected

printit("Joining mn_et_id fields to output.")
arcpy.analysis.SpatialJoin(in_fc, polygon_file, out_fc)
if join_etid == True:
    printit("Joining et_id field to output.")
    arcpy.management.JoinField(out_fc, 'mn_et_id', xsln_fc, 'mn_et_id', [etid_field])

#%% 9 Delete temporary polygon file

printit("Deleting temporary polygon file.")
try:
    arcpy.management.Delete(polygon_file)
except:
    printit("Unable to delete temporary file {0}".format(polygon_file))

# %% 10 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))