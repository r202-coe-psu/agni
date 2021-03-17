from browser import document, window, ajax, bind, timer
import javascript as js
import datetime

leaflet = window.L
turf = window.turf
jq = window.jQuery
mcss = window.M

_js_now = js.Date.new

BASE_MARKER_OPTS = {
    "stroke": False,
    "radius": 5,
    "color": 'orange',
    "fillOpacity": 0.7
}

DBSCAN_MARKER_OPTS = {
    "core": dict(BASE_MARKER_OPTS, color="red", fillOpacity=0.75),
    "edge": dict(BASE_MARKER_OPTS, color="red"),
    "noise": dict(BASE_MARKER_OPTS, color="orange"),
}

ROI_STYLE = {
    "stroke": True,
    "color": '#33aa33',
    "opacity": 0.8,
    "fillColor": '#33aa33',
    "fillOpacity": 0.1,
    "weight": 2
}

CELLSTYLE = {
    'TREE': {
        'color': 'green',
        'fillColor': 'green',
        'fillOpacity': 0.2,
        'fill': False,
        'weight': 1,
        'stroke': False
    },
    'FIRE': {
        'color': 'red',
        #'weight': 0.5,
        'stroke': False,
        'fillColor': 'red',
        'fillOpacity': 0.3,
    },
    'EMPTY': {
        'stroke': False,
        'fillColor': 'black',
        'fillOpacity': 0.3
    }
}
def get_cell_style(feature):
    celltype = feature.properties.celltype
    return CELLSTYLE[celltype]

CHOROPLETH_BINS = ['#ffffb2','#fecc5c','#fd8d3c','#e31a1c']

ZONE_SELECT_STYLE = {
    'weight': 2,
    'fillOpacity': 0,
    'dashArray': '8, 8'
}

CLUSTER_CONVEX_STYLE = {
    'weight': 2,
    'fillOpacity': 0.2,
    'dashArray': '4, 4',
    'color': CHOROPLETH_BINS[3],
    'fillColor': CHOROPLETH_BINS[1]
}

# set up materialize css stuff
DP_OPTS = {
    "setDefaultDate": True,
    "defaultDate": _js_now(),
    "maxDate": _js_now(),
    "format": "yyyy-mm-dd",
    "container": document['main-row']
}

GOOGLE_MAPS_API_URL = 'https://www.google.com/maps/search/?api=1'

# materialize css init
dp_elems = document.querySelectorAll('.datepicker')
dp_instances = mcss.Datepicker.init(dp_elems, DP_OPTS)

sel_elems = document.querySelectorAll('select')
sel_instances = mcss.FormSelect.init(sel_elems)

tab_elems = document.querySelectorAll('.tabs')
tab_instances = mcss.Tabs.init(tab_elems)

range_elems = document.querySelectorAll("input[type=range]")
range_instance = mcss.Range.init(range_elems)

# leaflet init
lmap = leaflet.map("mapdisplay", {
    "preferCanvas": True,
    "doubleClickZoom": False
})

marker_layer = leaflet.LayerGroup.new()
marker_dated = {}

viirs_layer = leaflet.LayerGroup.new()
modis_layer = leaflet.LayerGroup.new()

viirs_marker_dated = {}
modis_marker_dated = {}

turf_dated = {}
clustered_layer = leaflet.LayerGroup.new()
raw_layer = leaflet.LayerGroup.new()
roi_layer = leaflet.FeatureGroup.new()
predict_layer = leaflet.FeatureGroup.new()
history_layer = leaflet.FeatureGroup.new()

viirs_mkl = {}
modis_mkl = {}

roi_name = False
roi_name = 'all'

fetch_in_progress = False

def toast(text, icon=None, **toastopts):
    html_icon = ''
    if icon is not None:
        html_icon = '<i class="material-icons">{icon}</i>'.format(icon=icon)

    html_text = '{}<span>{}</span>'.format(html_icon, text)
    opts = {
        'html': html_text,
        'displayLength': 3000,
        'classes': 'toast-text'
    }

    return mcss.Toast.new(dict(opts, **toastopts))

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

    raw_layer.clearLayers()
    clustered_layer.clearLayers()

    try:
        turf_dated[target_jul, roi_name, 'raw'].addTo(raw_layer)
        turf_dated[target_jul, roi_name, 'turf'].addTo(clustered_layer)
    except KeyError:
        fetch_in_progress = True
        query_ajax_cluster(target_str)

def date_from_offset(offset, maxdelta=30):
    # maxdelta of 30 for last month
    today = datetime.datetime.today()
    delta = datetime.timedelta(days=(maxdelta-offset))

    return today-delta

