from flask import (
    Blueprint, render_template, current_app, url_for, request,
    jsonify, send_from_directory
)

import datetime

import geojson
import shapely
import shapely.geometry

from agni.acquisitor import fetch_nrt, filtering
from agni.util import nrtconv, ranger, timefmt
from agni.models import create_influxdb, Region
from agni.processing import firecluster, firepredictor, heatmap

from .. import regions
from ..forms.mapcontrols import HistoryControlForm

module = Blueprint('map_api', __name__, url_prefix='/api')

@module.route('/hotspots/<region>/<date>')
def hotspots_date(region, date):
    pass

@module.route('/predict/<region>', methods=['POST'])
def do_predict(region):
    pass

@module.route('/history/<region>/seasonal/<month>')
def do_history_seasonal(region, month):
    pass

@module.route('/history/<region>/year/<year>')
def do_history_year(region, year):
    pass

@module.route('/history/<region>/range', methods=['POST'])
def do_history_timerange(region):
    pass
