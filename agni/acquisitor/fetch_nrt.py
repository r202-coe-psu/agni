import requests
import datetime
import csv
import os
import sys

token = 'DB8ECCD2-41E6-11EA-8E17-6EBC4405026C'

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
        line['latitude'] = float(line['latitude'])
        line['longitude'] = float(line['longitude'])
        line['bright_ti4'] = float(line['bright_ti4'])
        line['bright_ti5'] = float(line['bright_ti5'])
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
        daynight = None
        morning = datetime.datetime(1970, 1, 1, 6, 0, 0)
        evening = datetime.datetime(1970, 1, 1, 18, 0, 0)

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

def request_nrt(date=None):
    """Fetch NRT Data from NASA (SEA Region) by date

    Args:
        date (datetime.date): 
            target date for data fetching
            can go back at most 2 months from today.
    """

    if date is None:
        date = datetime.datetime.today()

    filedate = date.strftime('%Y%j')

    file_name = 'VIIRS_I_SouthEast_Asia_VNP14IMGTDL_NRT_'+ filedate + '.txt'
    url = 'https://nrt4.modaps.eosdis.nasa.gov/api/v2/content/archives/FIRMS/viirs/SouthEast_Asia/' + file_name
    r = requests.get(url , headers={'Authorization':'Bearer '+ token })
    return r