def draw_roi(roi_name, clear=True):
    def draw_roi_jq(resp, status, jqxhr):
        g = leaflet.geoJSON(resp, {"style":ROI_STYLE}).addTo(roi_layer)
        lmap.fitBounds(g.getBounds())

    if clear:
        roi_layer.clearLayers()
    if roi_name != 'all':
        jq.ajax('/regions/{}'.format(roi_name), {
            "dataType": "json",
            "success": draw_roi_jq
        })

@bind('#region-select', 'change')
def region_changed(ev):
    change_src = ev.target.id
    if change_src == 'region-list':
        global roi_name
        roi_name = ev.target.value
        draw_roi(roi_name)

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
    elif change_src == 'hotspot-date':
        # changes from date picker
        new_offset = today - date_cal
        document['hotspot-date-offset'].value = max(0, 30-new_offset.days)

predict_zone = 'zone-roi'
zone_layer = leaflet.LayerGroup.new()
zone_rect = None
zone_bounds = None

@bind('#do-predict', 'click')
def request_predict(ev):
    if predict_zone == 'zone-roi' and roi_name != 'all':
        b = roi_layer.getBounds()
        bounds = b.toBBoxString()
        print(bounds)
        zone_layer.clearLayers()
        z = leaflet.Rectangle.new(b).setStyle(ZONE_SELECT_STYLE)
        z.addTo(zone_layer).addTo(lmap)
    else:
        print('not possible')
        toast("Invalid Selection.")
        return

    drop_noise = document["ignore-noise"].checked
    #drop_low = document['ignore-low'].checked
    lag = document['lag-days'].value

    req_params = {
        'lagdays': int(lag),
        'area': bounds,
        'date': document['hotspot-date'].value,
        'dropnoise': drop_noise,
        #'droplow': drop_low
    }
    print(req_params)

    def draw_prediction(geojson):
        predict_layer.clearLayers()
        leaflet.geoJSON(
            geojson, {'style': get_cell_style}
        ).addTo(predict_layer)
        predict_layer.addTo(lmap)

    def req_success(resp, status, jqxhr):
        if jqxhr.status == 200:
            draw_prediction(resp)
        elif jqxhr.status == 204:
            toast("Prediction: empty results.", icon='info')

    def req_error(jqxhr, jq_error, text_error):
        toast("Predict: Error '{}': {}".format(jq_error, text_error),
              icon='error')

    jq.ajax('/predict.geojson', {
        "dataType": "json",
        "data": req_params,
        "success": req_success,
        "error": req_error
    })

@bind('#do-predict-clear', 'click')
def clear_predict(ev):
    predict_layer.clearLayers()
    zone_layer.clearLayers()

def wtforms_csrf_inject(csrf_token):
    def add_csrf(xhr, settings):
        re = js.RegExp.new('^(GET|HEAD|OPTIONS|TRACE)$', 'i')
        if not (re.test(settings.type) or js.this().crossDomain):
            xhr.setRequestHeader("X-CSRFToken", csrf_token)

    jq.ajaxSetup({
        'beforeSend': add_csrf
    })

def props_format_html(props, unit=''):
    if not isinstance(props, dict):
        props = props.to_dict()

    features_str = []
    for k, v in props.items():
        if unit != '' and k == 'value':
            kv_str = "<b>{}</b>: {} {}".format(k, v, unit)
        else:
            kv_str = "<b>{}</b>: {}".format(k, v)
        features_str.append(kv_str)

    feature_html = '<br />'.join(features_str)
    return feature_html

# choropleth
# low to high
chrp = None

def info_onadd(map_):
    this = js.this()
    map_.info_ctrl = this
    this._div = leaflet.DomUtil.create('div', 'info')
    this.update()
    return this._div

def info_onremove(map_):
    map_.info_ctrl = None

def info_update(props=None):
    this = js.this()
    if props is not None:
        this._div.innerHTML = props_format_html(props)
    else:
        this._div.innerHTML = 'Hover over heatmap cells for info'

Info_ctrl = leaflet.Control.extend({
    'options': {
        'position': 'bottomright'
    },
    'onAdd': info_onadd,
    'onRemove': info_onremove,
    'update': info_update
})
info_ctrl = Info_ctrl.new()
info_ctrl.addTo(lmap)
# /choropleth

def value_map(value, in_bounds, out_bounds):
    in_min, in_max = in_bounds
    out_min, out_max = out_bounds
    return (value-in_min) * (out_max-out_min) / (in_max-in_min) + out_min

