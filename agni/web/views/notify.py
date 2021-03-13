from flask import (
    Blueprint, 
    current_app, request, session,
    jsonify, url_for, render_template_string
)

from ..oauth2 import oauth2_client as oauth2c

import logging
logger = logging.getLogger(__name__)

module = Blueprint('notify', __name__, url_prefix='/notify-register')

@module.route('/', methods=['GET','POST'])
def start_register():
    html = """
    start <a href="{{auth_start}}" target="_blank">here</a>
    """
    return render_template_string(
        html, 
        auth_start=url_for('notify.authorize')
    )

@module.route('/authorize')
def authorize():
    redirect_uri = 'http://localhost:8080' + url_for('notify.callback')
    logger.debug("redirect_uri: {}".format(redirect_uri))
    return oauth2c.linenotify.authorize_redirect(redirect_uri)

@module.route('/callback', methods=['GET','POST'])
def callback():
    # get token from code
    if request.method == 'GET':
        mode = "request.args"
        token = oauth2c.linenotify.authorize_access_token()
    elif request.method == 'POST':
        # code and thatnot is parsed from form POSTed instead of
        # using query args
        mode = "form_post"
        params = request.form.to_dict(flat=True)
        token = oauth2c.linenotify.authorize_access_token(**params)

    # try using token: get status
    try:
        resp = oauth2c.linenotify.get('status', token=token)
        resp.raise_for_status()
    except:
        pass
    status = resp.json()

    html_template = """
        <style>
        span { font-family: monospace; }
        </style>
        <body>
        got token: <span>{{ token|safe }}</span>
        <br />
        got from mode: <span>{{ mode|safe }}</span>
        <br />
        {% if mode == "form_post" %}
        <span>{{ form_got|safe }}</span>
        <br />
        {% endif %}
        got status: <span>{{ status|safe }}</span>
        <body>
        """
    return render_template_string(
        html_template,
        token=token, status=status, mode=mode, form_got=params
    )