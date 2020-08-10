import geojson
import utm

import shapely
import shapely.geometry
import shapely.ops

# Bounding box taken from https://gist.github.com/graydon/11198540
# format: (lon_lo, lat_lo, lon_hi, lat_hi)
TH_BBOX_EXACT = (97.3758964376, 5.69138418215, 105.589038527, 20.4178496363)
TH_BBOX = (96.3758964376, 4.69138418215, 106.589038527, 21.4178496363)

def filter_bbox(nrt_points, bbox):
    """filter NRT data by bounding box (keep points inside)

    Args:
        nrt_points (list):
            list contains NRT data points as dict
            must have latitude and longitude key
        bbox (tuple):
            tuple in format (lon1, lat1, lon2, lat2) specifying bounding box
            (lon1, lat1) is top left
            (lon2, lat2) is bottom right

    Returns:
        list of dict with points within bbox
    """
    def filter_pred(point): 
        min_lon = bbox[0]
        max_lon = bbox[2]

        min_lat = bbox[1]
        max_lat = bbox[3]

        lon = point['longitude']
        lat = point['latitude']

        return (min_lon <= lon <= max_lon) and (min_lat <= lat <= max_lat)

    nrt_filtered = list(filter(filter_pred, nrt_points))
    return nrt_filtered

BUFFER_DISTANCE_M = 375

def filter_shape(nrt_points, shape):
    # shape as geojson FeatureCollection

    def latlon2utm(c):
        east, north, zonen, zonel = utm.from_latlon(c[1], c[0])
        return (east, north)

    def shapely_utm2latlon(x, y, z=None):
        lat, lon = utm.to_latlon(x, y, 47, northern=True, strict=False)
        return (lon, lat)

    # convert to UTM (zone 47N) for buffer
    geojson.utils.map_tuples(latlon2utm, shape)

    # make shapes
    shp_features = shape['features']
    shp_shapely = [
        shapely.geometry.shape(f['geometry'])
        for f in shp_features
    ]

    roi_shape = shapely.geometry.MultiPolygon(shp_shapely)
    roi_shape = roi_shape.buffer(BUFFER_DISTANCE_M)

    # convert coords back after buffer
    roi_shape = shapely.ops.transform(shapely_utm2latlon, roi_shape)

    # filter
    retlist = []
    for point in nrt_points:
        p = shapely.geometry.Point(point['longitude'], point['latitude'])
        if roi_shape.contains(p):
            retlist.append(point)

    return retlist


