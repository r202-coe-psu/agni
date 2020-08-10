from browser import document, window, ajax, bind, timer
import javascript
import datetime

leaflet = window.L
turf = window.turf
jq = window.jQuery
mcss = window.M

_jsdate_today = javascript.Date.new()

viirs_marker_opts = {
    "stroke": False,
    "radius": 5,
    "color": 'red'
}
modis_marker_opts = {
    "stroke": False,
    "radius": 12,
    "color": 'orange'
}

noise_marker_opts = {
    "stroke": False,
    "radius": 5,
    "color": 'orange'
}
high_marker_opts = {
    "radius": 5,
    "color": 'red'
}


# set up materialize css stuff
dp_opts = {
    "setDefaultDate": True,
    "defaultDate": _jsdate_today,
    "maxDate": _jsdate_today,
    "format": "yyyy-mm-dd"
}

dp_elems = document.querySelectorAll('.datepicker')
dp_instances = mcss.Datepicker.init(dp_elems, dp_opts)

lmap = leaflet.map("mapdisplay",{"preferCanvas": True})
marker_layer = leaflet.LayerGroup.new()
marker_dated = {}

viirs_layer = leaflet.LayerGroup.new()
modis_layer = leaflet.LayerGroup.new()

viirs_marker_dated = {}
modis_marker_dated = {}

turf_dated = {}
clustered_layer = leaflet.LayerGroup.new()
raw_layer = leaflet.LayerGroup.new()
roi_layer = leaflet.LayerGroup.new()

viirs_mkl = {}
modis_mkl = {}

using_roi = False

fetch_in_progress = False

fetch_satellite = {
    "modis" : True,
    "viirs" : True
}


def query_ajax(target=None):
    """ send request to server using ajaxmarker_layer
        Args: target (string): 
            date to query, formatted to '%Y-%m-%d'
    """
    data = {}
    if target is not None:
        data = { "date" : target
        }

    jq.ajax('/hotspots', {
        "dataType": "json",
        "data": data,
        "success": hotspot_get_jq
    })

def change_or_query(target=None):
    """ check if target date is queried before query for new entry
        if already queried, display them instead of query and redraw
        otherwise, proceed to query as normal.
        Args: target (datetime): 
            specifying target date, defaults to today if none provided
    """
    global fetch_in_progress
    if fetch_in_progress:
        return

    if target is None:
        target = datetime.datetime.today()

    target_jul = target.strftime('%Y%j')
    target_str = target.strftime('%Y-%m-%d')

    #if target_jul in marker_dated:
    #    marker_layer.clearLayers()
    #    marker_layer.addLayer(marker_dated[target_jul])
    #    enable_input(True)
    #else:
    #    fetch_in_progress = True
    #    query_ajax_cluster(target_str)

    raw_layer.clearLayers()
    clustered_layer.clearLayers()

    try:
        turf_dated[target_jul, using_roi, 'raw'].addTo(raw_layer)
        turf_dated[target_jul, using_roi, 'turf'].addTo(clustered_layer)
        enable_input(True)
    except KeyError:
        fetch_in_progress = True
        query_ajax_cluster(target_str)

def enable_input(state=True):
    document['hotspot-date-offset'].disabled = not state
    document['hotspot-date'].disabled = not state

# turf test
# only works with VIIRS data point

