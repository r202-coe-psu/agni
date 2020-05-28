import requests
import datetime
import csv
import os
import sys

api_url = 'https://nrt4.modaps.eosdis.nasa.gov/api/v2/content/archives/FIRMS/'
token = 'DB8ECCD2-41E6-11EA-8E17-6EBC4405026C'

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
    'url' : 'c6/SouthEast_Asia/' ,
    'filename': 'MODIS_C6_SouthEast_Asia_MCD14DL_NRT_'
}
SRC_NOAA = {
    'name': 'noaa',
    'url': 'noaa-20-viirs-c2/SouthEast_Asia/' ,
    'filename': 'J1_VIIRS_C2_SouthEast_Asia_VJ114IMGTDL_NRT_' 
}

def make_url(src, date):
    filedate = date.strftime('%Y%j')
    filename = "{}.txt".format(filedate)

    return ''.join([api_url, src['url'], src['filename'], filename])


def reshape_csv(raw_csv, satellite='viirs'):
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
        line['latitude'] = float(line['latitude'])
        line['longitude'] = float(line['longitude'])
        if satellite == "viirs" :
            line['bright_ti4'] = float(line['bright_ti4'])
            line['bright_ti5'] = float(line['bright_ti5'])
        if satellite == "modis" :
            line['bright_t31'] = float(line['bright_t31'])
        line['frp'] = float(line['frp'])

        # change acq_{date,time} to unix epoch MICROseconds
        acq_datetime = datetime.datetime.fromisoformat(
            "{acq_date} {acq_time}".format(
                acq_date = line['acq_date'],
                acq_time = line['acq_time']
            )
        )
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

        # reshape to tags
        # unsure about scan, track, version inclusion into reshaped data
        #daynight = None
        #morning = datetime.datetime(1970, 1, 1, 6, 0, 0)
        #evening = datetime.datetime(1970, 1, 1, 18, 0, 0)

        #if 'daynight' in line:
        #    daynignt = line['daynignt']
        #else:
        #    if morning.time() <= acq_datetime.time() <= evening.time():
        #        daynight = 'D'
        #    else:
        #        daynight = 'N'

        ## reshape to tags
        #hotspot_tags = {
        #    'daynight': daynight,
        #    'satellite': line['satellite'],
        #    'confidence': line['confidence']
        #}

        ## reshape to fields
        #hotspot_fields = {
        #    'acq_epoch_ms': int(acq_epoch + acq_dupe),
        #    'latitide': line['latitude'],
        #    'longitude': line['longitude'],
        #    'bright_ti4': line['bright_ti4'],
        #    'bright_ti5': line['bright_ti5'],
        #    'frp': line['frp'],
        #}
        
        line['acq_time'] = int(acq_epoch + acq_dupe)
        acq_epoch_last = acq_epoch

        # test formatting them into a line protocol format
        #fields_out = ['='.join([str(k), str(v)]) 
        #            for k, v in hotspot_fields.items() 
        #            if k != 'acq_epoch_ms' ]

        #tags_out = ['='.join([str(k), str(v)]) 
        #            for k, v in hotspot_tags.items() ]

        #line_out_str = "hotspot,{tags} {fields} {time}".format(
        #    tags = ','.join(tags_out),
        #    fields=','.join(fields_out),
        #    time='{}'.format(hotspot_fields['acq_epoch_ms'])
        #)

        #print(line_out_str, flush=True)
        # merge tags and fields into one entity
        #hotspot_point = hotspot_tags.copy()
        #hotspot_point.update(hotspot_tags)

        # add to known hotspots
        hotspots.append(line)

    # return hotspots
    return hotspots

def request_nrt(date=None, src=None):
    """Fetch NRT Data from NASA (SEA Region) by date

    Args:
        date (datetime.date): 
            target date for data fetching
            can go back at most 2 months from today.
        src (one of SRC_{VIIRS,SUOMI,NOAA,MODIS}):
            target satellite for request
            defaults to VIIRS
    """
    if date is None:
        date = datetime.datetime.today()
    if src is None:
        src = SRC_VIIRS

    filedate = date.strftime('%Y%j')

    url = make_url(src, date)
    r = requests.get(url , headers={'Authorization':'Bearer '+ token })
    return r

def request_viirs_nrt(date=None):
    return request_nrt(date, SRC_VIIRS)

def request_modis_nrt(date=None):
    return request_nrt(date, SRC_MODIS)

def request_suomi_nrt(date=None):
    return request_nrt(date, SRC_SUOMI)

def request_noaa_nrt(date=None):
    return request_nrt(date, SRC_NOAA)

def get_nrt_data(date=None, src=SRC_VIIRS):
    req = request_nrt(date, src)

    req.raise_for_status()
    hotspots = {}
    hotspots = reshape_csv(req.text, src['name'])

    return hotspots

