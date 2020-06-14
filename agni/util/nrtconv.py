import datetime
import json
import copy

PRUNE_PROPS = ['latitude', 'longitude', 'acq_date', 'acq_time']


def make_geojson_point(nrt):
    lat = nrt['latitude']
    lon = nrt['longitude']

    props = {k: v for k, v in nrt.items() if k not in PRUNE_PROPS}
    props['acq_time_us'] = nrt['acq_time']

    ret = {
        'type': 'Feature',
        'properties': props,
        'geometry': {
            'type': 'Point',
            'coordinates': [lon, lat]
        }
    }
    return ret


def to_geojson(nrt_points):
    points = list(
        make_geojson_point(p) 
        for p in nrt_points
    )

    ret = {
        'type': 'FeatureCollection',
        'features': points
    }
    return ret
