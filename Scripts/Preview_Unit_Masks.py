#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Preview Unit Masks
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: May 2024
'''
This script will allow geologists to preview how their
unit masks will look in map view with the current draft
of their stratlines. If also has an option to merge in
surficial geology polygons and correct masks for surficial
geology based on unit order.
'''

# %%
# 1 Import modules and define functions

import arcpy
import os
#import numpy
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
#%% 2 Set parameters to work in testing and compiled geopocessing tool

if run_location == "Pro":
    #variable = arcpy.GetParameterAsText(0)
    strat_all_orig = arcpy.GetParameterAsText(0)
    stratline_unit_field = arcpy.GetParameterAsText(1)
    xsln_file = arcpy.GetParameterAsText(2)
    ref_poly = arcpy.GetParameterAsText(3)
    overlap = int(arcpy.GetParameterAsText(4)) #meters, default = 10
    xs_spacing = int(arcpy.GetParameterAsText(5)) #meters, default = 1000
    smooth_tol = int(arcpy.GetParameterAsText(6)) #default = 1000
    scratch_folder = arcpy.GetParameterAsText(7)
    out_gdb = arcpy.GetParameterAsText(8)
    delete_temp_files = arcpy.GetParameter(9) #boolean, true to delete temporary files, false to keep them
    merge_sgpg = arcpy.GetParameter(10) #boolean
    #parameters below only appear if merge_sgpg is True
    sgpg = arcpy.GetParameterAsText(11)
    sgpg_unit_field = arcpy.GetParameterAsText(12)
    unitlist_txt = arcpy.GetParameterAsText(13)

    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    strat_all_orig = r'D:\Masks_scripting\Pipestone_editing.gdb\strat_all_merge'
    stratline_unit_field = 'unit'
    xsln_file = r'D:\Masks_scripting\Pipestone_xsec.gdb\xsln'
    ref_poly = r'D:\Masks_scripting\Pipestone_xsec.gdb\poly_ref'
    overlap = 10 #meters, default = 10
    xs_spacing = 1000 #meters, default = 1000
    smooth_tol = 1000 #default = 1000
    scratch_folder = r'D:\Masks_scripting\scratch'
    out_gdb = r'D:\Masks_scripting\test_no_merge.gdb'
    delete_temp_files = False #boolean, true to delete temporary files, false to keep them
    merge_sgpg = False #boolean
    #parameters below only appear if merge_sgpg is True
    sgpg = r'D:\Masks_scripting\Pipestone_xsec.gdb\sgpg'
    sgpg_unit_field = 'unit'
    unitlist_txt = r'D:\Masks_scripting\unitlist.txt'
    printit("Variables set with hard-coded parameters for testing.")



#%% 
#3 Define additional parameters and check that they exist

xsln_etid_field = 'et_id'
stratline_etid_field = 'et_id'

FieldExists(xsln_file, xsln_etid_field)
FieldExists(xsln_file, 'mn_et_id')

#create scratch gdb
arcpy.env.overwriteOutput = True
scratch_gdb = os.path.join(scratch_folder, 'Unit_masks_preview_temp.gdb')
if arcpy.Exists(scratch_gdb):
    printit("Deleting existing scratch gdb and making a new one.")
    arcpy.management.Delete(scratch_gdb)
arcpy.management.CreateFileGDB(scratch_folder, 'Unit_masks_preview_temp.gdb')

#%% 4 Set mapview spatial reference based on xsln file

spatialref = arcpy.Describe(xsln_file).spatialReference
if spatialref.name == "Unknown":
    printerror("{0} file has an unknown spatial reference. Continuing may result in errors.".format(os.path.basename(xsln_file)))
else:
    printit("Spatial reference set as {0} to match {1} file.".format(spatialref.name, os.path.basename(xsln_file)))

#%%
# 5 Create feature dataset for storing mask previews. Do not create if it already exists

out_fd = os.path.join(out_gdb, "Unit_mask_previews")
printit("Output feature dataset is {0}".format(out_fd))

if not arcpy.Exists(out_fd):
    printit("Output feature dataset does not yet exist. Creating.")
    arcpy.management.CreateFeatureDataset(out_gdb, "Unit_mask_previews", spatialref)

#make date code to append to file name
today = datetime.datetime.today()
#grab only last 2 digits of the year
year = today.strftime('%Y')[2:4]
date_code = today.strftime('%m%d') + year

