import time
import datetime

import pytz
import ciso8601

import pandas as pd
from influxdb import InfluxDBClient
import requests

from ..acquisitor import fetch_nrt, filtering
from ..util import nrtconv, timefmt, ranger
from ..models import create_influxdb

import logging
logger = logging.getLogger(__name__)

class FetcherDatabase:
    def __init__(self, settings):
        self.version = None
        self.influxdb = create_influxdb(settings)
    
    def write(
            self, data, measure, database=None,
            precision=None, batch_size=5000
    ):
        #database = database or self.database
        pending = (
            nrtconv.to_influx_json(
                point=p, measure=measure, timekey='time',
                auto_tags=True, skip=['acq_date', 'acq_time']
            )
            for _, p in data.iterrows()
        )

        self.influxdb.write_points(
            pending,
            time_precision=precision,
            #database=database,
            batch_size=batch_size,
            protocol='json'
        )

    def read(self, query, return_df=False):
        result = self.influxdb.query(query)
        result_list = list(result.get_points())
        if return_df:
            result_df = pd.DataFrame(result_list)
            return result_df
        return result_list
    
    def wait_server(self, delay=10):
        while True:
            try:
                self.version = self.influxdb.ping()
                logger.debug("Server Version {}".format(self.version))
                return
            except Exception:
                time.sleep(delay)


class Fetcher:
    LOCAL_TZ = pytz.timezone('Asia/Bangkok')
    MAX_DELTA = datetime.timedelta(days=60)

    def __init__(self, influxdb):
        self.influxdb = influxdb
    
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
        data = self.influxdb.read(ql_str, return_df=False)
        latest_time = ciso8601.parse_datetime_as_naive(data[0]['time'])
        return latest_time

    def update_data(self):
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
            self.influxdb.write(new_data, measure='hotspots', database='hotspots')
