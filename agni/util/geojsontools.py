import geojson

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