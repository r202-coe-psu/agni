import datetime
import json
import copy

PRUNE_PROPS = ['latitude', 'longitude', 'acq_date', 'acq_time']

class NRTPoint:
    def __init__(self, nrt):
        self.lat = nrt['latitude']
        self.lon = nrt['longitude']

        props = {k: v for k, v in nrt.items()}
        props['acq_time_us'] = nrt['acq_time']

        for prop in PRUNE_PROPS:
            if prop in props:
                del props[prop]

        self.properties = props

    def to_dict(self):
        ret = {
            'type': 'Feature',
            'properties': self.properties,
            'geometry': {
                'type': 'Point',
                'coordinates': [self.lon, self.lat]
            }
        }
        return ret

    def __str__(self):
        return str(self.to_dict())


class NRTPointCollection:
    def __init__(self, nrt_points):
        self.points = list(NRTPoint(p).to_dict() for p in nrt_points)

    def to_dict(self):
        ret = {
            'type': 'FeatureCollection',
            'features': self.points
        }
        return ret

    def __str__(self):
        return str(self.to_dict())


def to_geojson(nrt_points):
    # this uses raw list nrt points
    points = list(
        NRTPoint(p).to_dict()
        for p in nrt_points
    )

    ret_geojson = {
        'type': 'FeatureCollection',
        'features': points
    }

    return ret_geojson
