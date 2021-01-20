import datetime
import ciso8601

EPOCH_START = datetime.datetime(1970,1,1)
def parse_timestamp_us(ts):
    us = datetime.timedelta(microseconds=ts)
    return EPOCH_START + us

