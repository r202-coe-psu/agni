from browser import document, window
import datetime

mcss = window.M

JULIAN_FMT = '%Y%j'
WEB_FMT = '%Y-%m-%d'

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

def formdata_to_dict(form):
    form_data = window.FormData.new(form)
    return dict(x for x in form_data.entries())

def format_web(date):
    return date.strftime(WEB_FMT)

def parse_web(datestr):
    return datetime.datetime.strptime(datestr, WEB_FMT)

def format_julian(date):
    return date.strftime(JULIAN_FMT)

def parse_julian(datestr):
    return datetime.datetime.strptime(datestr, JULIAN_FMT)
