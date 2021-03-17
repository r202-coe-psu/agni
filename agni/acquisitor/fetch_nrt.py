from agni.models import region
import datetime
import csv
import io
import warnings

import requests
import pandas as pd

from ..util import timefmt

API_URL = 'https://nrt4.modaps.eosdis.nasa.gov/api/v2/content/archives/FIRMS/'
__TOKEN = None

class SatSrc:
    def __init__(self, name=None, url=None, filename=None, base_url=None):
        self.name = name
        self.base_url = base_url
        self.url = url
        self.filename = filename
    
    def to_url(self, date):
        filedate = timefmt.format_julian(date)
        filename_dated = "{}{}.txt".format(self.filename, filedate)
        return '/'.join([self.base_url, self.url, filename_dated])

SRC_VIIRS = {
    'name': 'viirs',
    'url': 'viirs/SouthEast_Asia/',
    'filename': 'VIIRS_I_SouthEast_Asia_VNP14IMGTDL_NRT_'
}
SRC_SUOMI = {
    'name': 'suomi',
    'url': 'suomi-npp-viirs-c2/SouthEast_Asia/',
    'filename': 'SUOMI_VIIRS_C2_SouthEast_Asia_VNP14IMGTDL_NRT_',
}
SRC_MODIS = {
    'name': 'modis',
    'url' : 'c6/SouthEast_Asia/',
    'filename': 'MODIS_C6_SouthEast_Asia_MCD14DL_NRT_'
}
SRC_NOAA = {
    'name': 'noaa',
    'url': 'noaa-20-viirs-c2/SouthEast_Asia/',
    'filename': 'J1_VIIRS_C2_SouthEast_Asia_VJ114IMGTDL_NRT_'
}

MAKE_FLOATS = [
    'latitude', 'longitude',
    'scan', 'track',
    'bright_ti4', 'bright_ti5', 'bright_t32',
    'frp',
]
SKIP = ['acq_date', 'acq_time']

class NoTokenError(Exception):
    pass

def set_token(token):
    global __TOKEN
    __TOKEN = token

def check_token(token=None):
    if token is not None:
        return token
    elif __TOKEN is not None:
        return __TOKEN
    else:
        raise NoTokenError("FIRMS API Token key required.")

def make_url(src, date, api_url=None):
    if api_url is None:
        api_url = API_URL

    if isinstance(src, SatSrc):
        url = src.url
        filename = src.filename
    else:
        url = src['url']
        filename = src['filename']
    
    filedate = timefmt.format_julian(date)
    filename_dated = "{}{}.txt".format(filename, filedate)

    return ''.join([api_url, url, filename_dated])

def process_csv(raw_csv):
    """preprocess NRT raw CSV to python dict

    Args:
        raw_csv (str):
            NRT Data in csv format
    """
    hotspots = []
    csv_reader = csv.DictReader(raw_csv.splitlines())
    acq_epoch_last = None
    acq_dupe = 0
    for line in csv_reader:
        out = {}
        # change acq_{date,time} to unix epoch MICROseconds
        acq_datetime = datetime.datetime.fromisoformat(
            "{acq_date} {acq_time}".format(
                acq_date=line['acq_date'],
                acq_time=line['acq_time']
            )
        )
        acq_epoch = timefmt.format_epoch_us(acq_datetime)

        # dealing with duplicate acquire datetime for different data points
        # append offset to us to make it a unique point for influxdb
        # original data resolution is only a minute
        if acq_epoch == acq_epoch_last:
            acq_dupe += 1
        else:
            acq_dupe = 0

        point_time = int(acq_epoch + acq_dupe)
        out['time'] = timefmt.parse_epoch_us(point_time)
        acq_epoch_last = acq_epoch

        for k, v in line.items():
            if k in SKIP:
                continue
            if k in MAKE_FLOATS:
                out[k] = float(v)
            else:
                out[k] = v

        # add to known hotspots
        hotspots.append(out)

    # return hotspots
    return hotspots

def df_as_dict(df: pd.DataFrame):
    df_list = df.to_dict('records')
    for point in df_list:
        point['time'] = point['time'].to_pydatetime()

    return df_list

def process_csv_pandas(raw_csv, as_dict=False):
    csv_str_io = io.StringIO(raw_csv)
    hotspots = pd.read_csv(
        csv_str_io, 
        parse_dates={
            'time': ['acq_date', 'acq_time']
        }
    )

    # no data yet, but file header exist
    if len(hotspots) == 0:
        return [] if as_dict else hotspots
    
    # dedupe time to usec offset
    time_dupe = hotspots.groupby('time').cumcount()
    hotspots['time'] = (hotspots['time']
                        + pd.to_timedelta(time_dupe, unit='us'))

    if as_dict:
        return df_as_dict(hotspots)

    return hotspots

def request_nrt(date=None, src=SRC_SUOMI, token=None):
    """Fetch NRT Data from NASA (SEA Region) by date

    Args:
        date (datetime.date):
            target date for data fetching
            can go back at most 2 months from today.
            defaults to today
        src (one of SRC_{VIIRS,SUOMI,NOAA,MODIS}):
            target satellite for request
            defaults to VIIRS (optional)
    """
    token = check_token(token)

    if date is None:
        date = datetime.datetime.today()

    url = make_url(src, date)
    r = requests.get(
        url, 
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )
    return r

def get_nrt_data(
        date=None, src=None, silent_404=True, as_dict=True, token=None
    ):
    if src is None:
        src = SRC_SUOMI
    token = check_token(token)

    hotspots = []
    req = request_nrt(date, src, token)
    if req.ok:
        hotspots = process_csv_pandas(req.text)
        hotspots['instrument'] = 'MODIS' if src == SRC_MODIS else 'VIIRS'
        if as_dict:
            hotspots = df_as_dict(hotspots)
    elif req.status_code == 404 and silent_404:
        warn_str = 'Server reported 404 for file {}.'.format(req.url)
        warnings.warn(warn_str)
    else:
        req.raise_for_status()

    return hotspots

