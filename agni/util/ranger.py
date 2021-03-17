import numpy as np
import pandas as pd

# from https://stackoverflow.com/a/57321916
def closed_range(start, stop, _step=1):
    delta = stop - start
    _step = delta // _step + 1

    if np.isclose(_step, np.round(_step)):
        _step = int(np.round(_step))

    return np.linspace(start, stop, _step)

# from https://stackoverflow.com/a/6822761
from collections import deque

def window(seq, n=2):
    it = iter(seq)
    win = deque((next(it, None) for _ in range(n)), maxlen=n)
    yield list(win)
    append = win.append
    for e in it:
        append(e)
        yield win

def date_range(start, end, freq='D', normalize=False):
    date_range = pd.date_range(start, end, freq=freq, normalize=normalize)
    date_range = date_range.to_pydatetime().tolist()
    return date_range