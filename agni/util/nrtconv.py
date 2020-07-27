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

def to_influx_json(nrt_point, measure, timekey, tags=None, skip=None):
    """ reshape NRT data to json compatible for InfluxDB usage

        Args:
            nrt (dict):
                NRT data point as dict
            measure (str):
                InfluxDB measure name
            timekey (str):
                name of key in dict which contains timestamp
                as unix epoch microseconds
            tags (list of str):
                list of keys within dict which should be made into tags
                instead of fields
            skip (list of str):
                list of keys for values to skip processing

        Return:
            point (dict):
                data point compatible with InfluxDB python client
    """

    if tags is None:
        tags = []
    if skip is None:
        skip = []

    influx_point = {
        'time': 0,
        'tags': {},
        'fields': {},
        'measurement': measure,
    }

    for k, v in nrt_point.items():
        if k in skip or k == timekey:
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

def to_influx_line(nrt, measure, timekey, tags=None, skip=None):
    point = to_influx_json(nrt, measure, timekey, tags, skip)

    # formatting them into a line protocol format
    fields_out = (
        '='.join([str(k), str(v)])
        for k, v in point['fields'].items()
    )

    tags_out = (
        '='.join([str(k), str(v)])
        for k, v in point['tags'].items()
    )

    lineprot_str = "{measure},{tags} {fields} {time}".format(
        measure=measure,
        tags = ','.join(tags_out),
        fields=','.join(fields_out),
        time=str(point['time'])
    )

    return lineprot_str
