import threading
import logging

from queue import Queue

from . import line
from ..models import Region, UserRegionNotify
from ..acquisitor import filtering

logger = logging.getLogger(__name__)

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
        token = user.access_token
        logger.debug(
            "Found new {} points in area '{}', notifying {}...".format(
                len(data),
                region.human_name,
                user.name
            ))
        pass

    def stop(self):
        self.running = False