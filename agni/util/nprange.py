import numpy as np

# from https://stackoverflow.com/a/57321916
def closed_range(start, stop, _step=1):
    delta = stop - start
    _step = delta // _step + 1

    if np.isclose(_step, np.round(_step)):
        _step = int(np.round(_step))

    return np.linspace(start, stop, _step)
