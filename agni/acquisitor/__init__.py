import time
import queue
import datetime

import pandas as pd
import ciso8601

from influxdb import InfluxDBClient

from .. import models
from ..acquisitor import fetch_nrt, filtering
from ..util import nrtconv, timefmt

import logging
logger = logging.getLogger(__name__)

class Server:
    MAX_GAP = datetime.timedelta(days=60)

    def __init__(self, settings):
        self.settings = settings
        self.running = False
        self.influxdb = InfluxDBClient(
            #host=self.settings.get("INFLUXDB_HOST", 'localhost'),
            host='localhost',
            port=self.settings.get("INFLUXDB_PORT", '8086'),
            username=self.settings.get("INFLUXDB_USER", "root"),
            password=self.settings.get("INFLUXDB_PASSWORD", "root"),
            database=self.settings.get("INFLUXDB_DATABASE", None)
        )

        logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
        # models.init_mongoengine(
        #         settings)

    def fetch(self):
        influxdb = self.influxdb
        now = datetime.datetime.now()

        ql_str = """
            select * from {measurement}
            order by time desc
            limit 1 ;
        """.format(measurement="hotspots")
        result = influxdb.query(ql_str)
        result = list(result.get_points())


        try:
            latest_time = ciso8601.parse_datetime_as_naive(result[0]['time'])
            logger.debug("latest time: {}".format(latest_time.isoformat()))
            gap = now - latest_time
            fetch_start = now - min(self.MAX_GAP, gap)
        except IndexError as ie:
            fetch_start = now - self.MAX_GAP


        date_range = pd.date_range(fetch_start, now, freq='D')
        date_range = date_range.to_pydatetime().tolist()

        new_data = []
        for date in date_range:
            logger.info('Fetching data for {}'.format(date.isoformat()))

            data = fetch_nrt.get_nrt_data(date=date)
#            all_data += data
            th_data = filtering.filter_bbox(data, filtering.TH_BBOX_EXACT)

            # time column to time index
            data_df = pd.DataFrame(th_data)
            data_time = data_df['acq_time'].apply(timefmt.parse_timestamp_us)
            data_df['time'] = pd.DatetimeIndex(data_time)
            #data_df.set_index('time')

            # concat to pending list
            new_data.append(data_df)

        # all pending data
        all_data = pd.concat(new_data)
        logger.debug('New data size: {}'.format(len(all_data)))
        pending_data = all_data[all_data['time'] > fetch_start]
        logger.debug('Pending data size: {}'.format(len(pending_data)))
        pending = (
            nrtconv.to_influx_json(
                point=p,
                measure='hotspots', timekey='acq_time',
                skip=['acq_date', 'time']
            )
            for _, p in pending_data.iterrows()
        )

        influxdb.write_points(
            pending,
            time_precision='u',
            database='hotspots',
            batch_size=5000,
            protocol='json'
        )
        logger.info('Written {} new entries.'.format(len(pending_data)))


    def run(self):
        self.running = True
        i = 0
        while(self.running):
            logger.debug('Start acquisitor {}'.format(i))
            self.fetch()
            logger.debug('Fetch is done. sleep for 10m')
            time.sleep(600)
            i += 1


def create_server(settings):
    return Server(settings)
