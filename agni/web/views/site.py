from flask import (
    Blueprint, render_template, current_app, url_for, request,
    jsonify, send_from_directory
)

import pathlib
import datetime

import geojson
import shapely
import shapely.geometry

try:
    import importlib.resources as pkg_res
except ImportError:
    import importlib_resources as pkg_res

from agni.acquisitor import fetch_nrt, filtering
from agni.util import nrtconv, ranger, timefmt
from agni.models import create_influxdb
from agni.models.region import Region
from agni.processing import firecluster, firepredictor, heatmap
from agni.web import regions
from agni.web.forms.mapcontrols import HistoryControlForm

module = Blueprint('site', __name__)

# fetched data cache
modis_hotspots = {}
viirs_hotspots = {}

@module.record
def on_bp_register(state):
    app = state.app
    fetch_nrt.set_token(app.config.get('FIRMS_API_TOKEN'))

def get_viirs_hotspots(date):
    return fetch_nrt.get_nrt_data(date, src=fetch_nrt.SRC_VIIRS)

def get_modis_hotspots(date):
    return fetch_nrt.get_nrt_data(date, src=fetch_nrt.SRC_MODIS)

fetch_hotspots = {
    'viirs': get_viirs_hotspots,
    'modis': get_modis_hotspots
}

ROI_NONE = ['Thailand', 'all']
def roi_list_module():
    roi_list = [ROI_NONE]

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
    return roi_list

def roi_label_db():
    roi_list = [ROI_NONE]
    reglist = Region.objects
    roi_list += [[c.human_name, c.name] for c in reglist]
    return roi_list

@module.route('/')
def index():
    roi_list = roi_label_db()

    now = datetime.datetime.now()
    history_controls = HistoryControlForm()
    # set starting value
    history_controls.start.process(
        None, data=dict(
            year=2000,
            month=1
        )
    )
    history_controls.end.process(
        None, 
        data=dict(
            year=now.year,
            month=now.month
        )
    )

    return render_template('/site/index.html',
        roi_list=roi_list,
        hisctrl=history_controls,
    )

@module.route('/hotspots')
def get_all_hotspots():
    queryargs = request.args

    requested_date = queryargs.get('date', type=str)
    today = datetime.datetime.today()
    datestart = today
    if requested_date is not None:
        try:
            datestart = datetime.datetime.strptime(requested_date, '%Y-%m-%d')
        except ValueError:
            datestart = today
    target_julian = datestart.strftime('%Y%j')
    # in practice, we does query on db and return data
    # probably
    ret = {}
    ret['date_jul'] = target_julian
    ret['modis'] = get_modis_hotspots(datestart)
    ret['viirs'] = get_viirs_hotspots(datestart)
    ret['status'] = 'success'

    # return as json
    return jsonify(ret)

def lookup_external(dates, sat_src, bounds=None):
    sat_points = []
    for date in dates:
        result = fetch_hotspots[sat_src](date)
        if bounds is not None:
            result = filtering.filter_bbox(result, bbox=bounds)
        sat_points += result
    return sat_points

def lookup_db(dates, bounds=None, measurement=None, database=None):
    start = min(dates)
    end = max(dates)
    measurement = measurement or 'hotspots'
    if (end - start).days == 0:
        end += datetime.timedelta(days=1)

    influxql_str = """
        select * from "{measurement}"
        where time >= '{start}' and time < '{end}'
    """.format(start=start, end=end, measurement=measurement)

    if bounds is not None:
        # west,south,east,north
        influxql_str += """ 
            and longitude >= {bbox[0]} and longitude < {bbox[2]}
            and latitude >= {bbox[1]} and latitude < {bbox[3]}
        """.format(bbox=bounds)

    influxql_str += ';'

    influxdb = create_influxdb(current_app.config)
    result = influxdb.query(influxql_str,
                            epoch=None,
                            database=database)
    sat_points = list(result.get_points())
    return sat_points

def lookup_data(
        datestart, dateend=None, sat_src=None, livedays=None,
        bounds=None
):

    sat_src = sat_src or 'viirs'
    livedays = livedays or 60

    # find requested date range for target
    if dateend is None:
        dateend = datestart

    lookup_dates = ranger.date_range(datestart, dateend, normalize=True)

    sat_points = lookup_db(lookup_dates, bounds)

    return sat_points

@module.route('/hotspots.geojson')
def get_geojson_hotspots():
    queryargs = request.args

    requested_date = queryargs.get('date', type=str)
    requested_source = queryargs.get('source', type=str)
    roi_name = queryargs.get('roi', type=str)

    today = datetime.datetime.today()
    datestart = today
    if requested_date is not None:
        try:
            datestart = datetime.datetime.strptime(requested_date, '%Y-%m-%d')
        except ValueError:
            datestart = today
    target_julian = datestart.strftime('%Y%j')

    sat_src = None
    if requested_source is not None:
        sat_src = requested_source

    sat_points = lookup_data(datestart, sat_src=sat_src)

    # if RoI filtering is set
    if roi_name is not None and roi_name != 'all':
        s = pkg_res.read_text(regions, '{}.geojson'.format(roi_name))
        roi = geojson.loads(s)
        filtered = filtering.filter_shape(sat_points, roi)
        sat_points = filtered
    elif roi_name == 'all':
        sat_points = filtering.filter_bbox(sat_points, filtering.TH_BBOX)

    if len(sat_points) > 0:
        sat_geojson = nrtconv.to_geojson(sat_points)
        return jsonify(sat_geojson)
    else:
        return '', 204

