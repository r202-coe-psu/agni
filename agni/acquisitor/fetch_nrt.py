import datetime
import csv
import os
import sys

import requests

API_URL = 'https://nrt4.modaps.eosdis.nasa.gov/api/v2/content/archives/FIRMS/'
TOKEN = 'DB8ECCD2-41E6-11EA-8E17-6EBC4405026C'

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

def make_url(src, date):
    filedate = date.strftime('%Y%j')
    filename = "{}.txt".format(filedate)

    return ''.join([API_URL, src['url'], src['filename'], filename])

def reshape_csv(raw_csv):
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
        # make floats
        make_floats = ['latitude', 'longitude', 'bright_ti4', 'bright_ti5',
                       'bright_t32', 'frp']
        for k, v in line.items():
            if k in make_floats:
                line[k] = float(v)

        # change acq_{date,time} to unix epoch MICROseconds
        acq_datetime = datetime.datetime.fromisoformat(
            "{acq_date} {acq_time}".format(
                acq_date=line['acq_date'],
                acq_time=line['acq_time']
            )
        )
        # had to determine epoch time by dividing timedeltas
        # since strftime('%S') isn't guaranteed to be portable
        # just in case
        epoch_start = datetime.datetime(1970, 1, 1)
        usec_delta = datetime.timedelta(microseconds=1)
        acq_epoch = (acq_datetime - epoch_start) / usec_delta

        # dealing with duplicate acquire datetime for different data points
        # append offset to us to make it a unique point for influxdb
        # original data resolution is only a minute
        if acq_epoch == acq_epoch_last:
            acq_dupe += 1
        else:
            acq_dupe = 0

        line['acq_time'] = int(acq_epoch + acq_dupe)
        acq_epoch_last = acq_epoch

        # add to known hotspots
        hotspots.append(line)

    # return hotspots
    return hotspots

def nrt_to_lineprot(nrt, measure, timekey, tags=None):
    """ reshape NRT data to line protocol compatible with InfluxDB
        needs testing

        Args:
            nrt (dict):
                NRT data point as dict
            measure (str):
                InfluxDB measure name
            timekey (str):
                name of key in dict which contains timestamp
                as unix epocj microseconds
            tags (list of str):
                list of keys within dict which should be made into tags
                instead of fields (optional)

        Return:
            line_protocol (str):
                formatted line protocol usable with InfluxDB
    """
    line_fields = {}
    line_tags = {}

    for key, val in nrt.items():
        if key in tags:
            _val = str(val)
            line_tags[key] = _val
        else:
            line_fields[key] = val

    # test formatting them into a line protocol format
    fields_out = [
        '='.join([str(k), str(v)])
        for k, v in line_fields.items()
        if k != timekey
    ]

    tags_out = [
        '='.join([str(k), str(v)])
        for k, v in line_tags.items()
    ]

    lineprot_str = "{measure},{tags} {fields} {time}".format(
        measure=measure,
        tags = ','.join(tags_out),
        fields=','.join(fields_out),
        time=str(line_fields[timekey])
    )

    #print(line_out_str, flush=True)
    # merge tags and fields into one entity
    return lineprot_str


def request_nrt(date=None, src=None):
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
    if date is None:
        date = datetime.datetime.today()
    if src is None:
        src = SRC_VIIRS

    #filedate = date.strftime('%Y%j')

    url = make_url(src, date)
    r = requests.get(url, headers={'Authorization': 'Bearer '+TOKEN})
    return r

def get_nrt_data(date=None, src=None):
    if src is None:
        src = SRC_VIIRS

    req = request_nrt(date, src)

    req.raise_for_status()
    hotspots = {}
    hotspots = reshape_csv(req.text, src['name'])

    return hotspots

