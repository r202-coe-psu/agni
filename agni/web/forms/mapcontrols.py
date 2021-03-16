import datetime

from flask_wtf import FlaskForm
from wtforms import (
    Form, StringField, SelectField, IntegerField, FormField, RadioField,
    ValidationError
)

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

class HistoryControlForm(FlaskForm):
    start = FormField(
        YearMonthSelect, 
        label='Time Start'
    )
    end = FormField(
        YearMonthSelect,
        label='Time End'
    )
    data_type = RadioField(
        label="Data Type", 
        choices=FORMS_NRT_VALUES,
        validate_choice=True,
        default='count'
    )

