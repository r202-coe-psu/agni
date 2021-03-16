from wtforms import Form, fields, validators
from wtforms.fields import html5

from flask_wtf import FlaskForm
from flask import request

from .. import models
from .fields import MultiCheckboxField

class NotificationRegisterForm(FlaskForm):
    name = fields.TextField(
        'Name',
        validators=[validators.InputRequired()]
    )
    regions = MultiCheckboxField(
        'Regions',
        validators=[validators.InputRequired()]
    )

    code = fields.HiddenField(
        'LINE Notify Code',
        validators=[validators.DataRequired()]
    )
    state = fields.HiddenField(
        'LINE Notify State',
        validators=[validators.DataRequired()]
    )

    notify_authorize = fields.SubmitField('Connect to LINE Notify')
    confirm = fields.SubmitField('Confirm Registration')

