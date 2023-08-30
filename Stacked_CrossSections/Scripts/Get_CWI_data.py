#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Get CWI Data
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: April 2023
'''
This script retrieves CWI data and creates a well point file and stratigraphy
table inside of a stacked cross section geodatabase. It attaches et_id and
mn_et_id attributes to both files.
'''

# %% 1 Import modules

import arcpy
import sys
import os
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
    #variable retrieved by esri geoprocessing tool
    output_gdb = arcpy.GetParameterAsText(0)
    xsln_spacing = int(arcpy.GetParameterAsText(1)) #meters
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    output_gdb = r'D:\ScottXS\Script_Testing\Cross_Sections_Stacked.gdb'
    xsln_spacing = 1000 #meters
    printit("Variables set with hard-coded parameters for testing.")

#%% 3 Buffer xsln file
printit("Buffering xsln file.")
xsln = os.path.join(output_gdb, "xsln")
xsln_buffer = os.path.join(output_gdb, "xsln_buffer")
buffer_distance = xsln_spacing/2

arcpy.analysis.Buffer(xsln, xsln_buffer, buffer_distance, '', "FLAT")

#%% 4 Clip statewide wwpt file by xsln buffer

printit("Clipping statewide CWI wwpt file with xsln buffer.")
arcpy.env.overwriteOutput = True
papg = os.path.join(output_gdb, 'papg')
state_wwpt = r'J:\ArcGIS_scripts\mgs_sitepackage\layer_files\MGSDB4.mgs_cwi.mgsstaff.sde\mgs_cwi.cwi.loc_wells'
wwpt_temp = os.path.join(output_gdb, 'wwpt_temp')

arcpy.analysis.Clip(state_wwpt, xsln_buffer, wwpt_temp)

#%% Join attributes from xsln to wwpt

printit("Spatial join xsln attributes to well points.")
arcpy.env.overwriteOutput = True
wwpt = os.path.join(output_gdb, 'wwpt')
arcpy.analysis.SpatialJoin(wwpt_temp, xsln_buffer, wwpt)

printit("Creating archival wwpt file with today's date.")
#create copy of wwpt file with date for archival purposes
now = datetime.datetime.now()
month = now.strftime("%m")
day = now.strftime("%d")
year = now.strftime("%y")
date = str(month + day + year)

arcpy.conversion.FeatureClassToFeatureClass(wwpt, output_gdb, "wwpt" + date)

#%% Make strat table
printit("Clipping statewide stratigraphy data with xsln buffer.")

#I think this point file has all of the attributes needed?
state_strat_points = r'J:\ArcGIS_scripts\mgs_sitepackage\layer_files\MGSDB4.mgs_cwi.mgsstaff.sde\mgs_cwi.cwi.stratigraphy'

#clip statewide strat points
strat_points_temp = os.path.join(output_gdb, "strat_temp")
arcpy.analysis.Clip(state_strat_points, xsln_buffer, strat_points_temp)

#spatial join with xsln buffer
printit("Spatial join xsln attributes to stratigraphy points.")
strat_points_temp2 = os.path.join(output_gdb, "strat_temp2")
arcpy.analysis.SpatialJoin(strat_points_temp, xsln_buffer, strat_points_temp2)

#export strat points temp2 to geodatabase table
printit("Exporting temp stratigraphy points to geodatabase table.")
temp_table_view = "temp_table_view"
arcpy.management.MakeTableView(strat_points_temp2, temp_table_view)
strat_table = os.path.join(output_gdb, "strat_cwi")
try:
    #TableToTable is apparently depricated, but the newer version (ExportTable)
    #isn't working? This way, one of them should work.
    arcpy.conversion.ExportTable(temp_table_view, strat_table)
except:
    arcpy.conversion.TableToTable(temp_table_view, output_gdb, "strat_cwi")

#%% Delete temporary files
printit("Deleting temporary files.")
try: arcpy.management.Delete(wwpt_temp)
except: printit("Unable to delete {0}.".format(wwpt_temp))

try: arcpy.management.Delete(strat_points_temp)
except: printit("Unable to delete {0}.".format(strat_points_temp))

try: arcpy.management.Delete(strat_points_temp2)
except: printit("Unable to delete {0}.".format(strat_points_temp2))

# %% 10 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))