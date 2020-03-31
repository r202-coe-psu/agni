from flask import Blueprint, render_template, current_app, url_for, request
from flask import jsonify
import csv

module = Blueprint('site', __name__)

hotspots = []

@module.route('/')
def index():
    return render_template('/site/index.html')

@module.route('/hotspots')
def get_hotspots():
    queryargs = request.args

    # in practice, we does query on db and return data
    if not hotspots:
        with module.open_resource(
                '../static/hotspots.csv', 
                mode='rt') as datafile:
            data_reader = csv.DictReader(datafile)
            for line in data_reader:
                line['latitude'] = float(line['latitude'])
                line['longitude'] = float(line['longitude'])
                hotspots.append(line)

    # for chunked requests support
    # might get removed later
    count = queryargs.get('count', type=int)
    offset = queryargs.get('offset', default=0, type=int)

    if count is not None:
        trun_hotspots = hotspots[offset:offset+count]
        return jsonify(trun_hotspots)

    # return as json
    return jsonify(hotspots)