out_fc = os.path.join(out_fd, "Unit_masks_draft_" + date_code)
if run_location == "Pro":
    # define derived output parameter. This is will make it automatically add the output to a map.
    arcpy.SetParameterAsText(14, out_fc)

#%%
# 6 create unit list based on text file if user wants to join sgpg
if merge_sgpg == True:
    printit("Creating unit list based on text file.")
    txt_file = open(unitlist_txt).readlines()
    #create empty list for appending unit names
    unitlist = []
    #remove "\n" line break from each unit name and add to empty list
    for units in txt_file:
        replace = units.replace("\n", "")
        unitlist.append(replace)
    #remove extra spaces and tabs from list items
    i = 0
    while i < len(unitlist):
        unitlist[i] = unitlist[i].strip()
        i += 1
    #remove blank list items
    while '' in unitlist:
        unitlist.remove('')
    
    #check for duplicates in unit list
    def duplicatecheck(list):
        if len(set(list)) == len(list):
            printit("There are no duplicates in text file.") 
        else:
            printerror("!!ERROR!! Unit list has duplicates. Please edit to remove and then retry.") #add error
            
    duplicatecheck(unitlist)
    printit("Unit list is {0}".format(unitlist))

#%%
# 7 check to make sure stratline unit attributes are populated, and that they match sgpg if user wants to join sgpg
stratline_unitlist = []
no_unit_count = 0
with arcpy.da.UpdateCursor(strat_all_orig, [stratline_unit_field]) as cursor:
    for row in cursor:
        unit = row[0].strip() #strip off spaces in attribute
        if unit == '':
            no_unit_count += 1
            continue
        if unit is None: #check for null value too
            no_unit_count += 1
            continue
        #add unit to stratline unitlist
        if unit not in stratline_unitlist:
            stratline_unitlist.append(unit)
        #if unit attribute had spaces, update the row so it doesn't
        if unit != row[0]:
            row[0] = unit
            cursor.updateRow(row)
        
if no_unit_count > 0:
    printwarning("!!WARNING!!: {0} lines in stratline do not have a unit attribute. Polygons will be created but will have no associated unit.".format(no_unit_count))

if merge_sgpg == True:
    #populate sgpg unitlist
    sgpg_unitlist = []
    with arcpy.da.SearchCursor(sgpg, [sgpg_unit_field]) as cursor:
        for row in cursor:
            unit = row[0]
            if unit not in sgpg_unitlist:
                sgpg_unitlist.append(unit)
    
    #check that units in sgpg and stratlines match units in unitlist
    for unit in stratline_unitlist:
        if unit not in unitlist:
            printwarning("!!WARNING!! Unit {0} in stratlines does not match any units in the unitlist. If this is a surficial unit, the surficial geology correction will not work correctly.".format(unit))
    for unit in sgpg_unitlist:
        if unit not in unitlist:
            printwarning("!!WARNING!! Unit {0} in sgpg does not match any units in the unitlist. The surficial geology correction will not work correctly.".format(unit))

#%% 
# 8 Join et_id and mn_et_id to stratline file using spatial join with refpoly
printit("Creating temporary stratlines file with et_id and mn_et_id joined.")
strat_all_join = os.path.join(scratch_gdb, "strat_all_join")
arcpy.analysis.SpatialJoin(strat_all_orig, ref_poly, strat_all_join)

#%% 9 Create output file and add fields
arcpy.env.overwriteOutput = True
printit("Creating empty mapview stratlines file.")

arcpy.management.CreateFeatureclass(out_fd, "Stratlines_mapview_" + date_code, 'POLYLINE', '', '', '', spatialref)
stratlines_mapview = os.path.join(out_fd, 'Stratlines_mapview_' + date_code)

output_fields = [[stratline_etid_field, 'TEXT'], [stratline_unit_field, 'TEXT'], ["mn_et_id", "TEXT"]]

arcpy.management.AddFields(stratlines_mapview, output_fields)
if run_location == "Pro":
    # define derived output parameter. This is will make it automatically add the output to a map.
    arcpy.SetParameterAsText(15, stratlines_mapview)


#%% 10 Convert stratline points to real xy

printit("Converting stratline vertex points to mapview and adding to output file.")

