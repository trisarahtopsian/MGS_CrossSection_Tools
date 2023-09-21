#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Polygon Boxes (Stacked)
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: December 2022, Updated September 2023
'''
This tool will create rectangles in stacked cross section view based on
locations of polygons in mapview. The anticipated use is to show areas of 
tribal land that should not be mapped. It can also be used to create a 
polygon showing county area in xsec view, which can be used to clip cross
section data to the county boundary. The tool may have additional
applications as well.
'''

#%% 
# 1 Import modules

import arcpy
import os
import sys
import datetime
#----------------------------------------------------------------------------------------------
##!!!!! Manually change this variable if running from python IDE



run_location = "Pro"
#run_location = "IDE"



#!!!!!!!!!!!!!!
#----------------------------------------------------------------------------------------------

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement function for testing and compiled geoprocessing tool

def printit(message):
    if run_location == "Pro":
        arcpy.AddMessage(message)
    else:
        print(message)
        
        
def printerror(message):
    if run_location == "Pro":
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

#%% 
# 2 Set parameters to work in testing and compiled geopocessing tool

if run_location == "Pro":
    xsln = arcpy.GetParameterAsText(0) #mapview xsln file
    xsec_id_field = arcpy.GetParameterAsText(1) #et_id in xsln
    intersect_polys = arcpy.GetParameterAsText(2) #polygon file to intersect with xsln. county boundary, papg, etc.
    output_poly_fc = arcpy.GetParameterAsText(3) #output polygon file
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    ## REMEMBER TO CHANGE RUN LOCATION PARAMETER ABOVE
    xsln = r'D:\Ottertail_story_map\c55_dvd\spatial\Quaternary_stratigraphy.gdb\cross_section_lines' #mapview xsln file
    xsec_id_field = 'et_id' #et_id in xsln
    intersect_polys = r'D:\Ottertail_story_map\c55_dvd\spatial\Database.gdb\County_basemap\County_Boundary' #polygon file to intersect with xsln. county boundary, papg, etc.
    output_poly_fc = r'D:\Ottertail_story_map\stacked_xsec.gdb\county_polys_polygonboxestest' #output polygon file
    printit("Variables set with hard-coded parameters for testing.")

#%% 
# 3 set county relief variable (controls distance between cross sections)
#DO NOT edit this value, except in special cases
county_relief = 700
vertical_exaggeration = 50

#%% 
# 4 Data QC
#Check that surface profiles have mn_et_id field
FieldExists(xsln, 'mn_et_id')

#%% 
# Add unique ID field to temp fc so join works correctly later
printit("Adding temporary join field.")
unique_id_field = 'unique_id'

try:
    arcpy.management.AddField(intersect_polys, unique_id_field, 'LONG')
except:
    printit("Unable to add unique_id field. Field may already exist.")

if 'OBJECTID' in [field.name for field in arcpy.ListFields(intersect_polys)]:
    arcpy.management.CalculateField(intersect_polys, unique_id_field, "!OBJECTID!")
elif 'objectid' in [field.name for field in arcpy.ListFields(intersect_polys)]:
    arcpy.management.CalculateField(intersect_polys, unique_id_field, "!objectid!")
elif 'FID' in [field.name for field in arcpy.ListFields(intersect_polys)]:
    arcpy.management.CalculateField(intersect_polys, unique_id_field, "!FID!")
elif 'fid' in [field.name for field in arcpy.ListFields(intersect_polys)]:
    arcpy.management.CalculateField(intersect_polys, unique_id_field, "!fid!")
else: printerror("Error: input feature class does not contain OBJECTID or FID field. Conversion will not work without one of these fields.") 
    

#%% 
# 5 Intersect 
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

#%% 
# 6 Create empty polygon file and add fields

printit("Creating empty line file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POLYGON')
fields = [[xsec_id_field, 'TEXT', '', 5], ["mn_et_id", "TEXT", '', 5], [unique_id_field, "LONG"]]
arcpy.management.AddFields(output_poly_fc, fields)

#%% 
# 7 Convert geometry to cross section view and write to output file

printit("Creating 2d line geometry.")
fields = ['SHAPE@', xsec_id_field, 'mn_et_id', unique_id_field]

with arcpy.da.SearchCursor(output_fc_temp, fields) as cursor:
    for line in cursor:
        etid = line[1]
        mn_etid = line[2]
        mn_etid_int = int(mn_etid)
        unique_id = line[3]
        #set top and bottom y coordinates for every x
        y_2d_1 = (((50 * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
        y_2d_2 = (((2300 * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
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
        with arcpy.da.InsertCursor(output_poly_fc, ['SHAPE@', unique_id_field, xsec_id_field, 'mn_et_id']) as cursor2d:
            cursor2d.insertRow([geometry, unique_id, etid, mn_etid])
            
#%% 
# Join fields from original polygon file
arcpy.env.overwriteOutput = True
#create empty list for storing names of fields to join
join_fields = []
#list all fields in original polygons
input_fields = arcpy.ListFields(intersect_polys)
for field in input_fields:
    name = field.name
    join_fields.append(name)

#remove redundant fields from list
if "mn_et_id" in join_fields:
    join_fields.remove("mn_et_id")
if "unique_id" in join_fields:
    join_fields.remove("unique_id")
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
if "et_id" in join_fields:
    join_fields.remove("et_id")


#join unit field using the unique id
arcpy.management.JoinField(output_poly_fc, unique_id_field, intersect_polys, unique_id_field, join_fields)
           
#%% 
# 8 Delete temporary files

printit("Deleting temporary line files.")
try: arcpy.management.Delete(output_fc_temp_multi)
except: printit("Unable to delete temporary file {0}".format(output_fc_temp_multi))
try: arcpy.management.Delete(output_fc_temp)
except: printit("Unable to delete temporary file {0}".format(output_fc_temp))

#%% 
# 9 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))