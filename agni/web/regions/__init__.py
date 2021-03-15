import pathlib

try:
    import importlib.resources as pkg_res
except ImportError:
    import importlib_resources as pkg_res

import geojson

def region_choices():
    regions = __name__

    region_list = [ 
        roi
        for roi in pkg_res.contents(regions) 
        if 'geojson' in pathlib.Path(roi).suffix
    ]
    roi_list = []
    for roi_file in region_list:
        # load geojson
        roi_str = pkg_res.read_text(regions, roi_file)
        roi_geojson = geojson.loads(roi_str)
        props = roi_geojson['features'][0]['properties']
        
        # get label and id names
        if 'human_name' in props:
            roi_label = props['human_name']
            roi_def = props['name']
        else:
            roi_label = props['name']
            roi_def = pathlib.Path(roi_file).stem
        roi_list.append([roi_def, roi_label])
    return roi_list