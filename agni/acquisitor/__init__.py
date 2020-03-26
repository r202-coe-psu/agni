import time
import queue

from .. import models

import logging
logger = logging.getLogger(__name__)

class Server:
    def __init__(self, settings):
        self.settings = settings
        self.running = False

        logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
        # models.init_mongoengine(
        #         settings)

    def run(self):
        self.running = True
        while(self.running):
            logger.debug('start acquisitor')
            time.sleep(1)


def create_server(settings):
    return Server(settings)
