import datetime
import ciso8601

EPOCH_START = datetime.datetime(1970,1,1)
_DELTA_ZERO = datetime.timedelta(0)

def parse_timestamp_us(ts: int):
    us = datetime.timedelta(microseconds=ts)
    return EPOCH_START + us

def format_delta(delta: datetime.timedelta):
    sign = ''
    if delta < _DELTA_ZERO:
        sign = '-'
        delta = -delta

    mm, ss = divmod(delta.seconds, 60)
    hh, mm = divmod(mm, 60)
    dd = delta.days
    tl = [sign]
    o = [
        (dd, 'd'),
        (hh, 'h'),
        (mm, 'm'),
        (ss, 's')
    ]

    for val, label in o:
        if abs(val) > 0:
            out = "{:d}{}".format(val, label)
            tl.append(out)

    return ''.join(tl)

