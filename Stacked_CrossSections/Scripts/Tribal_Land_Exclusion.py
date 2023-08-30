#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Tribal Land Exclusion (Stacked)
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: December 2022, Updated April 2023
'''
This tool will create rectangles in stacked cross section view based on
locations of polygons in mapview. The anticipated use is to show areas of 
Tribal land that should not be mapped, but the tool may have other
applications.
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

# Define file exists function and field exists function

def FileExists(file):
    if not arcpy.Exists(file):
        printerror("Error: {0} does not exist.".format(os.path.basename(file)))
    
def FieldExists(dataset, field_name):
    if field_name in [field.name for field in arcpy.ListFields(dataset)]:
        return True
    else:
        printerror("Error: {0} field does not exist in {1}."
                .format(field_name, os.path.basename(dataset)))

#%% 2 Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):
    xsln = arcpy.GetParameterAsText(0) #mapview xsln file
    xsec_id_field = arcpy.GetParameterAsText(1) #et_id in xsln
    intersect_polys = arcpy.GetParameterAsText(2) #polygon file to intersect with xsln. county boundary, papg, etc.
    output_attribute = arcpy.GetParameterAsText(3) #attribute to attach to output lines, such as county name. 
    output_poly_fc = arcpy.GetParameterAsText(4) #output polygon file
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    xsln = r'D:\GLC_Phase5_D_drive\data_setup.gdb\xsln' #mapview xsln file
    xsec_id_field = 'et_id' #et_id in xsln
    intersect_polys = r'D:\GLC_Phase5_D_drive\data_setup.gdb\tribal_land' #polygon file to intersect with xsln. county boundary, papg, etc.
    output_attribute = 'tribal_name' #attribute to attach to output lines, such as county name. 
    output_poly_fc = r'D:\GLC_Phase5_D_drive\200_relief_test.gdb\tribal_land_xsview' #output polygon file
    printit("Variables set with hard-coded parameters for testing.")

#%% 3 set county relief variable (controls distance between cross sections)
#DO NOT edit this value, except in special cases
county_relief = 700
vertical_exaggeration = 50

#%% 4 Data QC
#Check that surface profiles have mn_et_id field
FieldExists(xsln, 'mn_et_id')

#%% 5 Intersect 
arcpy.env.overwriteOutput = True

printit("Intersecting polygons with xsln and creating temporary line file.")
#get directory where output will be saved
output_dir = os.path.dirname(output_poly_fc)
#get filename of output
output_name = os.path.basename(output_poly_fc)
#create name and path for temp output
output_fc_temp_multi = os.path.join(output_dir, output_name + "_temp_3d_multi")
#create temporary 3D intersect file
arcpy.analysis.Intersect([xsln, intersect_polys], output_fc_temp_multi, 'NO_FID', '', 'LINE')
#convert multipart to singlepart
output_fc_temp = os.path.join(output_dir, output_name + "_temp_3d")
arcpy.management.MultipartToSinglepart(output_fc_temp_multi, output_fc_temp)

#%% 6 Create empty polygon file and add fields

attribute_with_filename = False
output_attribute_field = output_attribute
#if user did nto select an attribute field for output, set boolean to True to show that output will be attributed with filename

if output_attribute == '':
    attribute_with_filename = True
    output_attribute_field = "source_file"
    output_attribute_value = os.path.basename(intersect_polys)

printit("Creating empty line file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POLYGON')
fields = [[xsec_id_field, 'TEXT', '', 5], ["mn_et_id", "TEXT", '', 5], [output_attribute_field, "TEXT"]]
arcpy.management.AddFields(output_poly_fc, fields)

#%% 7 Convert geometry to cross section view and write to output file

printit("Creating 2d line geometry.")

if attribute_with_filename == True:
    fields = ['SHAPE@', xsec_id_field, 'mn_et_id']
elif attribute_with_filename == False:
    fields = ['SHAPE@', xsec_id_field, 'mn_et_id', output_attribute_field]

with arcpy.da.SearchCursor(output_fc_temp, fields) as cursor:
    for line in cursor:
        etid = line[1]
        mn_etid = line[2]
        mn_etid_int = int(mn_etid)
        #set top and bottom y coordinates for every x
        y_2d_1 = (((50 * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
        y_2d_2 = (((2300 * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
        if attribute_with_filename == False:
            output_attribute_value = line[3]
        pointlist = []
        x_list = []
        for vertex in line[0].getPart(0):
            #get x coordinate
            x_2d = vertex.X
            #make list of x coordinates in line
            x_list.append(x_2d)
        #create 2 vertical lines, one at each endpoint of the line
        pt1 = arcpy.Point(x_list[0], y_2d_1)
        pt2 = arcpy.Point(x_list[0], y_2d_2)
        pt3 = arcpy.Point(x_list[-1], y_2d_1)
        pt4 = arcpy.Point(x_list[-1], y_2d_2)
        pointlist.append(pt1)
        pointlist.append(pt2)
        pointlist.append(pt4)
        pointlist.append(pt3)
        array = arcpy.Array(pointlist)
        geometry = arcpy.Polygon(array)
        #create geometry into output file
        with arcpy.da.InsertCursor(output_poly_fc, ['SHAPE@', output_attribute_field, xsec_id_field, 'mn_et_id']) as cursor2d:
            cursor2d.insertRow([geometry, output_attribute_value, etid, mn_etid])
            
                     
#%% 8 Delete temporary files

printit("Deleting temporary line files.")
try: arcpy.management.Delete(output_fc_temp_multi)
except: printit("Unable to delete temporary file {0}".format(output_fc_temp_multi))
try: arcpy.management.Delete(output_fc_temp)
except: printit("Unable to delete temporary file {0}".format(output_fc_temp))

#%% 11 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))