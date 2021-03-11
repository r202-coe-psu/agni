import datetime
#import csv
#import os
#import sys

import requests

API_URL = 'https://nrt4.modaps.eosdis.nasa.gov/api/v2/content/archives/FIRMS/'

TOKEN = 'DB8ECCD2-41E6-11EA-8E17-6EBC4405026C'

SRC_VIIRS = {
    'name': 'viirs',
    'url': 'viirs/SouthEast_Asia/',
    'filename': 'VIIRS_I_SouthEast_Asia_VNP14IMGTDL_NRT_'
}

def make_url(src, date):
    filedate = date.strftime('%Y%j')
    filename = "{}.txt".format(filedate)

    return ''.join([API_URL, src['url'], src['filename'], filename])

def request_nrt():
    date = datetime.datetime.today()
    src = SRC_VIIRS
    url = make_url(src, date)
    r = requests.get(url, headers={'Authorization': 'Bearer {}'.format(TOKEN)})
    return r