def cluster_data(resp, status, jqxhr):
    marker_layer.clearLayers()
    turf_layer = leaflet.LayerGroup.new()
    turf_layer.clearLayers()

    geojson = resp
    # draw cluster convex and centroid to separate layer
    def process_cluster(cluster,clusterValue,currentIndex): 
        count = len(cluster.features)
        ch = turf.centroid(cluster)
        ctr = leaflet.geoJSON(ch)
        ctr_info = {
            "cluster": clusterValue,
            "cluster count": count,
        }
        ctr.bindPopup(
            "<br />".join([
                "<b>{}</b>: {}".format(k, v)
                for k, v in ctr_info.items()
            ])
        )
        ctr.addTo(turf_layer)

        cnv = turf.convex(cluster)
        leaflet.geoJSON(cnv).addTo(turf_layer)

    # clustering radius in km
    CLUSTER_RADIUS = 0.375 * 1.5
    clustered = turf.clustersDbscan(geojson, CLUSTER_RADIUS)
    turf.clusterEach(clustered, "cluster", process_cluster)

    def turf_markers(feature, latlng):
        opts = {
            "radius": 5,
            "stroke" : False,
            "color": 'orange'
        }
        dbscan_color = {
            "core": 'red',
            "edge": '#ff00aa',
            "noise": 'orange'
        }

        try:
            opts['color'] = dbscan_color[feature.properties.dbscan]
            if feature.properties.confidence_1 == 'h':
                opts['stroke'] = True
        except AttributeError:
            pass

        return leaflet.circleMarker(latlng, opts)

    def turf_features(feature, layer):
        features_dict = feature.properties.to_dict()
        features_str = [
            "<b>{}</b>: {}".format(k, v)
            for k, v in features_dict.items()
        ]
        layer.bindPopup('<br />'.join(features_str))

    def turf_filter(feature):
        return feature.properties.dbscan == 'noise'

    # draw raw points
    raw_points = leaflet.LayerGroup.new()
    leaflet.geoJSON(clustered, {
        'pointToLayer': turf_markers,
        'onEachFeature': turf_features,
        #'filter': turf_filter
    }).addTo(raw_points)

    thedate = datetime.datetime.strptime(
        document['hotspot-date'].value, '%Y-%m-%d'
    )
    date_str = thedate.strftime('%Y%j')
    turf_dated[date_str, using_roi, 'raw'] = raw_points
    turf_dated[date_str, using_roi, 'turf'] = turf_layer

    raw_points.addTo(raw_layer)
    turf_layer.addTo(clustered_layer)

    global fetch_in_progress
    fetch_in_progress = False

    enable_input(True)

def query_error(jqxhr, errortype, text):
    document['hotspot-info'].text = "E{}: {}".format(jqxhr.status, text)
    enable_input(True)

def query_succes(resp, status, jqxhr):
    if jqxhr.status == 200:
        document['hotspot-info'].text = ''
        cluster_data(resp, status, jqxhr)
    elif jqxhr.status == 204:
        document['hotspot-info'].text = 'No data'
        enable_input(True)

def query_ajax_cluster(target=None):
    """ send request to server using ajax
        Args: target (string): 
            date to query, formatted to '%Y-%m-%d'
    """
    data = {}
    if target is not None:
        data = {"date": target}

    data['roi'] = int(using_roi)

    jq.ajax('/hotspots.geojson', {
        "dataType": "json",
        "data": data,
        "success": query_succes,
        "error": query_error
    })

# /turf test

# RoI

@bind('#hotspot-roi', 'change')
def enable_roi(ev):
    global using_roi
    using_roi = document['hotspot-roi'].checked

# test date input, not final product
# toggle modis/viirs marker layers
def checkbox_changed(ev):
    if fetch_satellite['modis']:
        lmap.addLayer(modis_layer)
    else:
        lmap.removeLayer(modis_layer)

    if fetch_satellite['viirs']:
        lmap.addLayer(viirs_layer)
    else:
        lmap.removeLayer(viirs_layer)


@bind('#hotspot-modis', 'change')
def enable_sattellite(ev):
    if document['hotspot-modis'].checked:
        fetch_satellite['modis'] = True
    else:
        fetch_satellite['modis'] = False
    checkbox_changed(ev)

@bind('#hotspot-viirs', 'change')
def enable_sattellite(ev):
    if document['hotspot-viirs'].checked:
        fetch_satellite['viirs'] = True
    else:
        fetch_satellite['viirs'] = False
    checkbox_changed(ev)

@bind('#hotspot-query', 'click')
@bind('#hotspot-date', 'change')
def date_query(ev):
    enable_input(False)
    target_val = document['hotspot-date'].value
    target = datetime.datetime.strptime(target_val, '%Y-%m-%d')
    slider_offset = datetime.datetime.today() - target
    slider_offset = max(0, 60-slider_offset.days)
    document['hotspot-date-offset'].value = slider_offset
    change_or_query(target)

@bind('#hotspot-date-offset', 'input')
def slider_sync_date(ev):
    offset = document['hotspot-date-offset'].value
    offset = 60 - int(offset)
    delta = datetime.timedelta(days=offset)
    target = datetime.datetime.today() - delta
    target_str = target.strftime('%Y-%m-%d')

    document['hotspot-date'].value = target_str

