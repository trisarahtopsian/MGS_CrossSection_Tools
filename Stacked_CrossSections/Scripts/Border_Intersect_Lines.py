#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Border Intersect Lines (stacked)
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: December 2022, Updated April 2023
'''
This script creates vertical lines in stacked cross section view where 
mapview polygons boundaries intersect cross section lines. The output lines
are attributed with the filename if no output attribute is selected, or
will contain an attribute from the input polygons if the user chooses.
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
    xsec_id_field = arcpy.GetParameterAsText(1) #et_id in surface profiles
    intersect_polys = arcpy.GetParameterAsText(2)#polygon file to intersect with xsln. county boundary, papg, etc.
    output_attribute = arcpy.GetParameterAsText(3) #attribute to attach to output lines, such as county name. If left blank, output will have attribute with input file name
    output_line_fc = arcpy.GetParameterAsText(4)
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    xsln = r'D:\DakotaSandModel\TINmodel_110122\SandModeling_TIN.gdb\xsln' #mapview xsln file
    xsec_id_field = 'et_id' #et_id in xsln
    intersect_polys = r'D:\DakotaSandModel\TINmodel_110122\SandModeling_TIN.gdb\county_boundary' #polygon file to intersect with xsln. county boundary, papg, etc.
    output_attribute = '' #attribute to attach to output lines, such as county name. If left blank, output will have attribute with input file name
    output_line_fc = r'D:\DakotaSandModel\TINmodel_110122\SandModeling_TIN.gdb\county_intersect_lines' #output line file
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
output_dir = os.path.dirname(output_line_fc)
#get filename of output
output_name = os.path.basename(output_line_fc)
#create name and path for temp output
output_line_fc_temp_multi = os.path.join(output_dir, output_name + "_temp_line_3d_multi")
#create temporary 3D intersect file
arcpy.analysis.Intersect([xsln, intersect_polys], output_line_fc_temp_multi, 'NO_FID', '', 'LINE')
#convert multipart to singlepart
output_line_fc_temp = os.path.join(output_dir, output_name + "_temp_line_3d")
arcpy.management.MultipartToSinglepart(output_line_fc_temp_multi, output_line_fc_temp)

#%% 6 Create empty line file and add fields

#set output attribute field to have source file name if user didn't select an attribute

#set boolean variable to show that output will not be attributed with filename
attribute_with_filename = False
output_attribute_field = output_attribute
#if user did nto select an attribute field for output, set boolean to True to show that output will be attributed with filename
if output_attribute == '':
    attribute_with_filename = True
    output_attribute_field = "source_file"
    output_attribute_value = os.path.basename(intersect_polys)

printit("Creating empty line file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POLYLINE')
fields = [[xsec_id_field, 'TEXT', '', 5], ["mn_et_id", "TEXT", '', 5], [output_attribute_field, "TEXT"]]
arcpy.management.AddFields(output_line_fc, fields)

#%% 7 Convert geometry to cross section view and write to output file

printit("Creating 2d line geometry.")

if attribute_with_filename == True:
    fields = ['SHAPE@', xsec_id_field, 'mn_et_id']
elif attribute_with_filename == False:
    fields = ['SHAPE@', xsec_id_field, 'mn_et_id', output_attribute_field]

with arcpy.da.SearchCursor(output_line_fc_temp, fields) as cursor:
    for line in cursor:
        etid = line[1]
        mn_etid = line[2]
        mn_etid_int = int(mn_etid)
        #set top and bottom y coordinates for every x
        y_2d_1 = (((50 * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
        y_2d_2 = (((2300 * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
        if attribute_with_filename == False:
            output_attribute_value = line[3]
        line1_pointlist = []
        line2_pointlist = []
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
        line1_pointlist.append(pt1)
        line1_pointlist.append(pt2)
        line2_pointlist.append(pt3)
        line2_pointlist.append(pt4)
        line1_array = arcpy.Array(line1_pointlist)
        line1_geometry = arcpy.Polyline(line1_array)
        line2_array = arcpy.Array(line2_pointlist)
        line2_geometry = arcpy.Polyline(line2_array)
        #create geometry into output file
        with arcpy.da.InsertCursor(output_line_fc, ['SHAPE@', xsec_id_field, output_attribute_field, 'mn_et_id']) as cursor2d:
            cursor2d.insertRow([line1_geometry, etid, output_attribute_value, mn_etid])
            cursor2d.insertRow([line2_geometry, etid, output_attribute_value, mn_etid])
            
                     
#%% 8 Delete temporary files

printit("Deleting temporary line files.")
try: arcpy.management.Delete(output_line_fc_temp_multi)
except: printit("Unable to delete temporary file {0}".format(output_line_fc_temp_multi))
try: arcpy.management.Delete(output_line_fc_temp)
except: printit("Unable to delete temporary file {0}".format(output_line_fc_temp))

#%% 11 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))