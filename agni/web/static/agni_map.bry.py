from browser import document, window, ajax, bind, timer
import javascript
import datetime

leaflet = window.L
jq = window.jQuery
mcss = window.M

_jsdate_today = javascript.Date.new()

marker_opts = {
    "stroke": False,
    "radius": 5,
    "color": '#ff8833'
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
fetch_in_progress = False

def query_ajax(target=None):
    """ send request to server using ajax

        Args: target (string): 
            date to query, formatted to '%Y-%m-%d'
    """
    data = {}
    if target is not None:
        data = { "date" : target }

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

    if target_jul in marker_dated:
        marker_layer.clearLayers()
        marker_layer.addLayer(marker_dated[target_jul])
        enable_input(True)
    else:
        enable_input(False)
        fetch_in_progress = True
        query_ajax(target_str)

def enable_input(state=True):
    document['hotspot-date-offset'].disabled = not state
    document['hotspot-date'].disabled = not state

def date_from_offset(offset, maxdelta=60):
    # maxdelta of 60 since live NRT data is stored 
    # for at most 2 months (60 days)
    today = datetime.datetime.today()
    delta = datetime.timedelta(days=(maxdelta-offset))

    return today-delta

@bind('#map-options', 'change')
def map_options_changed(ev):
    today = datetime.datetime.today()
    date_cal_str = document['hotspot-date'].value
    date_cal = datetime.datetime.strptime(date_cal_str, '%Y-%m-%d')

    slider_val = int(document['hotspot-date-offset'].value)
    date_slider = date_from_offset(slider_val)

    change_src = ev.target.id
    if change_src == 'hotspot-date-offset':
        # changes from slider
        document['hotspot-date'].value = date_slider.strftime('%Y-%m-%d')
        target = date_slider

    elif change_src == 'hotspot-date':
        # changes from date picker
        new_offset = today - date_cal
        document['hotspot-date-offset'].value = max(0, 60-new_offset.days)
        target = date_cal

    change_or_query(target)

def marker_popup(e):
    """ generate contents for clicked marker """
    e_dict = e.to_dict()
    coords = e.getLatLng().to_dict()
    feature_str = [ "{}: {}".format(k, v)
        for k, v in e.feature.items() 
    ]
    return '<br />'.join(feature_str)

def draw_one_marker(spot, ext_opts=marker_opts):
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

def draw_chunks(data, date_jul):
    """ draw NRT data points onto a marker layer
        batch processed to avoid locking up browsers

        Args:
            data (list of dicts):
                list of NRT data points as dicts
            date_jul (str):
                date of data points

        Return:
            mkl (leaflet.LayerGroup):
                a LayerGroup containing markers
    """
    todo = data.copy()
    chunksize = 200
    chunkdelay = 100

    mkl = leaflet.LayerGroup.new()

    def dotask():
        items = todo[0:chunksize]

        for spot in items:
            m = draw_one_marker(spot)
            m.addTo(mkl)

        del todo[0:chunksize]

        if len(todo) > 0:
            timer.set_timeout(dotask, chunkdelay)
            load_percent = 1 - (len(todo) / len(data))
            load_str = "Loading {:.1%} ...".format(load_percent)
            document['hotspot-info'].text = load_str
        else:
            enable_input(True)
            document['hotspot-info'].text = ''

    timer.set_timeout(dotask, chunkdelay)
    return mkl

def hotspot_get_jq(resp_data, text_status, jqxhr):
    # resp_data.data is already json
    if resp_data.status == 'success':
        marker_layer.clearLayers()
        document['hotspot-info'].text = 'Loading...'

        data = resp_data.data
        date_jul = resp_data.date_jul

        if date_jul not in marker_dated:
            _mkl = draw_chunks(data, date_jul)
            marker_dated[date_jul] = _mkl
        else:
            _mkl = marker_dated[date_jul]

        _mkl.addTo(marker_layer)
        marker_layer.addTo(lmap)
        enable_input(True)
    else:
        document['hotspot-info'].text = 'Error retrieving hotspots'
        enable_input(True)

    global fetch_in_progress
    fetch_in_progress = False

# jQuery is somehow way faster
# get point for today
def get_point_jq(ev):
    query_ajax()

lmap.on('load', get_point_jq)

leaflet.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png", {
    "maxZoom": 18,
    "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(lmap)

lmap.setView([13, 100.8], 6)

# for browser console debug only
window.lmap = lmap
window.marker_layer = marker_layer
window.marker_dated = marker_dated
