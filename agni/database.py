import logging
import time

import pandas as pd

from influxdb import InfluxDBClient
from .util import nrtconv

logger = logging.getLogger(__name__)

def create_influxdb(settings=None):
    if settings is None:
        settings = {}

    host = settings.get('INFLUXDB_HOST', 'localhost')
    port = settings.get('INFLUXDB_PORT', '8086')
    username = settings.get('INFLUXDB_USER', '')
    password = settings.get('INFLUXDB_PASSWORD', '')
    database = settings.get('INFLUXDB_DATABASE', None)

    influxdb = InfluxDBClient(host=host,
                              port=port,
                              username=username,
                              password=password,
                              database=database)
    return influxdb

class HotspotDatabase:
    def __init__(self, settings=None):
        self.version = None
        self.influxdb = None
        self.init_db(settings)

    def init_db(self, settings):
        self.influxdb = create_influxdb(settings)
        return self
    
    def write(
            self, data, measure,
            precision=None, batch_size=5000
    ):
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
        while self.version is not None:
            try:
                self.version = self.influxdb.ping()
                logger.debug("Server Version {}".format(self.version))
                return self.version
            except Exception:
                time.sleep(delay)
    
    @property
    def connection(self):
        return self.influxdb