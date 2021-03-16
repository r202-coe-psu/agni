import datetime

from flask_wtf import FlaskForm
from wtforms import (
    Form, 
    StringField, SelectField, IntegerField, FormField, RadioField, DateField,
    BooleanField,
    ValidationError,
    fields, widgets
)
from wtforms.fields import html5
from markupsafe import Markup

YEAR_START = 2000
YEAR_END = datetime.datetime.now().year

FORMS_MONTHS = [
    (m, datetime.datetime(YEAR_START, m, 1).strftime('%B'))
    for m in range(1, 13)
]
FORMS_NRT_VALUES = [
    ('count', 'Count'),
    ('frp', 'FRP'),
    ('bright_ti4', 'Temperature I-4'),
    ('bright_ti5', 'Temperature I-5'),
]

class YearMonthSelect(Form):
    year = IntegerField(label='Year', default=2000)
    month = SelectField(label='Month', choices=FORMS_MONTHS, default=1)

    def validate_year(form, field):
        if not (YEAR_START <= field.data <= YEAR_END):
            raise ValidationError('Year outside available data range.')

class McssRadioWidget(object):
    def __init__(self, html_tag='div'):
        self.html_tag = html_tag

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        html = []#['<%s %s>' % (self.html_tag, widgets.html_params(**kwargs))]
        for subfield in field:
            html.append((
                '<p>'
                '<label>%s <span>%s</span></label>'
                '</p>'
            ) % (subfield(class_='with-gap'), subfield.label.text))
        #html.append('</%s>' % self.html_tag)
        return Markup(''.join(html))

class McssRadioField(RadioField):
    widget = McssRadioWidget(widgets.Input())

class MapControls(FlaskForm):
    class Meta:
        csrf = False

class HistoryControlForm(MapControls):
    class Meta:
        csrf = False

    mode = RadioField(
        label='Time Range',
        choices=[
            ('timerange', 'Time Range'),
            ('yearly', 'By Year'),
            ('monthly', 'By Month'),
        ],
        default='timerange'
    )

    # timerange mode
    start = FormField(
        YearMonthSelect, 
        label='Time Start'
    )
    end = FormField(
        YearMonthSelect,
        label='Time End'
    )

    # monthly mode
    monthly = SelectField(
        label='Month', choices=FORMS_MONTHS, default=1
    )
    years_over = IntegerField(
        label='Aggregate over years'
    )

    # yearly mode
    yearly = IntegerField(
        label='Year', 
    )

    data_type = SelectField(
        label="Data Type", 
        choices=FORMS_NRT_VALUES,
        default='count'
    )

class HotspotControlForm(MapControls):
    date = fields.DateField(label='Date')
    date_slider = html5.IntegerRangeField()

    last_24h = BooleanField(label='Last 24 hours')

    color_by = RadioField(
        label='Color Hotspots By',
        choices=[
            ('none', 'None'),
            ('confidence', 'Confidence'),
            ('cluster', 'Clustering Status')
        ],
        default='none'
    )

class PredictControlForm(MapControls):
    base_date = DateField(
        label='Base Date'
    )

    lag_day = IntegerField(
        label='Burned Area Data'
    )