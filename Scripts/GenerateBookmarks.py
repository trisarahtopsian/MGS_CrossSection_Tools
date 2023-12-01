#script by Johannes Lindner, retrieved from ESRI Community webpage.
# https://community.esri.com/t5/arcgis-pro-questions/create-bookmarks-from-features/m-p/1299420



import arcpy
from pathlib import Path
def _create_bookmark_dict(in_geometry, min_dist):
    """Returns a dict defining a bookmark for the input arcpy.Geometry object."""
    e = in_geometry.extent
    d = min([e.width, e.height])
    if d < min_dist:
        buffered_geometry = in_geometry.buffer((min_dist - d) / 2)
        e = buffered_geometry.extent
    return {
        "type": "CIMBookmark",
        "location": {
            "xmin": e.XMin,
            "xmax": e.XMax,
            "ymin": e.YMin,
            "ymax": e.YMax,
            "spatialReference": {"wkid": in_geometry.spatialReference.factoryCode}
            }
        }
    
def create_bookmarks(in_features, out_path, name_field=None, dissolve_field=None, buffer_dist=None, min_dist=None):
    """Creates bookmarks from all features in a layer.
    in_features (path to feature class as str / arcpy.mp.Layer object): The input features. If this is a layer, definition queries and selection will be honored.
    out_path (str): Path of the output bkmx file.
    name_field (str): The field used to name the bookmarks. Optional, default is incrementing number.
    dissolve_field (str): The field by which to dissolve the features before creating the bookmarks. Optional, by default there is no dissolving. If both name and dissolve field are specified, the name will be ignored and the features will be named by the dissolve field.
    buffer_dist: distance by which the input features are buffered, measured in the default units of the in_feature's coordinate system, important for small features. Optional, defaults to zero.
    min_dist: minimum extent width or height, measured in the default units of the in_feature's coordinate system, important for small features. Optional, defaults to zero.
    
    """
    # dissolve features
    if dissolve_field not in [None, "", "#"]:
        in_features = arcpy.management.Dissolve(in_features, "memory/dissolve", [dissolve_field])
        if name_field not in [None, "", "#"]:
            name_field = dissolve_field
    # buffer features
    if buffer_dist is not None:
    #if buffer_dist is not None and buffer_dist > 0:
        in_features = arcpy.analysis.Buffer(in_features, "memory/buffer", buffer_dist)
    # create the bookmarks
    if min_dist is None or min_dist < 0:
        min_dist = 0
    bookmarks = []
    read_fields = ["SHAPE@"]
    if name_field not in [None, "", "#"]:
        read_fields.append(name_field)
    for i, row in enumerate(arcpy.da.SearchCursor(in_features, read_fields)):
        try:
            bm = _create_bookmark_dict(row[0], min_dist)
        except:  # eg null geometry
            continue
        if name_field not in [None, "", "#"] and row[1] is not None:
            bm["name"] = row[1]
        else:
            bm["name"] = str(i)
        bookmarks.append(bm)
    # write bkmx file
    out_dict = {"bookmarks": bookmarks}
    f = Path(str(out_path))
    f.write_text(str(out_dict))
if __name__ == "__main__":
    in_features = arcpy.GetParameter(0)
    out_path = arcpy.GetParameterAsText(1)
    name_field = arcpy.GetParameterAsText(2)
    buffer_dist = arcpy.GetParameter(3)
    #dissolve_field = arcpy.GetParameterAsText(3)
    dissolve_field = name_field
    #buffer_dist = arcpy.GetParameter(4)
    min_dist = None
    #min_dist = arcpy.GetParameter(5)
    create_bookmarks(in_features, out_path, name_field, dissolve_field, buffer_dist, min_dist)