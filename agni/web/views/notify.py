from flask import (
    Blueprint, 
    current_app, request, session,
    jsonify, url_for, redirect, abort,
    render_template, render_template_string
)

from agni.models import UserRegionNotify, Region

from ..oauth2 import oauth2_client as oauth2c
from ..forms.notify import NotificationRegisterForm

import logging
logger = logging.getLogger(__name__)

module = Blueprint('notify', __name__, url_prefix='/notify-register')

@module.route('/authorize')
def authorize():
    redirect_uri = url_for('notify.callback', _external=True)
    logger.debug("redirect_uri: {}".format(redirect_uri))
    return oauth2c.linenotify.authorize_redirect(redirect_uri)

@module.route('/callback', methods=['GET','POST'])
def callback():
    # get code and status
    if request.method == 'GET':
        params = request.args.to_dict(flat=True)
    elif request.method == 'POST':
        # code and status is parsed from form POST instead of query args
        params = request.form.to_dict(flat=True)
    
    if 'form_preauth' in session:
        session['form_postauth'] = params

    return redirect(url_for('notify.register_page'))

@module.route('/', methods=['GET'])
def register_page():
    form_data = session.pop('form_preauth', {})
    auth_data = session.pop('form_postauth', {})
    all_data = {**form_data, **auth_data}

    form = NotificationRegisterForm(data=all_data)
    form.regions.choices = [('kuankreng', 'Kuan Kreng')]

    auth = bool(auth_data)
    if auth:
        form.notify_authorize.label.text = 'LINE Notify Connected'

    return render_template(
        '/notify/register.html', 
        form=form, auth=auth
    )

@module.route('/', methods=['POST'])
def register_form():
    form = NotificationRegisterForm(request.form)
    form.regions.choices = [('kuankreng', 'Kuan Kreng')]

    if form.is_submitted():
        # clicked on authorize button
        if form.notify_authorize.data:
            session['form_preauth'] = dict(form.data)
            return redirect(url_for('notify.authorize'))

        # clicked on confirm button
        # user should have clicked on the authorize button before
        if form.validate() and form.confirm.data:
            # get the actual token
            token = oauth2c.linenotify.authorize_access_token(
                code=form.code.data,
                state=form.state.data
            )

            # commit token to db for later use
            notify = UserRegionNotify()
            notify.name = form.name.data
            notify.access_token = token.get('access_token')
            regions = form.regions.data
            for region in regions:
                reg_db = Region.objects.get(name=region)
                notify.regions.append(reg_db)
            notify.save()

            # clear session
            # CLEAR IT AFTER GETTING TOKEN, YOU HAVE BEEN WARNED
            # ELSE CSRF MISMATCH AND OTHER WEIRD SHIT
            session.clear()
            # perhaps redirect back to main page?
            return render_template('/notify/register_success.html')
            #return jsonify(form.data, token)
    
    # something went wrong, shouldn't be here
    if current_app.debug:
        form_data = session.pop('form_preauth', {})
        auth_data = session.pop('form_postauth', {})
        return jsonify(
            "DEBUG DEBUG DEBUG WHY ARE YOU HERE DEBUG DEBUG DEBUG", 
            form.data, 
            form.errors
        ), 400
    return abort(400)