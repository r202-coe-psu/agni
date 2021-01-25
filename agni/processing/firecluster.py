import json
import time

import numpy as np
import pandas as pd
import sklearn.cluster as cluster

from shapely.geometry import MultiPoint

# Constants
KMS_PER_RAD = 6371.0088

CLUSTER_ALGO = 'ball_tree'
CLUSTER_METRIC = 'haversine'
CLUSTER_RADIUS_KM = 0.375 * 1.5
CLUSTER_MIN_SAMPLES = 5

NOISE_LABEL = -1

COORDS_KEY = ['latitude', 'longitude']
CLUSTER_KEY = 'cluster'

def get_epsilon(dist_km):
    """ calculate DBSCAN eps value from given radius, in km """

    return dist_km / KMS_PER_RAD

def create_dbscan(
        algorithm=None, metric=None, radius_km=None, min_samples=None
    ):
    _algo = algorithm or CLUSTER_ALGO
    _metric = metric or CLUSTER_METRIC
    _step_km = radius_km or CLUSTER_RADIUS_KM
    _min_samples = min_samples or CLUSTER_MIN_SAMPLES

    db = cluster.DBSCAN(algorithm=_algo, metric=_metric)
    db.eps = get_epsilon(_step_km)
    db.min_samples = _min_samples

    return db

def process_labels(nrt_df, db):
    labels = db.labels_
    labels_series = pd.Series(labels)
    labels_series[db.labels_ == NOISE_LABEL] = np.nan
    nrt_df['cluster'] = labels_series

    # classifying cluster types
    dbccol = pd.Series(labels)
    dbccol[:] = 'edge'
    dbccol[db.core_sample_indices_] = 'core'
    dbccol[db.labels_ == NOISE_LABEL] = 'noise'
    nrt_df['dbscan'] = dbccol

    return nrt_df

def partial_record(df):
    # https://stackoverflow.com/a/47544280
    return df.T.apply(lambda x: x.dropna().to_dict()).tolist()

def full_record(df):
    return df.to_dict('records')

def cluster_fire(nrt_points, db=None, key=None, eps=None):
    """
    perform clustering using DBSCAN by default

    Args:
        nrt_points (list[dict]):
            input data points
        db (sklearn.cluster) (optional):
            custom clustering model compatible with sklearn.cluster module
        key (list[str]) (optional)
            custom key for extracting location info from data points
            defaults to ['latitude', 'longitude']

    Returns:
        data points with new field 'cluster' indicate cluster the points
        belong to, -1 is noise by DBSCAN algorithm
    """
    # prepare data
    nrt_df = pd.DataFrame(nrt_points)
    key = COORDS_KEY if key is None else key
    # early bail out if there's no data to be clustered
    if  len(nrt_df) == 0:
        return []

    coords = nrt_df[key].to_numpy()

    # do clustering using dbscan
    if db is None:
        db = create_dbscan()

    db.fit(np.radians(coords))

    nrt_df = process_labels(nrt_df, db)
    return partial_record(nrt_df)

def drop_noise(nrt_points):
    nrt_df = pd.DataFrame(nrt_points)
    return full_record(nrt_df[nrt_df['dbscan'] != 'noise'])

def get_centroid(cluster):
    """ get centroids from group of points """

    c = MultiPoint(cluster)
    centroid = (c.centroid.x, c.centroid.y)
    return tuple((*centroid, len(cluster))) # return: (x, y, count)

def find_cluster_centroids(
        clustered_data, coords_key=None, labels_key=None, noise_label=None
    ):
    """ 
    find cluster centroids from given clustered data
    the input data MUST be clustered beforehand
    """

    cluster_df = drop_noise(clustered_data)
    nrt_df = pd.DataFrame(cluster_df, copy=True)

    if labels_key is None: labels_key = CLUSTER_KEY
    if coords_key is None: coords_key = COORDS_KEY
    if noise_label is None: noise_label = -1

    if labels_key not in nrt_df.columns:
        raise KeyError("Invalid cluster key")

    cluster_labels = nrt_df[labels_key]
    coords = nrt_df[coords_key].to_numpy()

    available_clusters = list(set(cluster_labels))

    clusters = pd.Series([
        coords[cluster_labels == n] 
        for n in available_clusters
    ])

    centroids = clusters.map(get_centroid)
    c_lats, c_lons, c_count = zip(*centroids)
    rs = pd.DataFrame({ 
        'latitude': c_lats, 
        'longitude': c_lons, 
        'count': c_count
    })

    return full_record(rs)
