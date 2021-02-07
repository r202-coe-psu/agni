import pyproj
import geojson

import numpy as np
import pandas as pd

from ..util import ranger
from ..util import geojsontools as gjtool

_PROJ_LONLAT = pyproj.Proj('epsg:4326') # lat, lon
_PROJ_UTM47N = pyproj.Proj('epsg:32647') # UTM 47N, as appeared in shapefiles
# coordinate transformers
_UTM_TF = pyproj.Transformer.from_proj(
    _PROJ_LONLAT, _PROJ_UTM47N, always_xy=True
)
_GPS_TF = pyproj.Transformer.from_proj(
    _PROJ_UTM47N, _PROJ_LONLAT, always_xy=True
)

class NRTHeatmap:
    UTM_TF = _UTM_TF
    GPS_TF = _GPS_TF
    def __init__(self, step=None, bounds=None):
        self.grid = None
        self.edges = None
        self.step = step
        self.bounds = bounds
        if step and bounds:
            self._regen_edges()

        self.info = {
            'start': None,
            'end': None,
            'src': None
        }

    def _regen_edges(self):
        bounds = self.bounds
        area_lons = bounds[0], bounds[2]
        area_lats = bounds[1], bounds[3]
        area_x, area_y = self.UTM_TF.transform(area_lons, area_lats)
        bl = (area_x[0], area_y[0])
        tr = (area_x[1], area_y[1])

        lons_u = ranger.closed_range(bl[0], tr[0], self.step)
        lats_u = ranger.closed_range(bl[1], tr[1], self.step)

        self.edges = (lons_u, lats_u)

    def set_step(self, step):
        self.step = step
        self._regen_edges()

    def set_bounds(self, bounds):
        self.bounds = bounds
        self._regen_edges()

    def set_bounds_str(self, boundstr):
        bounds = [float(n) for n in boundstr.split(',')]
        self.set_bounds(bounds)

    def _prepare_data(self, data, xkey, ykey):
        try:
            xdata = data[xkey]
            ydata = data[ykey]
        except KeyError:
            xdata = pd.Series([0])
            ydata = pd.Series([0])
        xdata, ydata = self.UTM_TF.transform(xdata.to_list(), ydata.to_list())
        return xdata, ydata

    def fit(self, data, xkey, ykey, wkey=None, density=False):
        """ fit data to make grid """
        if self.bounds is None:
            raise ValueError("bounding area unset")

        data_ = pd.DataFrame(data)

        weights = wkey is not None
        weights_data = None
        if weights:
            weights_data = data_[wkey]

        xdata, ydata = self._prepare_data(data_, xkey=xkey, ykey=ykey)
        count, xedge, yedge = np.histogram2d(
            x=xdata, y=ydata, bins=self.edges,
            weights=(weights_data if weights else None),
            density=density
        )
        self.grid = (count.T).astype(float)

    def _create_cell_rect(self, x, y):
        elons = self.edges[0]
        elats = self.edges[1]

        west, east = elons[x:x+2]
        south, north = elats[y:y+2]

        bounds = [float(x) for x in [west, south, east, north]]
        return gjtool.rect(*bounds) 

    def repr_geojson(self, keep_zero=True):
        elons = self.edges[0]
        elats = self.edges[1]

        out_rects = []
        for x in range(len(elons)-1):
            for y in range(len(elats)-1):
                data = float(self.grid[y, x])
                if not keep_zero and data == 0:
                    continue

                rect = self._create_cell_rect(x, y)
                rect = gjtool.reproject(rect, self.GPS_TF)

                feature = geojson.Feature(
                    geometry=rect,
                    properties={
                        'count': data,
                        'grid_index': [int(y), int(x)]
                    },
                )

                out_rects.append(feature)

        out_features = geojson.FeatureCollection(out_rects)
        out_features['info'] = {
            'min_count': float(self.grid.min()),
            'max_count': float(self.grid.max()),
            'shape': list(self.grid.shape)
        }
        return out_features

def loads(hmap_gj: dict):
    """ UNIMPLEMENTED: reconstruct hmap from serialized hmap geojson """
    pass

def dumps(hmap: NRTHeatmap):
    return hmap.repr_geojson()
