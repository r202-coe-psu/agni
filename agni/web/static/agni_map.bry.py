from browser import document, window, ajax, bind, timer
import javascript
import datetime

leaflet = window.L
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

viirs_mkl = {}
modis_mkl = {}

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

    if target_jul in marker_dated:
        marker_layer.clearLayers()
        marker_layer.addLayer(marker_dated[target_jul])
        enable_input(True)
    else:
        fetch_in_progress = True
        query_ajax(target_str)

def enable_input(state=True):
    document['hotspot-date-offset'].disabled = not state
    document['hotspot-date'].disabled = not state
    #if state:
    #    document['hotspot-query'].classList.remove('disabled')
    #else:
    #    document['hotspot-query'].classList.add('disabled')

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
def date_query(ev):
    enable_input(False)
    target_val = document['hotspot-date'].value
    target = datetime.datetime.strptime(target_val, '%Y-%m-%d')
    slider_offset = datetime.datetime.today() - target
    slider_offset = max(0, 60-slider_offset.days)
    document['hotspot-date-offset'].value = slider_offset
    change_or_query(target)

@bind('#hotspot-date', 'change')
def datepicker_query(ev):
    date_query(ev)

@bind('#hotspot-date-offset', 'input')
def sync_date(ev):
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