#loop through cross sections
with arcpy.da.SearchCursor(xsln_file, ['SHAPE@', xsln_etid_field, "mn_et_id"]) as xsln_cursor:
    for line in xsln_cursor:
        etid = line[1]
        mn_etid = line[2]
        etid_int = int(etid)
        if etid_int % 5 == 0:
            printit("Working on stratlines for line {0}.".format(etid))
        pointlist = []
        for vertex in line[0].getPart(0):
            # List vertices in xsln
            xsln_y = vertex.Y
            pointlist.append(xsln_y)
        if len(pointlist) > 2:
            printit("Warning: xsln {0} has more than 2 vertices. It may not be straight East/West, and points will not convert correctly".format(etid))
        #throw an error if xsln is not straight east/west
        first_y = pointlist[0]
        last_y = pointlist[-1]
        
        if first_y != last_y:
            printerror("Error: xsln {0} vertices do not have the same y coordinate. Points will not plot correctly.".format(etid))
        # y coordinate will be the same for every vertex in this xsln
        y = first_y
        where_clause = "{0}='{1}'".format(stratline_etid_field, etid)
        #search through strat vertex points along current xsln
        with arcpy.da.SearchCursor(strat_all_join, ['SHAPE@', stratline_unit_field], where_clause) as strat_cursor:
            for stratline in strat_cursor:
                unit = stratline[1]
                line_pointlist = []
                for vertex in stratline[0].getPart(0):
                    x = vertex.X
                    #calculate mapview coordinates
                    #x coordinate stays the same
                    new_x = x
                    #y coordinate is the same as the xsln y coordinate
                    new_y = y
                    point = arcpy.Point(new_x, new_y)
                    line_pointlist.append(point)
                line_array = arcpy.Array(line_pointlist)
                line_geom = arcpy.Polyline(line_array, spatialref)
                with arcpy.da.InsertCursor(stratlines_mapview, ['SHAPE@', stratline_etid_field, stratline_unit_field, 'mn_et_id']) as out_cursor:
                    out_cursor.insertRow([line_geom, etid, unit, mn_etid]) 

#%% 11 set two buffer distances based on xs spacing and overlap defined in parameters 

buff_1 = int(xs_spacing / 10)
buff_2 = int((xs_spacing / 2 ) + overlap)

#define filenames for temp outputs
buff_1_filename = "buff_" + str(buff_1)
buff_1_fc = os.path.join(scratch_gdb, buff_1_filename)

buff_2_filename = "buff_" + str(buff_2)
buff_2_fc = os.path.join(scratch_gdb, buff_2_filename)

#%% 12 Buffer mapview stratlines at narrow (buff_1) and wide (buff_2) distance and dissolve by unit

printit("Buffering mapview stratlines at {0} and {1} meters.".format(buff_1, buff_2))
arcpy.analysis.Buffer(stratlines_mapview, buff_1_fc, buff_1, '', 'FLAT', 'LIST', 'unit')
arcpy.analysis.Buffer(stratlines_mapview, buff_2_fc, buff_2, '', 'FLAT', 'LIST', 'unit')

#%% 13 Smooth wide buffer

printit("Smoothing wide buffer.")
buff_2_smooth_filename = buff_2_filename + "_smooth"
buff_2_smooth = os.path.join(scratch_gdb, buff_2_smooth_filename)

arcpy.cartography.SmoothPolygon(buff_2_fc, buff_2_smooth, 'PAEK', smooth_tol)

#%% 14 Erase smoothed buffer with buff 1 to remove smoothed area along stratline

printit("Erasing smoothed polygons along cross section lines.")
buff_2_erase_filename = buff_2_filename + "_erase"
buff_2_erase = os.path.join(scratch_gdb, buff_2_erase_filename)

arcpy.analysis.Erase(buff_2_smooth, buff_1_fc, buff_2_erase)

#%% 15 Merge erased buff2 with buff1

printit("Merging erased polygons with narrow buffer.")
buff_merge = os.path.join(scratch_gdb, 'buff_merge')
arcpy.management.Merge([buff_1_fc, buff_2_erase], buff_merge)

#%% 16 Dissolve by unit and save as output fc if merge_sgpg == False

printit("Dissolving polygons by unit.")
if merge_sgpg == True:
    buff_diss = os.path.join(scratch_gdb, 'buff_diss')
elif merge_sgpg == False:
    buff_diss = out_fc

arcpy.management.Dissolve(buff_merge, buff_diss, 'unit', '', 'SINGLE_PART')

#%% 17 Merge and dissolve with sgpg if merge_sgpg === True

