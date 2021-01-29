from agni.util import timefmt
import time
import queue
import datetime

from contextlib import contextmanager

import pandas as pd
import ciso8601
import pytz

from influxdb import InfluxDBClient

from . import service

#from .. import models
#from ..models import influxdb

import logging
logger = logging.getLogger(__name__)

class Server:
    SLEEP_SHORT = datetime.timedelta(seconds=10)
    SLEEP_LONG = datetime.timedelta(minutes=20)

    def __init__(self, settings):
        self.settings = settings
        self.running = False

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
            datefmt='%m-%d %H:%M'
        )
        # models.init_mongoengine(
        #         settings)
        self.fetch_db = service.FetcherDatabase(settings)
        self.fetcher = service.Fetcher(self.fetch_db)
    

    def sleep(self, duration: datetime.timedelta):
        next_wake = (datetime.datetime.now() + duration).isoformat()
        logger.debug(
            'Sleeping, next wake in {dur} (at {at})'.format(
                dur=timefmt.format_delta(duration),
                at=next_wake
            ), 
        )
        time.sleep(duration.total_seconds())

    def run(self):
        self.fetch_db.wait_server()
        self.running = True
        while(self.running):
            try:
                self.fetcher.update_data()
                logger.info('Fetch succeded')
                self.sleep(self.SLEEP_LONG)
            except Exception as e:
                logger.exception(e)
                logger.info('Fetch encounter an error, retrying ...')
                self.sleep(self.SLEEP_SHORT)
                
            

def create_server(settings):
    return Server(settings)
