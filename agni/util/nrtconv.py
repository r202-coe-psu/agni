import geojson

PRUNE_PROPS = ['latitude', 'longitude', 'acq_date', 'acq_time']

def point_geojson(nrt):
    lat = nrt['latitude']
    lon = nrt['longitude']

    props = {k: v for k, v in nrt.items() if k not in PRUNE_PROPS}

    point = geojson.Point(coordinates=(lon, lat))
    ret = geojson.Feature(geometry=point, properties=props)
    return ret

def to_geojson(nrt_points):
    points = list(
        point_geojson(p)
        for p in nrt_points
    )

    ret = geojson.FeatureCollection(points)
    return ret

def to_influx_json(
        point, measure, timekey, 
        tags=None, skip=None, auto_tags=False,
        precision=None
):

    """ reshape NRT data to json compatible for InfluxDB usage

        Args:
            point (dict):
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
            skip_time (bool):
                skip including time column in timekey in data points
                timekey column is always skipped unless this option is false

        Return:
            point (dict):
                data point compatible with InfluxDB python client
    """

    if tags is None:
        tags = []
    if skip is None:
        skip = [timekey]

    influx_point = {
        'time': None,
        'tags': {},
        'fields': {},
        'measurement': measure,
    }

    if auto_tags:
        for k, v in point.items():
            if k in skip or k == timekey:
                continue

            try:
                _ = float(v)
            except ValueError:
                k not in tags and tags.append(k)

    for k, v in point.items():
        if k in skip or k == timekey:
            continue

        if k in tags:
            influx_point['tags'][k] = str(v)
        else:
            influx_point['fields'][k] = float(v)

    if precision is None or precision.casefold() == 'rfc3339':
        influx_point['time'] = point[timekey].isoformat()
    elif precision in ['h','m','s','ms','u','ns']:
        influx_point['time'] = int(point[timekey])
    else:
        raise TypeError('Cannot parse time data')

    return influx_point

def to_influx_line(
        point, measure, timekey, 
        tags=None, skip=None, auto_tags=False,
        precision=None
):

    point = to_influx_json(
        point, measure, timekey, tags, skip, auto_tags, precision
    )

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
