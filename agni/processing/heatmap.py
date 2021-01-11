import math

import pyproj
import geojson

import numpy as np
import pandas as pd

from agni.util import nprange

class NRTHeatmap:
    _PROJ_LONLAT = pyproj.Proj('epsg:4326') # lat, lon
    _PROJ_UTM47N = pyproj.Proj('epsg:32647') # UTM 47N, as appeared in shapefiles

    # coordinate transformers
    UTM_TF = pyproj.Transformer.from_proj(
        _PROJ_LONLAT, _PROJ_UTM47N, always_xy=True
    )
    GPS_TF = pyproj.Transformer.from_proj(
        _PROJ_UTM47N, _PROJ_LONLAT, always_xy=True
    )
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

        lons_u = nprange.closed_range(bl[0], tr[0], self.step)
        lats_u = nprange.closed_range(bl[1], tr[1], self.step)

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

    def fit(self, data, xkey, ykey):
        """ fit data to make grid """
        if self.bounds is None:
            raise ValueError("bounding area unset")

        data = pd.DataFrame(data, copy=True)
        self.map_data = data
        try:
            xdata = data[xkey]
            ydata = data[ykey]
        except KeyError:
            xdata = pd.Series([0])
            ydata = pd.Series([0])
        xdata, ydata = self.UTM_TF.transform(xdata.to_list(), ydata.to_list())

        count, xedge, yedge = np.histogram2d(x=xdata, y=ydata, bins=self.edges)
        self.grid = (count.T).astype(int)

    def repr_geojson(self, keep_zero=True):
        elons = self.edges[0]
        elats = self.edges[1]

        out_rects = []
        for x in range(len(elons)-1):
            for y in range(len(elats)-1):
                data = int(self.grid[y, x])
                if not keep_zero and data == 0:
                    continue
                tl = (elons[x], elats[y])
                tr = (elons[x+1], elats[y])
                bl = (elons[x], elats[y+1])
                br = (elons[x+1], elats[y+1])

                # draw rectangle
                poly = [tl, bl, br, tr, tl] # manually draw rect, ccw per spec
                rect = geojson.Polygon([poly])
                lonlat_rect = geojson.utils.map_tuples(
                    lambda c: self.GPS_TF.transform(*c),
                    rect
                )

                feature_rect = geojson.Feature(
                    geometry=lonlat_rect,
                    properties={
                        'count': data,
                        'grid_index': [y, x]
                    },
                )

                out_rects.append(feature_rect)

        out_features = geojson.FeatureCollection(out_rects)
        return out_features

    #__geo_interface__ = {
        # return geojson-like for rendering
    #}
