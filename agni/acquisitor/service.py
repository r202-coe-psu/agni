import time
import datetime
import threading
import queue

import pytz
import ciso8601
import requests

import pandas as pd
import mongoengine as me

from ..models import HotspotDatabase
from ..acquisitor import fetch_nrt, filtering
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

    def __init__(self, database: HotspotDatabase):
        self.database = database
    
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
            logger.debug('Latest time: None!')
            latest = self.oldest_data_date()

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

class DatabaseDaemon(threading.Thread):
    def __init__(self, settings, in_queue: queue.Queue):
        super().__init__()

        self.database = HotspotDatabase(settings)
        self.measure = 'hotspots'
        self.in_queue = in_queue
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            data = self.in_queue.get()
            self.database.write(data, measure=self.measure)
            logger.info("Written data of length {}".format(len(data)))

    def stop(self):
        self.running = False

class NotifierDaemon(threading.Thread):
    def __init__(self, settings, in_queue):
        super().__init__()

        self.running = False
        self.in_queue = in_queue

    def run(self):
        self.running = True
        while self.running:
            data = self.in_queue.get()
            logger.debug('Got new data of length {}.'.format(len(data)))

    def stop(self):
        self.running = False
