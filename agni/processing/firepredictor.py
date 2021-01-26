import json
import csv

import pyproj
import geojson

import numpy as np
import pandas as pd

from scipy import ndimage

from ..util import ranger
from ..util import geojsontools as gjtool

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
        utm (bool) [optional]:
            set this to True if data given is already in UTM

    Returns:
        firegrid (np.array):
            2d numpy array bitmap showing which grid has value
        edges (tuple[np.array]):
            bin edges along (x axis, y axis)
    """
    nrt_df = pd.DataFrame(nrt_points, copy=True)

    # supplied dummy data to get histogram2d to function
    # no data -> no fire; still need that empty grid with its edges

    try:
        xdata = nrt_df[xkey]
        ydata = nrt_df[ykey]
    except KeyError:
        xdata = pd.Series([0])
        ydata = pd.Series([0])

    # convert to UTM as necessary
    if not utm:
        xdata, ydata = UTM47N_TF.transform(xdata.to_list(), ydata.to_list())

    # actually binning, abuse histogram2d to count
    count, lon_edge, lat_edge = np.histogram2d(x=xdata, y=ydata, bins=bins)
    # filter only those with values
    firegrid = (count.T > 0).astype(int)
    edges = (lon_edge, lat_edge)

    return firegrid, edges

def generate_firegrid(nrt_points, area, step, utm=False,
                      xkey=None, ykey=None):
    """
    generate fire grid from data points over a given area

    Args:
        nrt_point (list[dict]): 
            NRT data points
        area (list[4]):
            a list of bounding box's bottom left and top right coordinates
            (bl_lon, bl_lat, tr_lon, tr_lat)
        distance (int):
            grid distance in meters, each cell is assumed to be a square

    Returns:
        firegrid (numpy.array):
            bitmap-like grid representing burn states, categorized to 3 types
            of cannot burn, can burn, burning (EMPTY, TREE, FIRE)
        edges (tuple[numpy.array])
            edges of each cell in a grid
    """

    # formatting coordinates
    # leaflet .ToBBoxString() gives out coordinates in 
    # southwest,northeast corner, lon,lat format, as flat list
    area_lons = area[0], area[2]
    area_lats = area[1], area[3]
    area_x, area_y = UTM47N_TF.transform(area_lons, area_lats)
    bl = (area_x[0], area_y[0])
    tr = (area_x[1], area_y[1])

    lons_u = ranger.closed_range(bl[0], tr[0], step)
    lats_u = ranger.closed_range(bl[1], tr[1], step)

    if xkey is None:
        xkey = 'longitude'
    if ykey is None:
        ykey = 'latitude'

    firegrid, edges = bin_firegrid(
        nrt_points, xkey=xkey, ykey=ykey,
        bins=(lons_u, lats_u), utm=utm
    )

    return firegrid, edges

def firegrid_split(firegrid):
    """ split a fire grid into separate fire map and burn map """
    firemap = firegrid == G_FIRE
    burnedmap = firegrid == G_EMPTY
    return firemap, burnedmap

def firegrid_combine(basemap, overlaymap, value):
    firegrid = np.where(overlaymap == 1, value, basemap)
    return firegrid

def burnmap_combine(burnmaps):
    """ combining multiple burnmaps into one burnmap """
    _shape = min(b.shape for b in burnmaps)
    out_map = np.zeros(_shape).astype(bool)
    for bmap in burnmaps:
        out_map |= bmap.astype(bool)
    return out_map

def firegrid_prepare_input(firemap, burnedmap):
    """ set up firegrid as input for model step"""
    fg_input = firemap.copy().astype(int)
    # try to avoid broadcasting else weird cell shows up
    fg_input = firegrid_combine(firemap, burnedmap, G_EMPTY)
    return fg_input

def firegrid_step(firegrid, kernel=None):
    if kernel is None:
        kernel = FIRE_KERNEL

    # expands fire to not burned areas
    firemap, burnedmap = firegrid_split(firegrid)
    next_grid = ndimage.binary_dilation(
        firemap, 
        structure=kernel, 
        mask=np.bitwise_not(burnedmap),
        border_value=0
    ).astype(int)

    # mark current fire point as burned area
    burnedmap_all = firemap | burnedmap
    next_grid = firegrid_combine(next_grid, burnedmap_all, G_EMPTY)

    return next_grid

def firegrid_model_compute(nrt_current, nrt_pasts, area, step, kernel=None):
    if kernel is None:
        kernel = FIRE_KERNEL

    # make map
    # assumes nrt_(current|pasts) is flat list of data points
    firemap, edges = generate_firegrid(nrt_current, area=area, step=step)
    burnmap, burnedges = generate_firegrid(nrt_pasts, area=area, step=step)

    # prepare
    fg_input = firegrid_prepare_input(firemap, burnmap)
    fg_step = firegrid_step(fg_input)
    #print([firemap.shape, burnmap.shape, fg_input.shape])

    return fg_step, edges

def firegrid_geojson(firegrid, edges, ignore_trees=False):
    try:
        elons = edges[0].tolist()
        elats = edges[1].tolist()
    except AttributeError:
        elons = edges[0]
        elats = edges[1]

    out_rects = []
    for x in range(len(elons)-1):
        for y in range(len(elats)-1):
            data = firegrid[y, x]
            if data == G_TREE and ignore_trees:
                continue
            west, east = elons[x:x+2]
            south, north = elats[x:x+2]

            rect = gjtool.rect(west, south, east, north)
            lonlat_rect = gjtool.reproject(rect, LONLAT_TF)

            feature_rect = geojson.Feature(
                geometry=lonlat_rect, properties={'celltype': G_STATE[data]},
            )

            out_rects.append(feature_rect)

    out_features = geojson.FeatureCollection(out_rects)
    return out_features
