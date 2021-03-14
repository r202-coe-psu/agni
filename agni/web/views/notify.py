from flask import (
    Blueprint, 
    current_app, request, session,
    jsonify, url_for, render_template_string, redirect
)

from ..oauth2 import oauth2_client as oauth2c

from ..forms.notify import NotificationRegisterForm

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
    #redirect_uri = 'http://localhost:8080' + url_for('notify.callback')
    redirect_uri = url_for('notify.callback', _external=True)
    logger.debug("redirect_uri: {}".format(redirect_uri))
    return oauth2c.linenotify.authorize_redirect(redirect_uri)

@module.route('/callback', methods=['GET','POST'])
def callback():
    token = None
    # get token from code
    if request.method == 'GET':
        mode = "request.args"
        params = request.args.to_dict(flat=True)
        #token = oauth2c.linenotify.authorize_access_token()
    elif request.method == 'POST':
        # code and whatnot is parsed from form POST instead of
        # using query args
        mode = "form_post"
        params = request.form.to_dict(flat=True)
        #token = oauth2c.linenotify.authorize_access_token(**params)
    
    if 'form_preauth' in session:
        session['form_postauth'] = params
        return redirect(url_for('notify.register_page'))

    if token is not None:
        # try using token: get status
        resp = oauth2c.linenotify.get('status')
        #resp.raise_for_status()
        status = resp.json()

        html_template = """
            <style>
            span { font-family: monospace; }
            </style>
            <body>
            got from mode: <span>{{ mode|safe }}</span> <br />
            {% if mode == "form_post" %}
            content: <span>{{ form_got|safe }}</span> <br />
            {% endif %}
            got token: <span>{{ token|safe }}</span> <br />
            got status: <span>{{ status|safe }}</span>
            <body>
            """
        return render_template_string(
            html_template,
            token=token, status=status, mode=mode, form_got=params
        )

@module.route('/register', methods=['GET'])
def register_page():
    html = """
    <h1>Register for hotspots notifications</h1>
    <form action="{{ url_for('notify.register_form') }}" method="post">
        {{ form.csrf_token }}
        {{ form.hidden_tag() }}
        <fieldset>{{ form.name.label }}: {{ form.name }}</fieldset>
        <fieldset>{{ form.regions.label }}: {{ form.regions }}</fieldset>
        {% if auth %}
        {{ form.confirm }}
        {% else %}
        {{ form.notify_authorize }}
        {% endif %}
    </form>
    """
    
    form_data = session.pop('form_preauth', {})
    auth_data = session.pop('form_postauth', {})
    all_data = {**form_data, **auth_data}

    form = NotificationRegisterForm(data=all_data)
    form.regions.choices = [('kuankreng', 'Kuan Kreng')]

    return render_template_string(html, form=form, auth=bool(auth_data))

@module.route('/register', methods=['POST'])
def register_form():
    form = NotificationRegisterForm()
    form.regions.choices = [('kuankreng', 'Kuan Kreng')]

    if form.is_submitted():
        if form.notify_authorize.data:
            session['form_preauth'] = dict(form.data)
            return redirect(url_for('notify.authorize'))
        
        if form.validate() and form.confirm.data:
            token = oauth2c.linenotify.authorize_access_token(
                code=form.code.data,
                state=form.state.data
            )
            # commit to db here
            # clear session
            # CLEAR IT AFTER GETTING TOKEN, YOU HAVE BEEN WARNED
            session.clear()
            return jsonify(form.data, token)
    

    form_data = session.pop('form_preauth', {})
    auth_data = session.pop('form_postauth', {})
    return jsonify(form.data, form.errors)