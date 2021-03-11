import geojson
import geojson.utils

import pyproj

PROJ_LONLAT = pyproj.Proj('epsg:4326') # lat, lon
PROJ_UTM47N = pyproj.Proj('epsg:32647') # UTM 47N, as appeared in shapefiles
# coordinate transformers
UTM_TF = pyproj.Transformer.from_proj(
    PROJ_LONLAT, PROJ_UTM47N, always_xy=True
)
GPS_TF = pyproj.Transformer.from_proj(
    PROJ_UTM47N, PROJ_LONLAT, always_xy=True
)

def reproject(geojson_, transformer):
    reproj_geojson = geojson.utils.map_tuples(
        lambda c: transformer.transform(*c),
        geojson_
    )
    return reproj_geojson

def rect(west, south, east, north):
    tl = (west, north)
    tr = (east, north)
    bl = (west, south)
    br = (east, south)

    poly = [bl, br, tr, tl, bl]
    rect = geojson.Polygon([poly])
    return rect


def rect_corner(lower_corner, upper_corner):
    west, east = lower_corner[0], upper_corner[0]
    south, north = lower_corner[1], upper_corner[1]

    return rect(west, south, east, north)
