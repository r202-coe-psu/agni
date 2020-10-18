class FireGridType:
    EMPTY, TREE, FIRE = 0, 1, 2

#
# probably process everything in UTM coords for distance simplicity
# 1 unit == 1m irl
#

def generate_firegrid(nrtpoints, sample_area, distance):
    """ generate fire grid from data points over a given area

    Args:
        nrtpoint (list[dict]): 
            NRT data points
        sample_area (tuple, tuple):
            a pair of points represent sampling boundary (topleft/downright?)
        distance (int):
            grid distance in meters, each cell is assumed to be a square

    Returns:
        firegrid (numpy.array?):
            bitmap-like grid representing burn states, categorized to 3 types
            of cannot burn, can burn, burning (EMPTY, TREE, FIRE)
    """
    pass

def burn_simple_iterate(firegrid):
    """ try to predict which grid will likely burn based on current
        fire grid burn map
    
    Args:
        firegrid:
            fire grid of current iteration

    Returns:
        firegrid:
            fire grid of the next iteration after applied the model
    """
    pass

def firegrid_dump(firegrid):
    """ generate datapoint from firegrid more suitable for storage """
    pass

def firegrid_load(firegrid_points):
    """ load firegrid datapoints and reconstruct firegrid. 
    flipside of firegrid_dump()
    """
    pass