if merge_sgpg == True:
    printit("Merging with sgpg and dissolving by unit.")
    sgpg_merge = os.path.join(scratch_gdb, 'sgpg_merge')
    arcpy.management.Merge([sgpg, buff_diss], sgpg_merge)
    buff_diss_merge = os.path.join(scratch_gdb, 'buff_diss_merge')
    arcpy.management.Dissolve(sgpg_merge, buff_diss_merge, 'unit', '', 'SINGLE_PART')


    # correct for surficial geology polygons
    # Create unit list for only surficial units
    printit("Correcting masks for surficial geology.")
    surface_unitlist = []
    for unit in unitlist:
        if unit in sgpg_unitlist:
            surface_unitlist.append(unit)

    printit("Surface unitlist is {0}".format(surface_unitlist))

    #create temp copy of sgpg
    #polygons will be sequentially deleted from this file as the loop moves through the list
    sgpg_temp = os.path.join(scratch_gdb, "sgpg_temp")
    arcpy.conversion.ExportFeatures(sgpg, sgpg_temp)

    #create blank output masks file and add fields based on existing fields in buff_diss_merge
    out_path = os.path.dirname(out_fc)
    out_name = os.path.basename(out_fc)
    printit("Creating output feature class {0}.".format(out_fc))
    arcpy.management.CreateFeatureclass(out_path, out_name, 'POLYGON', buff_diss_merge, '', '', spatialref)

    #loop through surface units from top top to bottom
    #for each unit, delete the sgpg polygons from the temp file for that unit
    #then, use the temp sgpg polygons to erase portions of the mask with underlying units at the surface
    #create a temp output mask file as the output from the erase
    #append the temp output mask to the main output file

    #make a feature layer of the temp sgpg
    sgpg_temp_lyr = "sgpg_temp_lyr"
    arcpy.management.MakeFeatureLayer(sgpg_temp, sgpg_temp_lyr)

    printit("Correcting surface units with surficial geology.")
    for unit in surface_unitlist:
        printit("Working on {0}.".format(unit))
        where_clause = "{0}='{1}'".format(sgpg_unit_field, unit)
        #select sgpg polygons that have current unit in the unit field
        arcpy.management.SelectLayerByAttribute(sgpg_temp_lyr, '', where_clause)
        #delete selected current unit polygons from temp sgpg
        arcpy.management.DeleteFeatures(sgpg_temp_lyr)
        #clear selection
        arcpy.management.SelectLayerByAttribute(sgpg_temp_lyr, 'CLEAR_SELECTION')
        #make feature layer of current unit mask
        where_clause = "{0}='{1}'".format(stratline_unit_field, unit)
        mask_lyr = "mask_lyr" + unit
        arcpy.management.MakeFeatureLayer(buff_diss_merge, mask_lyr, where_clause)
        #use the temp sgpg file to erase portions of the current unit mask
        temp_mask_path = os.path.join(scratch_gdb, unit + "_mask_temp")
        arcpy.analysis.Erase(mask_lyr, sgpg_temp_lyr, temp_mask_path)
        #append features from temp mask file to output mask file
        arcpy.management.Append(temp_mask_path, out_fc)
        #delete temporary mask layer
        arcpy.management.Delete(mask_lyr)

    #copy over subsurface unit masks
    printit("Copying subsurface unit masks to the output.")
    #make a list of subsurface units
    sub_unitlist = []
    for unit in unitlist:
        if unit not in sgpg_unitlist:
            sub_unitlist.append(unit)

    printit("Subsurface units are {0}".format(sub_unitlist))

    #make temporary feature layer of original unit masks
    mask_temp_lyr = "mask_temp_lyr"
    arcpy.management.MakeFeatureLayer(buff_diss_merge, mask_temp_lyr)

    #select each subsurface unit and append to the output feature class
    for unit in sub_unitlist:
        #printit("Working on {0}.".format(unit))
        where_clause = "{0}='{1}'".format(stratline_unit_field, unit)
        #select masks that have current unit in the unit field
        arcpy.management.SelectLayerByAttribute(mask_temp_lyr, '', where_clause)
        #append selected polygons to the output
        arcpy.management.Append(mask_temp_lyr, out_fc)

    #delete temporary mask layer
    arcpy.management.Delete(mask_temp_lyr)


#%% 13 Delete scratch gdb
if delete_temp_files == True:
    printit("Deleting scratch gdb.")
    try: arcpy.management.Delete(scratch_gdb)
    except: printit("Unable to delete scratch gdb {0}".format(scratch_gdb))

#%%  Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))
