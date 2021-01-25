import datetime
import ciso8601

EPOCH_START = datetime.datetime(1970,1,1)
_DELTA_ZERO = datetime.timedelta(0)
_DELTA_US = datetime.timedelta(microseconds=1)

def parse_epoch_us(ts: int):
    us = datetime.timedelta(microseconds=ts)
    return EPOCH_START + us

def format_epoch_us(dt: datetime):
    # had to determine epoch time by dividing timedeltas
    # since strftime('%S') isn't guaranteed to be portable
    return (dt-EPOCH_START) / _DELTA_US

def format_delta(delta: datetime.timedelta):
    sign = ''
    if delta < _DELTA_ZERO:
        sign = '-'
        delta = -delta

    mm, ss = divmod(delta.seconds, 60)
    hh, mm = divmod(mm, 60)
    dd = delta.days
    text = [sign]
    fields = [
        (dd, 'd'),
        (hh, 'h'),
        (mm, 'm'),
        (ss, 's')
    ]

    for val, label in fields:
        if abs(val) > 0:
            out = "{:d}{}".format(val, label)
            text.append(out)

    return ''.join(text)

