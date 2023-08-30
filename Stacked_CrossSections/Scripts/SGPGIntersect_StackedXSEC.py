#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Cross Section / Surficial Geology Intersect (stacked)
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: October 2022
'''
This script will create feature classes that show surficial geology polygons
in stacked cross section view. It will create a point file with points at the
boundary of each surficial geology polygon. It will also create a line file that
follows land surface topography, where each line segment is labeled with the
corresponding surficial polygon.
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
    surface_profiles_3d = arcpy.GetParameterAsText(0) #dem30dnr profiles IN 3D (not xsec view). These are created by the profile tool.
    xsec_id_field = arcpy.GetParameterAsText(1) #et_id in surface profiles
    sgpg = arcpy.GetParameterAsText(2) #surficial geology polygons
    unit_field = arcpy.GetParameterAsText(3) #unit field in sgpg
    output_dir = arcpy.GetParameterAsText(4) #output geodatabase
    #output_line_fc = arcpy.GetParameterAsText(4) #output line file
    #output_point_fc = arcpy.GetParameterAsText(5) #output point file
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    surface_profiles_3d = r'D:\Pipestone_CrossSections\CrossSections_Stacked.gdb\dem30dnr_profiles3d' #dem30dnr profiles IN 3D (not xsec view). These are created by the profile tool.
    xsec_id_field = 'et_id' #et_id in surface profiles
    sgpg = r'D:\Pipestone_CrossSections\CrossSections_Stacked.gdb\sgpg3' #surficial geology polygons
    unit_field = 'Unit' #unit field in sgpg
    output_dir = r'' #output geodatabase
    #output_line_fc = r'D:\Pipestone_CrossSections\CrossSections_Stacked.gdb\sgpg_lines' #output line file
    #output_point_fc = r'D:\Pipestone_CrossSections\CrossSections_Stacked.gdb\sgpg_points' #output point file
    printit("Variables set with hard-coded parameters for testing.")

#%% 3 set county relief variable (controls distance between cross sections)
#DO NOT edit this value, except in special cases
county_relief = 700
vertical_exaggeration = 50

#%% 4 Data QC

#check to make sure profiles are 3d, not cross section view
desc = arcpy.Describe(surface_profiles_3d)
if desc.hasZ == False:
    printerror("!!ERROR!! Surface profiles do not have z 3D geometry. Select 3D profiles for this parameter and try again.")

#Check that surface profiles have mn_et_id field
FieldExists(surface_profiles_3d, 'mn_et_id')

#%% 5 Intersect sgpg with 3D surface profiles and create line
arcpy.env.overwriteOutput = True

printit("Intersecting surficial polygons with 3d surface profiles and creating temporary line file.")
#get directory where output will be saved
#output_dir = os.path.dirname(output_line_fc)
#get filename of output

sgpg_filename = os.path.basename(sgpg)
output_name = sgpg_filename + "_intersect_lines"
output_line_fc = os.path.join(output_dir, output_name)
#output_name = os.path.basename(output_line_fc)
#create name and path for temp output
output_line_fc_temp_multi = os.path.join(output_dir, output_name + "_temp_line_3d_multi")
#create temporary 3D intersect file
arcpy.analysis.Intersect([surface_profiles_3d, sgpg], output_line_fc_temp_multi, 'NO_FID', '', 'LINE')
#convert multipart to singlepart
output_line_fc_temp = os.path.join(output_dir, output_name + "_temp_line_3d")
arcpy.management.MultipartToSinglepart(output_line_fc_temp_multi, output_line_fc_temp)

#%% 6 Create empty line file and add fields

printit("Creating empty line file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POLYLINE')
fields = [[xsec_id_field, 'TEXT', '', 5], ["mn_et_id", "TEXT", '', 5], [unit_field, 'TEXT', '', 10]]
arcpy.management.AddFields(output_line_fc, fields)

#%% 7 Convert geometry to cross section view and write to output file

printit("Creating 2d line geometry.")

with arcpy.da.SearchCursor(output_line_fc_temp, ['SHAPE@', xsec_id_field, unit_field, 'mn_et_id']) as cursor:
    for line in cursor:
        etid = line[1]
        mn_etid = line[3]
        mn_etid_int = int(mn_etid)
        #etid_int = int(etid)
        unit = line[2]
        line_pointlist = []
        for vertex in line[0].getPart(0):
            x_2d = vertex.X
            #y_2d = ((vertex.Z * 0.3048) - (county_relief * etid_int)) * vertical_exaggeration
            #y_2d = ((vertex.Z * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration
            y_2d = (((vertex.Z * 0.3048) - (county_relief * mn_etid_int)) * vertical_exaggeration) + 23100000
            xy_xsecview = arcpy.Point(x_2d, y_2d)
            line_pointlist.append(xy_xsecview)
        line_array = arcpy.Array(line_pointlist)
        line_geometry = arcpy.Polyline(line_array)
        with arcpy.da.InsertCursor(output_line_fc, ['SHAPE@', xsec_id_field, unit_field, 'mn_et_id']) as cursor2d:
            cursor2d.insertRow([line_geometry, etid, unit, mn_etid])
                     
#%% 8 Delete temporary files

printit("Deleting temporary line files.")
try: arcpy.management.Delete(output_line_fc_temp_multi)
except: printit("Unable to delete temporary file {0}".format(output_line_fc_temp_multi))
try: arcpy.management.Delete(output_line_fc_temp)
except: printit("Unable to delete temporary file {0}".format(output_line_fc_temp))

#%% 9 Create empty point file and add fields
arcpy.env.overwriteOutput = True

#get filename of output
output_name = sgpg_filename + "_intersect_points"
output_point_fc = os.path.join(output_dir, output_name)
#output_name = os.path.basename(output_point_fc)

printit("Creating empty point file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POINT')
fields = [[xsec_id_field, 'TEXT', '', 5],["mn_et_id", "TEXT", '', 5], [unit_field, 'TEXT', '', 10]]
arcpy.management.AddFields(output_point_fc, fields)

#%% 10 Convert geometry to cross section view and write to output file

printit("Creating 2d point geometry.")

with arcpy.da.SearchCursor(output_line_fc, ['SHAPE@', xsec_id_field, unit_field, 'mn_et_id']) as cursor:
    for line in cursor:
        geom = line[0]
        etid = line[1]
        mn_etid = line[3]
        unit = line[2]
        start = geom.firstPoint
        end = geom.lastPoint
        #with arcpy.da.InsertCursor(output_point_fc, ['SHAPE@', xsec_id_field, unit_field]) as cursor2d:
            #cursor2d.insertRow([start, etid, unit])
            #cursor2d.insertRow([end, etid, unit])
        with arcpy.da.InsertCursor(output_point_fc, ['SHAPE@', xsec_id_field, unit_field, 'mn_et_id']) as cursor2d:
            cursor2d.insertRow([start, etid, unit, mn_etid])
            cursor2d.insertRow([end, etid, unit, mn_etid])

#%% 11 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))