@bind('#do-history', 'click')
def show_history(ev):
    if roi_name == 'all':
        toast(text="Must pick a region", icon="error")
        return

    form_serialize = jq('#history-options').serialize()
    form_data = window.FormData.new(document['history-options'])
    form_dict = dict(x for x in form_data.entries())

    data_type = form_dict['data_type']
    csrf_token = form_dict['csrf_token']

    def generate_colors_func(colors, lower, upper):
        color_class = len(colors)

        def get_color(value):
            cindex = value_map(value, (lower, upper), (0, color_class))
            cindex = max(0, min(color_class-1, cindex))
            return colors[cindex]

        return get_color

    def highlight_feature(e):
        layer = e.target

        layer.setStyle({
            "color": '#666',
            "fillOpacity": 0.75,
            "stroke": True,
            "weight": 1
        })
        info_ctrl.update(layer.feature.properties.to_dict())

        if not (leaflet.Browser.ie
                or leaflet.Browser.opera
                or leaflet.Browser.edge):
            layer.bringToFront()

    def highlight_reset(e):
        global chrp
        chrp.resetStyle(e.target)
        info_ctrl.update()

    def histogram_cell_style(feature, input_bounds, output_bounds):
        value = feature.properties.value

        base_cell = CELLSTYLE['FIRE']

        colorfunc = generate_colors_func(CHOROPLETH_BINS, *input_bounds)
        cell_color = colorfunc(value)

        style = dict(
            base_cell,
            #fillColor=cell_color,
            fillOpacity=value_map(value, input_bounds, output_bounds)
            #fillOpacity=0.5
        )
        return style

    def histogram_cell_features(feature, layer, unit=''):
        props = feature.properties.to_dict()
        info_ctrl.update(props)

        props_html = props_format_html(props, unit)
        layer.bindPopup(props_html)

        layer.on({
            "mouseover": highlight_feature,
            "mouseout": highlight_reset
        })

    def req_success(resp, status, jqxhr):
        if jqxhr.status == 200:
            global chrp
            min_val = resp.info.min_value
            max_val = resp.info.max_value
            unit = resp.info.value_unit
            bounds = [min_val, max_val]
            print(bounds, max_val-min_val)

            history_layer.clearLayers()
            chrp = leaflet.geoJSON(
                resp, 
                {
                    'style': lambda s: histogram_cell_style(
                        s, bounds, [0.2, 0.5]
                    ),
                    'onEachFeature': lambda f, l: histogram_cell_features(
                        f, l, unit
                    )
                }
            )
            chrp.addTo(history_layer)
            history_layer.addTo(lmap)

    def req_error(jqxhr, jq_error, text_error):
        toast("History: Error '{}': {}".format(jq_error, text_error),
              icon='error')

    wtforms_csrf_inject(csrf_token)
    jq.ajax("/history/{region}/{data_type}".format(
            region=roi_name, data_type=data_type
        ),
        {
            'type': 'POST',
            'dataType': 'json',
            'data': form_serialize,
            'success': req_success,
            'error': req_error
        }
    )
    ev.preventDefault()

@bind('#color-frp', 'click')
def color_hotspots_frp(ev):
    layer_js = raw_layer.getLayers()[0].getLayers()[0]
    layers = layer_js.getLayers()
    for layer in layers:
        props = layer.feature.properties
        style = color_frp(props)
        layer.setStyle(style)
    
    def raise_layer(layer):
        props = layer.feature.properties
        if props.frp >= 90:
            layer.bringToFront()
    layer_js.eachLayer(raise_layer)


@bind('#color-confidence', 'click')
def color_hotspots_confidence(ev):
    layer_js = raw_layer.getLayers()[0].getLayers()[0]
    layers = layer_js.getLayers()
    for layer in layers:
        props = layer.feature.properties
        style = color_confidence(props)
        layer.setStyle(style)

    def raise_layer(layer):
        props = layer.feature.properties
        if confidence_coerce(props) == 'high':
            layer.bringToFront()
    layer_js.eachLayer(raise_layer)

@bind('#color-confidence', 'click')
@bind('#color-frp', 'click')
def change_button_color(ev):
    target = ev.target
    for id_class in ['color-frp', 'color-confidence']:
        if id_class in target.id:
            document[id_class].classList.replace('btn-flat', 'btn')
        else:
            document[id_class].classList.replace('btn', 'btn-flat')

# turf test

def color_frp(props):
    frp = props.frp
    if frp < 30:
        return dict(
            BASE_MARKER_OPTS, 
            color=CHOROPLETH_BINS[1], 
            opacity=0.35
        )
    elif 30 <= frp < 90:
        return dict(BASE_MARKER_OPTS, color=CHOROPLETH_BINS[2])
    else:
        return dict(BASE_MARKER_OPTS, color=CHOROPLETH_BINS[3])

def confidence_coerce(props):
    def confidence_map(percent):
        if 75 <= percent <= 100:
            return 'high'
        elif 0 <= percent < 30:
            return 'low'
        else:
            return 'nominal'

    try:
        return props.confidence
    except AttributeError:
        return confidence_map(props.confidence_percent)


