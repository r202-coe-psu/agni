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
        self.__weighted_avg = None
        self.weights = None
        self.counts = None
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
            xdata, ydata = self.UTM_TF.transform(xdata.to_list(),
                                                 ydata.to_list())
        except KeyError:
            xdata = pd.Series([])
            ydata = pd.Series([])
        return xdata, ydata

    def fit(self, data, xkey, ykey, wkey=None):
        """ fit data to make grid """
        if self.bounds is None:
            raise ValueError("bounding area unset")

        data_ = pd.DataFrame(data)

        weights = wkey is not None

        xdata, ydata = self._prepare_data(data_, xkey=xkey, ykey=ykey)
        self._fit_count(xdata=xdata, ydata=ydata)

        if weights:
            try:
                wdata = data_[wkey]
            except KeyError:
                wdata = pd.Series([])
            self._fit_weight(xdata=xdata, ydata=ydata, wdata=wdata)
            self._calc_weighted_average()
        else:
            self.weights = None


    def _fit_count(self, xdata, ydata):
        count, xedge, yedge = np.histogram2d(
            x=xdata, y=ydata, bins=self.edges,
        )
        self.counts = (count.T).astype(int)

    def _fit_weight(self, xdata, ydata, wdata):
        weight_grid, xedge, yedge = np.histogram2d(
            x=xdata, y=ydata, bins=self.edges,
            weights=wdata
        )
        self.weights = (weight_grid.T).astype(float)

    def _calc_weighted_average(self):
        wg = np.divide(
            self.weights, self.counts,
            out=np.zeros_like(self.counts.astype(float)),
            where=(self.counts != 0)
        )
        wg[np.isnan(wg)] = 0
        self.__weighted_avg = wg

    @property
    def grid(self):
        if self.weights is not None:
            return self.__weighted_avg
        return self.counts

    def _create_cell_rect(self, x, y):
        elons = self.edges[0]
        elats = self.edges[1]

        west, east = elons[x:x+2]
        south, north = elats[y:y+2]

        bounds = [float(x) for x in [west, south, east, north]]
        return gjtool.rect(*bounds) 

    def min(self, nonzero=True):
        g = self.grid
        return float(np.min(g[np.nonzero(g)]))
    
    def max(self, nonzero=True):
        g = self.grid
        return float(np.max(g[np.nonzero(g)]))

    def repr_geojson(self, keep_zero=False, mode='count'):
        elons = self.edges[0]
        elats = self.edges[1]

        modegrid = {
            'count': self.counts,
            'sum': self.weights,
            'average': self.grid
        }

        out_rects = []
        for x in range(len(elons)-1):
            for y in range(len(elats)-1):
                data = float(modegrid[mode][y, x])
                if not keep_zero and data == 0:
                    continue

                rect = self._create_cell_rect(x, y)
                rect = gjtool.reproject(rect, self.GPS_TF)

                feature = geojson.Feature(
                    geometry=rect,
                    properties={
                        'value': data,
                        'grid_index': [int(y), int(x)]
                    },
                )

                out_rects.append(feature)

        out_features = geojson.FeatureCollection(out_rects)
        out_features['info'] = {
            'min_value': self.min(),
            'max_value': self.max(),
            'shape': list(self.grid.shape),
            'mode': mode
        }
        return out_features

def loads(hmap_gj: dict):
    """ UNIMPLEMENTED: reconstruct hmap from serialized hmap geojson """
    pass

def dumps(hmap: NRTHeatmap):
    return hmap.repr_geojson()
