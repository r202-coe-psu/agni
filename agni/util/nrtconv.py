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

def to_influx_point(nrt_point, tags=None, measurement=None, skip=None):
    if measurement is None:
        measurement = 'hotspot'
    if tags is None:
        tags = []
    if skip is None:
        skip = []

    influx_point = {
        'time': 0,
        'tags': {},
        'fields': {},
        'measurement': measurement,
    }

    for k, v in nrt_point.items():
        if k in skip:
            continue

        if k in tags:
            influx_point['tags'][k] = str(v)
        else:
            try:
                influx_point['fields'][k] = float(v)
            except ValueError:
                influx_point['tags'][k] = str(v)

    influx_point['time'] = int(nrt_point['acq_time'])

    return influx_point
