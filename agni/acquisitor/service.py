import time
import datetime
import threading

from queue import Queue

import pytz
import ciso8601
import requests
import geojson

import pandas as pd
import mongoengine as me

from ..models import HotspotDatabase
from ..models.region import UserRegionNotify, Region
from ..acquisitor import fetch_nrt, filtering, line
from ..util import timefmt, ranger

import logging
logger = logging.getLogger(__name__)

def sleep_log(duration: datetime.timedelta):
    next_wake = (datetime.datetime.now() + duration).isoformat()
    logger.debug(
        'Sleeping, next wake in {dur} (at {at})'.format(
            dur=timefmt.format_delta(duration),
            at=next_wake
        ), 
    )
    time.sleep(duration.total_seconds())

class Fetcher:
    LOCAL_TZ = pytz.timezone('Asia/Bangkok')
    MAX_DELTA = datetime.timedelta(days=60)

    def __init__(self, settings, database: HotspotDatabase):
        self.firms_token = settings.get('FIRMS_API_TOKEN')
        self.database = database

        fetch_nrt.set_token(self.firms_token)
    
    def oldest_data_date(self):
        oldest = self.current_time(utc=True) - self.MAX_DELTA
        return oldest.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def current_time(self, utc=False):
        now_local = datetime.datetime.now()
        now_utc = self.LOCAL_TZ.localize(now_local).utcnow()
        return now_utc if utc else now_local

    def process_data_time_us(self, data, timekey, index_timekey='time'):
        data_df = pd.DataFrame(data)
        data_time = data_df[timekey].apply(timefmt.parse_epoch_us)
        data_df[index_timekey] = pd.DatetimeIndex(data_time)
        #data_df.set_index(index_timekey)
        return data_df

    def filter_newer_data(self, data, min_time, timekey='time'):
        min_time = min_time.replace(microsecond=0)
        newer = data[data[timekey] > min_time]
        return newer

    def fetch_live_data(self, date, region=None, silent=False):
        result = fetch_nrt.get_nrt_data(date=date, silent_404=silent)
        if region is not None and len(result) > 0:
            result = filtering.filter_bbox(result, region)
        return result

    def influx_latest_time(self):
        ql_str = """\
            select * from {measurement}
            order by time desc
            limit 1 ;
        """.format(measurement="hotspots")
        data = self.database.read(ql_str, return_df=False)
        latest_time = ciso8601.parse_datetime_as_naive(data[0]['time'])
        return latest_time

    def update_data(self, write=True):
        try:
            latest = self.influx_latest_time()
            logger.debug('Latest time: {}'.format(latest.isoformat()))
        except IndexError as e:
            latest = self.oldest_data_date()
            logger.debug('Latest time: None!')

        fetch_start = max(self.oldest_data_date(), latest)
        fetch_end = self.current_time(utc=True)
        logger.debug(
            'Start: {}, End: {}'.format(
                fetch_start.isoformat(),
                fetch_end.isoformat()
            )
        )

        all_data = []
        fetch_dates = ranger.date_range(
            fetch_start, fetch_end, 
            freq='D', normalize=True
        )
        for date in fetch_dates:
            logger.debug('Fetching: {}'.format(date.isoformat()))
            try:
                data = self.fetch_live_data(
                    date, region=filtering.TH_BBOX_EXACT, silent=False
                )
                all_data += data
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    logger.warn("Server reported {} for file at {}".format(
                        e.response.status_code,
                        e.response.url
                    ))
                else:
                    raise e
                break

        if len(all_data) > 0:
            all_data_df = pd.DataFrame(all_data)
            new_data = self.filter_newer_data(all_data_df, min_time=fetch_start)
            logger.debug('All data length: {}'.format(len(all_data)))
            logger.debug('New data length: {}'.format(len(new_data)))
            if write:
                self.database.write(
                    new_data, 
                    measure='hotspots', 
                )
            return new_data
        return None

class NotifierDaemon(threading.Thread):
    def __init__(self, settings, in_queue: Queue):
        super().__init__()

        self.running = False
        self.daemon = True
        self.in_queue = in_queue

    def run(self):
        self.running = True
        while self.running:
            data = self.in_queue.get()
            line.send("พบเจอจุดความร้อนใหม่ในไทย {} จุด".format(len(data)))
            logger.debug('Got new data of length {}.'.format(len(data)))
            self.process_new_data(data)

    def process_new_data(self, data_df):
        data = data_df.to_dict('records')
        regions = Region.objects
        for region in regions:
            r = region.to_geojson()
            point_within = filtering.filter_shape(data, r)
            if len(point_within) > 0:
                subbed_users = UserRegionNotify.objects(
                    regions__name=region.name
                ).exclude('regions')
                for user in subbed_users:
                    if user.notification:
                        self.send_notification(user, region, point_within)

    def send_notification(self, user, region, data):
        token = user.token
        logger.debug(
            "Found new {} points in area '{}', notifying {}...".format(
                len(data),
                region.human_name,
                user.name
            ))
        pass

    def stop(self):
        self.running = False