@module.route('/regions/<roi>')
def serve_roi_file(roi):
    region = Region.objects(name=roi).first()
    if region:
        return jsonify(region)
    # fallback
    return send_from_directory('regions', roi)

@module.route('/clustered.geojson')
def get_clustered_hotspots():
    queryargs = request.args

    requested_date = queryargs.get('date', type=str)
    roi_name = queryargs.get('roi', type=str)

    today = datetime.datetime.now()
    datestart = today
    if requested_date is not None:
        try:
            datestart = timefmt.parse_web(requested_date)
        except ValueError:
            datestart = today
    target_julian = datestart.strftime('%Y%j')

    sat_src = None
    sat_points = lookup_data(datestart, sat_src=sat_src)

    # if RoI filtering is set
    if roi_name is not None and roi_name != 'all':
        s = pkg_res.read_text(regions, '{}.geojson'.format(roi_name))
        roi = geojson.loads(s)
        filtered = filtering.filter_shape(sat_points, roi)
        sat_points = filtered
    elif roi_name == 'all':
        sat_points = filtering.filter_bbox(sat_points, filtering.TH_BBOX)

    if len(sat_points) > 0:
        clustered = firecluster.cluster_fire(sat_points)
        sat_geojson = nrtconv.to_geojson(clustered)
        return jsonify(sat_geojson)
    else:
        return '', 204

@module.route('/predict.geojson')
def get_prediction():
    queryargs = request.args

    requested_date = queryargs.get('date', type=str)
    lagdays = queryargs.get('lag', type=int)
    bounds = queryargs.get('area', type=str)
    ignorenoise = queryargs.get('dropnoise', type=str)

    if bounds is None:
        return '', 400

    if ignorenoise is None:
        ignorenoise = 'false'

    today = datetime.datetime.today()
    datestart = today
    if requested_date is not None:
        try:
            datestart = datetime.datetime.strptime(requested_date, '%Y-%m-%d')
        except ValueError:
            datestart = today
    target_julian = datestart.strftime('%Y%j')

    if lagdays is None:
        lagdays = 1

    start  = datestart - datetime.timedelta(days=lagdays)
    end = datestart - datetime.timedelta(days=1)
    sat_src = None

    prev_sat_points = lookup_data(start, end, sat_src=sat_src)
    current_sat_points = lookup_data(datestart, sat_src=sat_src)

    area = [float(n) for n in bounds.split(',')]

    prev_data = firecluster.cluster_fire(prev_sat_points)
    #prev_data = filtering.filter_bbox(prev_data, area)

    current_data = firecluster.cluster_fire(current_sat_points)
    if ignorenoise.casefold() == 'true':
        current_data = firecluster.drop_noise(current_data)
    #current_data = filtering.filter_bbox(current_data, area)

    p_grid, p_edges = firepredictor.firegrid_model_compute(
        current_data, prev_data, area, 375
    )

    result_geojson = firepredictor.firegrid_geojson(p_grid, p_edges)

    return jsonify(result_geojson)

@module.route('/history/<region>/<data_type>', methods=['POST'])
def get_region_histogram(region, data_type=None):
    form = HistoryControlForm()
    if form.validate_on_submit():
        start, end = (
            [int(n) for n in (form.start.year.data, form.start.month.data)],
            [int(n) for n in (form.end.year.data, form.end.month.data)],
        )
        date_start = datetime.datetime(*start, 1)
        date_end = datetime.datetime(*end, 1)
        date_start = timefmt.normalize(date_start)
        date_end = timefmt.normalize(date_end)
    else:
        return "Malformed input", 400

    #print([start, end])
    # get region bbox for faster processing, no db yet
    roi_str = pkg_res.read_text(regions, "{}.geojson".format(region))
    roi_geojson = geojson.loads(roi_str)
    roi_shape = shapely.geometry.shape(
        roi_geojson.features[0].geometry
    ).buffer(0)
    roi_bbox = roi_shape.bounds

    data = lookup_data(datestart=date_start, dateend=date_end, bounds=roi_bbox)
    if len(data) == 0:
        return 'No Data', 204

    if data_type == 'count':
        weight = None
        repr_mode = 'count'

    else:
        weight = data_type
        repr_mode = 'average'

    NRT_DATA_UNITS = {
        'frp': 'MW',
        'bright_ti4': 'K',
        'bright_ti5': 'K',
    }

    try:
        val_unit = NRT_DATA_UNITS[data_type]
    except KeyError:
        val_unit = ''

    hmap = heatmap.NRTHeatmap(step=375, bounds=roi_bbox)
    hmap.fit(
        data, 'longitude', 'latitude',
        wkey=weight
    )

    hmap_gj = hmap.repr_geojson(keep_zero=False, mode=repr_mode)
    hmap_gj['info'].update({
        'region': region,
        'value_unit': val_unit
    })

    return jsonify(hmap_gj)