@bind('#hotspot-date-offset', 'change')
def date_query_slider(ev):
    enable_input(False)
    offset = document['hotspot-date-offset'].value
    offset = 60 - int(offset)
    delta = datetime.timedelta(days=offset)
    target = datetime.datetime.today() - delta
    target_str = target.strftime('%Y-%m-%d')

    change_or_query(target)

def marker_popup(e):
    """ generate contents for clicked marker """
    e_dict = e.to_dict()
    coords = e.getLatLng().to_dict()
    feature_str = [ "{}: {}".format(k, v)
        for k, v in e.feature.items() 
    ]
    return '<br />'.join(feature_str)

def draw_one_marker(spot, marker_opts):
    # make a marker
    coords = (spot['latitude'], spot['longitude'])

    m = leaflet.circleMarker(coords, marker_opts)

    # embed features into marker
    feature = spot.to_dict()
    del feature['latitude']
    del feature['longitude']
    del feature['acq_date']
    del feature['acq_time']
    m.feature = feature

    # add popup before return marker instance
    m.bindPopup(marker_popup)
    return m

def draw_all(data, date_jul):
    if date_jul not in marker_dated:
        mkl = leaflet.LayerGroup.new()
        marker_dated[date_jul] = mkl
    else:
        mkl = marker_dated[date_jul]

    for spot in data:
        m = draw_one_marker(spot)
        m.addTo(mkl)

    mkl.addTo(marker_layer)
    marker_layer.addTo(lmap)
    document['hotspot-info'].text = ''

def draw_chunks(data, date_jul,marker_opts,marker_layer,mkl,marker_dated):
    todo = data.copy()
    chunksize = 200
    chunkdelay = 100

    if date_jul not in marker_dated:
        mkl = leaflet.LayerGroup.new()
        marker_dated[date_jul] = mkl
    else:
        mkl = marker_dated[date_jul]
        enable_input(True)

    def dotask():
        items = todo[0:chunksize]

        for spot in items:
            m = draw_one_marker(spot,marker_opts)
            m.addTo(mkl)

        del todo[0:chunksize]

        if len(todo) > 0:
            timer.set_timeout(dotask, chunkdelay)
            load_percent = 1 - (len(todo) / len(data))
            load_str = "{:.1%}".format(load_percent)
            #document['progress-bar-v'].style.width = load_str
            document['hotspot-info'].text = load_str
        else:
            enable_input(True)
            document['hotspot-info'].text = ''

    timer.set_timeout(dotask, chunkdelay)
    mkl.addTo(marker_layer)
    marker_layer.addTo(lmap)

def hotspot_get_jq(resp_data, text_status, jqxhr):
    # resp_data.data is already json
    if resp_data['status'] == 'success':
        viirs_layer.clearLayers()
        modis_layer.clearLayers()
        document['hotspot-info'].text = 'Loading...'

        data = resp_data
        date_jul = resp_data['date_jul']
        draw_chunks(data.modis['data'],date_jul,modis_marker_opts,modis_layer,modis_mkl,modis_marker_dated)
        draw_chunks(data.viirs['data'],date_jul,viirs_marker_opts,viirs_layer,viirs_mkl,viirs_marker_dated)
    else:
        document['hotspot-info'].text = 'Error retrieving hotspots'
        enable_input(True)

    global fetch_in_progress
    fetch_in_progress = False

# jQuery is somehow way faster
# get point for today
def get_point_jq(ev):
    query_ajax_cluster()

lmap.on('load', get_point_jq)

base = leaflet.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png", {
    "maxZoom": 18,
    "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
})

def draw_roi(resp, status, jqxhr):
    roi_layer.clearLayers()
    leaflet.geoJSON(resp).addTo(roi_layer)

jq.ajax('/regions/kuankreng.geojson', {
    "dataType": "json",
    "success": draw_roi
    }
)

leaflet.control.layers(
    {
        "Base": base.addTo(lmap)
    },
    {
        "RoI": roi_layer.addTo(lmap),
        "Clustered": clustered_layer.addTo(lmap),
        "Raw": raw_layer.addTo(lmap),
    }
).addTo(lmap)
lmap.setView([13, 100.8], 6)
leaflet.control.scale({"imperial": False}).addTo(lmap)

# for browser console debug only
window.lmap = lmap
window.marker_layer = marker_layer
window.marker_dated = marker_dated
