#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Get CWI Data
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: November 2023
'''
This script gets CWI data for a buffered cross section line file
and creates a well point file and strat table.
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
    output_gdb = arcpy.GetParameterAsText(0)
    xsln = arcpy.GetParameterAsText(1)
    buffer_distance = int(arcpy.GetParameterAsText(2)) #meters
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    output_gdb = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb'
    xsln = r'D:\Cross_Section_Programming\112123\script_testing\Steele_Script_Testing.gdb\xsln'
    buffer_distance = 500 #meters, half of xsln spacing
    printit("Variables set with hard-coded parameters for testing.")


#%% 3 Buffer xsln file
printit("Buffering xsln file.")

xsln_buffer = os.path.join(output_gdb, "xsln_buffer")
arcpy.analysis.Buffer(xsln, xsln_buffer, buffer_distance, '', "FLAT")

#%% 4 Clip statewide wwpt file by xsln buffer

printit("Clipping statewide CWI wwpt file with xsln buffer.")
arcpy.env.overwriteOutput = True

state_wwpt = r'J:\ArcGIS_scripts\mgs_sitepackage\layer_files\MGSDB5.mgs_cwi.mgsstaff.sde\mgs_cwi.cwi.loc_wells'
wwpt_temp = os.path.join(output_gdb, 'wwpt_temp')

arcpy.analysis.Clip(state_wwpt, xsln_buffer, wwpt_temp)

#%% 
# 4 Join attributes from xsln to wwpt

printit("Spatial join xsln attributes to well points.")
arcpy.env.overwriteOutput = True
wwpt = os.path.join(output_gdb, 'wwpt')
arcpy.analysis.SpatialJoin(wwpt_temp, xsln_buffer, wwpt, 'JOIN_ONE_TO_MANY')

'''
printit("Creating archival wwpt file with today's date.")
#create copy of wwpt file with date for archival purposes
now = datetime.datetime.now()
month = now.strftime("%m")
day = now.strftime("%d")
year = now.strftime("%y")
date = str(month + day + year)

arcpy.conversion.FeatureClassToFeatureClass(wwpt, output_gdb, "wwpt" + date)
'''

#%% 
# 5 Make strat table
printit("Clipping statewide stratigraphy data with xsln buffer.")

#I think this point file has all of the attributes needed?
state_strat_points = r'J:\ArcGIS_scripts\mgs_sitepackage\layer_files\MGSDB5.mgs_cwi.mgsstaff.sde\mgs_cwi.cwi.stratigraphy'

#clip statewide strat points
strat_points_temp = os.path.join(output_gdb, "strat_temp")
arcpy.analysis.Clip(state_strat_points, xsln_buffer, strat_points_temp)

#spatial join with xsln buffer
printit("Spatial join xsln attributes to stratigraphy points.")
strat_points_temp2 = os.path.join(output_gdb, "strat_temp2")
arcpy.analysis.SpatialJoin(strat_points_temp, xsln_buffer, strat_points_temp2, 'JOIN_ONE_TO_MANY')

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

#%% 
# 6 Delete temporary files
printit("Deleting temporary files.")
try: arcpy.management.Delete(wwpt_temp)
except: printit("Unable to delete {0}.".format(wwpt_temp))

try: arcpy.management.Delete(strat_points_temp)
except: printit("Unable to delete {0}.".format(strat_points_temp))

try: arcpy.management.Delete(strat_points_temp2)
except: printit("Unable to delete {0}.".format(strat_points_temp2))

# %% 
# 7 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))
# %%