def color_confidence(props):
    confidence_colors_map = {
        'low': CHOROPLETH_BINS[1],
        'nominal': CHOROPLETH_BINS[2],
        'high': CHOROPLETH_BINS[3]
    }

    conf = confidence_coerce(props)

    opts = dict(
        BASE_MARKER_OPTS,
        color=confidence_colors_map[conf],
        fillOpacity=(conf == 'high' and 0.7 or 0.5)
    )
    return opts

def cluster_data(resp, status, jqxhr):
    marker_layer.clearLayers()
    turf_layer = leaflet.LayerGroup.new()
    turf_layer.clearLayers()

    geojson = resp
    # draw cluster convex and centroid to separate layer
    def process_cluster(cluster, clusterValue, currentIndex):
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
        leaflet.geoJSON(cnv, {'style': CLUSTER_CONVEX_STYLE}).addTo(turf_layer)

    clustered = geojson
    turf.clusterEach(clustered, "cluster", process_cluster)
        
    def turf_markers(feature, latlng):
        props = feature.properties
        opts = color_frp(props)
        return leaflet.circleMarker(latlng, opts)

    def turf_features(feature, layer):
        props = feature.properties.to_dict()

        # format time for display
        utc_time = js.Date.new(props['time'])
        props['time'] = utc_time.toLocaleString()
        features_str = [
            "<b>{}</b>: {}".format(k, v)
            for k, v in props.items()
        ]

        coords = layer.getLatLng() # leaflet's LatLon object
        coords_link = '&'.join([
            GOOGLE_MAPS_API_URL,
            'query={lat},{lon}'
        ]).format(lat=coords.lat, lon=coords.lng)
        coords_html = (
            '<a href="{link}" target="_blank">Open in Google maps</a>'
        ).format(link=coords_link)
        features_str.append(coords_html)

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
    turf_dated[date_str, roi_name, 'raw'] = raw_points
    turf_dated[date_str, roi_name, 'turf'] = turf_layer

    raw_points.addTo(raw_layer)
    turf_layer.addTo(clustered_layer)

    global fetch_in_progress
    fetch_in_progress = False

def query_ajax_cluster(target=None):
    """ send request to server using ajax
        Args: target (string): 
            date to query, formatted to '%Y-%m-%d'
    """
    def query_error(jqxhr, errortype, text):
        toast("Error {}: {}".format(jqxhr.status, text))

    def query_success(resp, status, jqxhr):
        if jqxhr.status == 200:
            cluster_data(resp, status, jqxhr)
        elif jqxhr.status == 204:
            toast('No data', icon='info')

    data = {}
    if target is not None:
        data = {"date": target}

    data['roi'] = roi_name

    jq.ajax('/clustered.geojson', {
        "dataType": "json",
        "data": data,
        "success": query_success,
        "error": query_error
    })
# /turf test

@bind('#hotspot-query', 'click')
@bind('#hotspot-date', 'change')
def date_query(ev):
    target_val = document['hotspot-date'].value
    target = datetime.datetime.strptime(target_val, '%Y-%m-%d')
    slider_offset = datetime.datetime.today() - target
    slider_offset = max(0, 30-slider_offset.days)
    document['hotspot-date-offset'].value = slider_offset
    change_or_query(target)

# TODO: nuke this too probably
@bind('#hotspot-date-offset', 'input')
def slider_sync_date(ev):
    offset = document['hotspot-date-offset'].value
    offset = 30 - int(offset)
    delta = datetime.timedelta(days=offset)
    target = datetime.datetime.today() - delta
    target_str = target.strftime('%Y-%m-%d')

    document['hotspot-date'].value = target_str

@bind('#hotspot-date-offset', 'change')
def date_query_slider(ev):
    offset = document['hotspot-date-offset'].value
    offset = 30 - int(offset)
    delta = datetime.timedelta(days=offset)
    target = datetime.datetime.today() - delta
    change_or_query(target)

def map_load_init(ev):
    query_ajax_cluster()

lmap.on('load', map_load_init)

base = leaflet.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png", {
    "maxZoom": 18,
    "attribution": ( 
        '&copy; '
        '<a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
        'contributors'
    )
})

leaflet.control.layers(
    {
        "Base": base.addTo(lmap)
    },
    {
        "Region": roi_layer.addTo(lmap),
        "Clustered": clustered_layer.addTo(lmap),
        "Raw Points": raw_layer.addTo(lmap),
        "Zone": zone_layer.addTo(lmap),
        "Prediction": predict_layer,
        "History": history_layer
    }
).addTo(lmap)
lmap.setView([13, 100.8], 6)
leaflet.control.scale({"imperial": False}).addTo(lmap)

# for browser console debug only
window.lmap = lmap
