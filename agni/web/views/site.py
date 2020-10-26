from flask import Blueprint, render_template, current_app, url_for, request
from flask import jsonify, send_from_directory

import pathlib
import json
import csv
import datetime

import geojson
import requests

try:
    import importlib.resources as pkg_res
except ImportError:
    import importlib_resources as pkg_res

from agni.acquisitor import fetch_nrt, filtering
from agni.util import nrtconv
from agni.models import influxdb
from agni.processing import firecluster, firepredictor
from agni.web import regions

module = Blueprint('site', __name__)

# fetched data cache
modis_hotspots = {}
viirs_hotspots = {}

INFLUX_UNAME = 'agnitest'
INFLUX_PASSWD = 'agnitest'
INFLUX_BUCKET = 'hotspots'
INFLUX_URL = 'http://localhost:8086'

TODAY = datetime.datetime.today()

def get_viirs_hotspots(date):
    return fetch_nrt.get_nrt_data(date, src=fetch_nrt.SRC_VIIRS)

def get_modis_hotspots(date):
    return fetch_nrt.get_nrt_data(date, src=fetch_nrt.SRC_MODIS)

fetch_hotspots = {
    'viirs': get_viirs_hotspots,
    'modis': get_modis_hotspots
}

@module.route('/')
def index():
    roi_none = ['Thailand', 'all']
    roi_list = [roi_none]

    region_list = [ 
        roi
        for roi in pkg_res.contents(regions) 
        if 'geojson' in pathlib.Path(roi).suffix
    ]
    for roi_file in region_list:
        # get region name from geojson
        roi_str = pkg_res.read_text(regions, roi_file)
        roi_geojson = geojson.loads(roi_str)
        roi_feature = roi_geojson['features'][0]
        roi_label = roi_feature['properties']['name']
        # get matching filename
        roi_def = pathlib.Path(roi_file).stem
        roi_list.append([roi_label, roi_def])

    return render_template('/site/index.html', roi_list=roi_list)

@module.route('/hotspots')
def get_all_hotspots():
    queryargs = request.args

    requested_date = queryargs.get('date', type=str)
    today = datetime.datetime.today()
    target = today
    if requested_date is not None:
        try:
            target = datetime.datetime.strptime(requested_date, '%Y-%m-%d')
        except ValueError:
            target = today
    target_julian = target.strftime('%Y%j')
    # in practice, we does query on db and return data
    # probably
    ret = {}
    ret['date_jul'] = target_julian
    ret['modis'] = get_modis_hotspots(target)
    ret['viirs'] = get_viirs_hotspots(target)
    ret['status'] = 'success'

    # return as json
    return jsonify(ret)

def lookup_data(target, dateend=None, sat_src=None, livedays=None):
    sat_src = 'viirs' if sat_src is None else sat_src
    livedays = 60 if livedays is None else livedays
    # fetch live first, then try db
    if TODAY - target <= datetime.timedelta(days=livedays):
        result = fetch_hotspots[sat_src](target)
        sat_points = result
    else:
        if dateend is not None:
            dateplus = dateend
        else:
            dateplus = target + datetime.timedelta(days=1)
        
        params = {
            "date": target.strftime("%Y-%m-%d"),
            "dateplus": dateplus.strftime('%Y-%m-%d')
        }
        # OH MAN I AM NOT GOOD WITH PARAMS PLZ TO HELP
        influxql_str = """
            select * from "hotspots"
            where "time" >= '{date}'
                and time < '{dateplus}';
        """.format(**params)
        result = influxdb.query(influxql_str,
                                epoch='u',
                                database=INFLUX_BUCKET)
        sat_points = list(result.get_points())
    
    return sat_points

@module.route('/hotspots.geojson')
def get_geojson_hotspots():
    queryargs = request.args

    requested_date = queryargs.get('date', type=str)
    requested_source = queryargs.get('source', type=str)
    roi_name = queryargs.get('roi', type=str)

    today = datetime.datetime.today()
    target = today
    if requested_date is not None:
        try:
            target = datetime.datetime.strptime(requested_date, '%Y-%m-%d')
        except ValueError:
            target = today
    target_julian = target.strftime('%Y%j')
    # in practice, we does query on db and return data
    # probably

    sat_src = None
    if requested_source is not None:
        sat_src = requested_source
    
    sat_points = lookup_data(target, sat_src=sat_src)

    # if RoI filtering is set
    if roi_name is not None and roi_name != 'all':
        s = pkg_res.read_text(regions, '{}.geojson'.format(roi_name))
        roi = geojson.loads(s)
        filtered = filtering.filter_shape(sat_points, roi)
        sat_points = filtered

    if len(sat_points) > 0:
        sat_geojson = nrtconv.to_geojson(sat_points)
        return jsonify(sat_geojson)
    else:
        return '', 204

@module.route('/regions/<roi>')
def serve_roi_file(roi):
    return send_from_directory('regions', roi)
