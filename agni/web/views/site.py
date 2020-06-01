from flask import Blueprint, render_template, current_app, url_for, request
from flask import jsonify
import csv
import datetime
import requests

from agni.acquisitor import fetch_nrt, filtering

module = Blueprint('site', __name__)

# fetched data cache
hotspots = {}


@module.route('/')
def index():
    return render_template('/site/index.html')

@module.route('/hotspots')
def get_hotspots():
    queryargs = request.args

    today = datetime.datetime.today()
    requested_date = queryargs.get('date', type=str)
    lineprot = queryargs.get('line', type=str)

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
    ret['status'] = None
    ret['data'] = []
    ret['date_jul'] = target_julian

    hotspot_points = None
    if target_julian not in hotspots:
        res = fetch_nrt.request_nrt(target)
        if res.status_code == 200:
            hotspot_points = fetch_nrt.reshape_csv(res.text)
            hotspot_points = filtering.filter_bbox(hotspot_points, 
                                                   filtering.TH_BBOX)
            hotspots[target_julian] = hotspot_points
            ret['status'] = 'success'
            ret['data'] = hotspot_points
        else:
            ret['status'] = 'failed'
    else:
        ret['status'] = 'success'
        ret['data'] = hotspots[target_julian]


    # for chunked requests support
    # might get removed later
    count = queryargs.get('count', type=int)
    offset = queryargs.get('offset', default=0, type=int)

    if count is not None:
        trun_hotspots = ret['data'][offset:offset+count]
        ret['data'] = trun_hotspots

    # for testing
    if lineprot == 'yes':
        line_nrts = []
        for nrt in ret['data']:
            line_nrt = fetch_nrt.nrt_to_lineprot(
                nrt, 'hotspots', 'acq_time',
                ['daynight', 'satellite', 'confidence'],
            )
            line_nrts.append(line_nrt)
        ret['line_protocol'] = line_nrts

    # return as json
    return jsonify(ret)

