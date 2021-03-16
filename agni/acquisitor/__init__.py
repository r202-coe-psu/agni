import time
import queue
import datetime

from .service import Fetcher, sleep_log

from .. import models
from ..notify import NotifierDaemon
from ..util import timefmt

import logging
logger = logging.getLogger(__name__)

DEMO_URL = "https://t.coe.psu.ac.th/~6010110106/agni-demo/hotspot-inject.txt"

class Server:
    SLEEP_SHORT = datetime.timedelta(seconds=10)
    SLEEP_LONG = datetime.timedelta(minutes=20)

    def __init__(self, settings):
        self.settings = settings
        self.running = False
        self.demo = False

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
            datefmt='%m-%d %H:%M'
        )

        self.database = models.HotspotDatabase(settings)
        models.init_mongoengine(settings)

        self.fetcher = Fetcher(settings, self.database)

        demo_mode = settings.get('FETCHER_DEMO_MODE')
        if demo_mode is not None and demo_mode == 'yes':
            logger.debug(r'//////// DEMO MODE ENABLED ////////')
            self.demo = True

        self.notify_queue = queue.Queue()
        self.out_queues = [self.notify_queue]

        self.notifyd = NotifierDaemon(settings, in_queue=self.notify_queue)
        self.notifyd.start()

    def demo_injector(self, base_data=None):
        logger.debug(r'//////// DEMO INJECTOR ACTIVE ////////')
        import requests
        from pandas import concat, DataFrame
        from .fetch_nrt import process_csv_pandas

        req = requests.get(DEMO_URL)
        if req.ok:
            demo_data = process_csv_pandas(req.text)
            hotspots = concat([base_data, demo_data], join='inner')
            return hotspots
        return DataFrame()
        
    def run(self):
        self.database.wait_server()
        self.running = True
        while self.running:
            try:
                new_data = self.fetcher.update_data(write=True)
                if self.demo:
                    new_data = self.demo_injector(new_data)
                if len(new_data) > 0:
                    for q in self.out_queues:
                        q.put(new_data)
                sleep_log(self.SLEEP_LONG)
            except Exception as e:
                logger.exception(e)
                logger.error('Fetch encounter an error, retrying ...')
                sleep_log(self.SLEEP_SHORT)

    def stop(self):
        self.running = False


def create_server(settings):
    return Server(settings)
