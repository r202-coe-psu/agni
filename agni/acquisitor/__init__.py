import time
import queue
import datetime

from contextlib import contextmanager

import pandas as pd
import ciso8601
import pytz

from influxdb import InfluxDBClient

#from .. import models
#from ..models import influxdb
from ..acquisitor import fetch_nrt, filtering
from ..util import nrtconv, timefmt

import logging
logger = logging.getLogger(__name__)

class Server:
    LOCAL_TZ = pytz.timezone('Asia/Bangkok')
    MAX_DELTA = datetime.timedelta(days=60)

    def __init__(self, settings):
        self.settings = settings
        self.running = False

        self.influxdb = self.init_influxdb()
        self.OLDEST_DATA_DATE = self.current_time(utc=True) - self.MAX_DELTA

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
            datefmt='%m-%d %H:%M'
        )
        # models.init_mongoengine(
        #         settings)

    def init_influxdb(self):
        influxdb = InfluxDBClient(
            host=self.settings.get("INFLUXDB_HOST", 'localhost'),
            port=self.settings.get("INFLUXDB_PORT", '8086'),
            username=self.settings.get("INFLUXDB_USER", "root"),
            password=self.settings.get("INFLUXDB_PASSWORD", "root"),
            database=self.settings.get("INFLUXDB_DATABASE", None)
        )
        return influxdb

    def current_time(self, utc=False):
        now_local = datetime.datetime.now()
        now_utc = self.LOCAL_TZ.localize(now_local).utcnow()
        return now_utc if utc else now_local

    def process_time_index(self, data, timekey):
        data_df = pd.DataFrame(data)
        data_time = data_df[timekey].apply(timefmt.parse_timestamp_us)
        data_df['time'] = pd.DatetimeIndex(data_time)
        data_df.set_index('time')
        return data_df

    def filter_newer_data(self, data, min_time, timekey):
        all_data = self.process_time_index(data, timekey)
        newer = all_data[all_data['time'] > min_time]
        return newer

    def fetch_live_data(self, date, region=None):
        result = fetch_nrt.get_nrt_data(date=date)
        if region is not None:
            result = filtering.filter_bbox(result, region)
        return result

    def write_influx(
            self, data, database='hotspots',
            precision='u', batch_size=5000
    ):
        pending = (
            nrtconv.to_influx_json(
                point=p,
                measure='hotspots', timekey='acq_time',
                skip=['acq_date', 'time']
            )
            for _, p in data.iterrows()
        )

        self.influxdb.write_points(
            pending,
            time_precision=precision,
            database=database,
            batch_size=batch_size,
            protocol='json'
        )

    def read_influx(self, query):
        result = self.influxdb.query(query)
        result = list(result.get_points())
        return result

    def influx_latest_time(self):
        ql_str = """
            select * from {measurement}
            order by time desc
            limit 1 ;
        """.format(measurement="hotspots")
        data = self.read_influx(ql_str)
        latest_time = ciso8601.parse_datetime_as_naive(data[0]['time'])
        return latest_time

    def date_range(self, start, end, freq='D'):
        date_range = pd.date_range(start, end, freq=freq, normalize=True)
        date_range = date_range.to_pydatetime().tolist()
        return date_range

    def run_fetch(self):
        try:
            latest = self.influx_latest_time()
            logger.debug('Latest time: {}'.format(latest.isoformat()))
        except Exception as e:
            logger.debug('Latest time: None!')
            latest = self.OLDEST_DATA_DATE

        fetch_start = max(self.OLDEST_DATA_DATE, latest)
        fetch_end = self.current_time(utc=True)
        logger.debug('Start: {}, End: {}'.format(fetch_start.isoformat(),
                                                 fetch_end.isoformat()))

        all_data = []
        for date in self.date_range(fetch_start, fetch_end, freq='D'):
            logger.debug('Fetching: {}'.format(date.isoformat()))
            data = self.fetch_live_data(date, region=filtering.TH_BBOX_EXACT)
            all_data += data

        new_data = self.filter_newer_data(all_data, min_time=fetch_start,
                                          timekey='acq_time')
        logger.debug('All data length: {}'.format(len(all_data)))
        logger.debug('New data length: {}'.format(len(new_data)))
        self.write_influx(new_data, database='hotspots')

    def run(self):
        while True:
            try:
                ver = self.influxdb.ping()
                break
            except Exception as e:
                logger.error('Cannot connect to DB, retrying after 10s ...')
                time.sleep(10)

        self.running = True
        while(self.running):
            try:
                self.run_fetch()
            except Exception as e:
                logger.error('Fetch failed, retrying after 10s ...')
                time.sleep(10)
                continue
            logger.info('Next fetch attempt in 10m, sleep ...')
            time.sleep(600)

def create_server(settings):
    return Server(settings)
