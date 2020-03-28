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
        with open('/home/arch/agni/agni/web/static/hotspots.csv') as datafile:
            data_reader = csv.DictReader(datafile)
            for line in data_reader:
                hotspots.append(line)
    trun_hotspots = hotspots[0:50]
    
    reqdata = request.json
    
    # get length of total data
    #if reqdata['mode'] == 'length':
    #    return jsonify({"length":len(hotspots)})

    return jsonify(trun_hotspots)

