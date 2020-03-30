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
    if not hotspots:
        # in practice we does query on db and return data
        with module.open_resource(
                '../static/hotspots.csv', 
                mode='rt') as datafile:
            data_reader = csv.DictReader(datafile)
            for line in data_reader:
                line['latitude'] = float(line['latitude'])
                line['longitude'] = float(line['longitude'])
                hotspots.append(line)
    
    # return as json
    return jsonify(hotspots)

