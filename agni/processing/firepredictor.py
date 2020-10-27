import json
import csv

import pyproj
import geojson

import numpy as np
import pandas as pd

from scipy import ndimage

from agni.util import nprange

# perfome some project from latlon -> UTM 47N so I can do things in meters
# force use of x, y (lon, lat) (east, north) order
PROJ_LONLAT = pyproj.Proj('epsg:4326') # lat, lon
PROJ_UTM47N = pyproj.Proj('epsg:32647') # UTM 47N, as appeared in shapefiles

# coordinate transformers
UTM47N_TF = pyproj.Transformer.from_proj(
    PROJ_LONLAT, PROJ_UTM47N, always_xy=True
)
LONLAT_TF = pyproj.Transformer.from_proj(
    PROJ_UTM47N, PROJ_LONLAT, always_xy=True
)

# grid type
G_TREE, G_FIRE, G_EMPTY = 0, 1, 2
G_STATE = ['TREE', 'FIRE', 'EMPTY']

FIRE_KERNEL = np.ones((3, 3))

#
# probably process everything in UTM coords for distance simplicity
# 1 unit == 1m irl
#

def bin_firegrid(nrt_points, xkey, ykey, bins, utm=False):
    """ 
    perform 2d binning of data points
    
    Args:
        nrt_points (list[dict]):
            raw data points, containing position info
        xkey, ykey (str):
            string indicates which dict key has position info by that axis
            e.g. xkey='longitude', ykey='latitude'
        bins (tuple[np.array]):
            bin edges for 2d binning, in order of x axis and y axis
        utm (bool):
            set this to True if data given is already in UTM
    
    Returns:
        firegrid (np.array):
            2d numpy array bitmap showing which grid has value
        edges (tuple[np.array]):
            bin edges along (x axis, y axis)
    """
    if isinstance(nrt_points, pd.DataFrame):
        nrt_df = nrt_points.copy()
    else:
        nrt_df = pd.DataFrame(nrt_points)
    
    xdata = nrt_df[xkey]
    ydata = nrt_df[ykey]

    # convert to UTM as necessary
    if not utm:
        xdata, ydata = UTM47N_TF.transform(xdata.to_list(), ydata.to_list())

    # actually binning, abuse histogram2d to count
    count, lon_edge, lat_edge = np.histogram2d(x=xdata, y=ydata, bins=bins)
    # filter only those with values
    firegrid = (count.T > 0).astype(int)
    edges = (lon_edge, lat_edge)

    return firegrid, edges

def generate_firegrid(nrtpoints, sample_area, step, utm=False):
    """
    generate fire grid from data points over a given area

    Args:
        nrtpoint (list[dict]): 
            NRT data points
        sample_area (tuple, tuple):
            a pair of points represent sampling boundary (topleft/downright?)
        distance (int):
            grid distance in meters, each cell is assumed to be a square

    Returns:
        firegrid (numpy.array):
            bitmap-like grid representing burn states, categorized to 3 types
            of cannot burn, can burn, burning (EMPTY, TREE, FIRE)
        edges (tuple[numpy.array])
            edges of each cell in a grid
    """

    # (lat, lon) to (lon, lat) to (east, north)
    lonlat_corner = [reversed(c) for c in sample_area]
    tl, br = UTM47N_TF.transform(lonlat_corner)

    lons_u = nprange.closed_range(tl[0], br[0], step)
    lats_u = nprange.closed_range(tl[1], br[1], step)

    firegrid, edges = bin_firegrid(
        nrt_points, xkey='longitude', ykey='latitude',
        bins=(lons_u, lats_u), utm=utm
    )

    return firegrid, edges

def firegrid_split(firegrid):
    """ split a fire grid into separate fire map and burn map """
    firemap = firegrid == G_FIRE
    burnedmap = firegrid == G_EMPTY
    return firemap, burnedmap

def burnmap_combine(burnmaps):
    """ combining multiple burnmaps into one burnmap """
    _shape = min(b.shape for b in burnmaps)
    out_map = np.zeros(_shape).astype(bool)
    for bmap in burnmaps:
        out_map |= bmap.astype(bool)
    return out_map

def firegrid_prepare_input(firemap, burnedmap):
    """ set up firegrid as input for """
    fg_input = firemap.copy().astype(int)
    fg_input[burnedmap] = G_EMPTY
    return fg_input

def firegrid_step(firegrid, kernel=None):
    if kernel is None:
        kernel = FIRE_KERNEL
    
    firemap, burnedmap = firegrid_split(firegrid)
    next_grid = ndimage.binary_dilation(
        firemap, 
        structure=kernel, 
        mask=np.bitwise_not(burnedmap),
        border_value=0
    ).astype(int)
    
    next_grid[burnedmap] = G_EMPTY
    next_grid[firemap] = G_EMPTY

    return next_grid

def firegrid_model_compute(nrt_current, nrt_pasts, area, step, kernel=None):
    kernel = FIRE_KERNEL if kernel is None else kernel

    # make map
    firemap, edges = generate_firegrid(nrt_current, sample_area=area, step=step)

    burned_grids = []
    for points in nrt_pasts:
        burngrid, _ = generate_firegrid(points, sample_area=area, step=step)
        burned_grids.append(burngrid)
    burnmap = burnmap_combine(burned_grids)

    # prepare
    fg_input = firegrid_prepare_input(firemap, burnmap)

    fg_step = firegrid_step(fg_input)

    return fg_step, edges

def firegrid_geojson(firegrid, edges):
    elons = edges[0]
    elats = edges[1]

    out_rects = []
    for x in range(len(elons)-1):
        for y in range(len(elats)-1):
            data = firegrid[y, x]
            tl = (elons[x], elats[y])
            tr = (elons[x+1], elats[y])
            bl = (elons[x], elats[y+1])
            br = (elons[x+1], elats[y+1])

            # draw rectangle
            poly = [tl, bl, br, tr, tl] # manually draw rect, ccw per spec
            rect = geojson.Polygon([poly])
            lonlat_rect = geojson.utils.map_tuples(
                lambda c: LONLAT_TF.transform(*c), 
                rect
            )

            feature_rect = geojson.Feature(
                geometry=lonlat_rect, properties={'celltype': G_STATE[data]}, 
            )

            out_rects.append(feature_rect)
    
    out_features = geojson.FeatureCollection(out_rects)
    return out_features