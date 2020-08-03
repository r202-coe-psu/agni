from flask import Blueprint, render_template, current_app, url_for, request
from flask import jsonify

import json
import csv
import datetime
import requests
import influxdb_client as ifc

from agni.acquisitor import fetch_nrt, filtering
from agni.util import nrtconv
from agni.models import influxdb

module = Blueprint('site', __name__)

# fetched data cache
modis_hotspots = {}
viirs_hotspots = {}

INFLUX_UNAME = 'agnitest'
INFLUX_PASSWD = 'agnitest'
INFLUX_BUCKET = 'hotspots'
INFLUX_URL = 'http://localhost:8086'

ifxclient = ifc.InfluxDBClient(url=INFLUX_URL, token='-')
ifx_query = ifxclient.query_api()

TODAY = datetime.datetime.today()

def get_modis_hotspots(target,target_julian):
    ret = {}
    ret['status'] = None
    ret['data'] = []
    hotspot_points = None
    if target_julian not in modis_hotspots:
        res = fetch_nrt.request_modis_nrt(target)
        if res.status_code == 200:
            hotspot_points = fetch_nrt.reshape_csv(res.text,"modis")
            hotspot_points = filtering.filter_bbox(hotspot_points, 
                                                filtering.TH_BBOX)
            modis_hotspots[target_julian] = hotspot_points
            ret['status'] = 'success'
            ret['data'] = hotspot_points
        else:
            ret['status'] = 'failed'
    else:
        ret['status'] = 'success'
        ret['data'] = modis_hotspots[target_julian]
    return ret        

def get_viirs_hotspots(target,target_julian):
    ret = {}
    ret['status'] = None
    ret['data'] = []
    hotspot_points = None

    if target_julian not in viirs_hotspots:
        res = fetch_nrt.request_viirs_nrt(target)
        if res.status_code == 200:
            hotspot_points = fetch_nrt.reshape_csv(res.text,"viirs")
            hotspot_points = filtering.filter_bbox(hotspot_points, 
                                                filtering.TH_BBOX)
            viirs_hotspots[target_julian] = hotspot_points
            ret['status'] = 'success'
            ret['data'] = hotspot_points
        else:
            ret['status'] = 'failed'
    else:
        ret['status'] = 'success'
        ret['data'] = viirs_hotspots[target_julian]
    return ret   



@module.route('/')
def index():
    return render_template('/site/index.html')

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
    ret['modis'] = get_modis_hotspots(target,target_julian)
    ret['viirs'] = get_viirs_hotspots(target,target_julian)
    ret['status'] = 'success'

    # return as json
    return jsonify(ret)

fetch_hotspots = {
    'viirs': get_viirs_hotspots,
    'modis': get_modis_hotspots
}

@module.route('/hotspots.geojson')
def get_geojson_hotspots():
    queryargs = request.args

    requested_date = queryargs.get('date', type=str)
    requested_source = queryargs.get('source', type=str)

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

    sat_src = 'viirs'
    if requested_source is not None:
        sat_src = requested_source

    sat_points = fetch_hotspots[sat_src](target,target_julian)
    sat_geojson = nrtconv.to_geojson(sat_points['data'])
    return jsonify(sat_geojson)

@module.route('/ifdb', defaults={'date': None})
@module.route('/ifdb/<date>')
def testquery(date):
    queryargs = request.args

    requested_date = date #queryargs.get('date', type=str)
    requested_source = queryargs.get('source', type=str)
    useinfluxql = queryargs.get('influxql', type=int)

    target = TODAY
    if requested_date is not None:
        try:
            target = datetime.datetime.strptime(requested_date, '%Y-%m-%d')
        except ValueError:
            target = TODAY
    target_julian = target.strftime('%Y%j')

    # flux query
    # this is a goddamn trainwreck holy shit
    flux_query = """ from(bucket: "hotspots") 
        |> range(start: 2020-04-01T00:00:00Z, stop: 2020-04-02T00:00:00Z)
        |> filter(fn: (r) =>
            r._field != "version" and
            r._field != "type"
        )
        |> pivot(
            rowKey:["_time"],
            columnKey: ["_field"],
            valueColumn: "_value"
        )
        |> drop(columns: ["satellite", "_start", "_stop"])
    """
    if useinfluxql == 1:
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
        # I (ALMOST) GOT THE ORIGINAL TABLE BACK YAY
        return jsonify(list(result.get_points()))
    else:
        flux_res = ifx_query.query_raw(
            flux_query.format(
                bucket=INFLUX_BUCKET, 
                start='2020-04-01T00:00:00Z',
                stop='2020-04-02T00:00:00Z'
            )
        )
        reslist = [ s.decode('utf-8') for s in flux_res ]
        return str(reslist)
    return 'nada'
