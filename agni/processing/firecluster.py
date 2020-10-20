import json
import time

import numpy as np
import pandas as pd
import sklearn.cluster as cluster

from shapely.geometry import MultiPoint

# Constants
KMS_PER_RAD = 6371.0088
CLUSTER_DB = cluster.DBSCAN(eps=eps, min_samples=min_samples, 
                            algorithm='ball_tree', metric='haversine')
COORDS_KEY = ['latitude', 'longitude']
CLUSTER_KEY = 'cluster'

def get_epsilon(dist_km):
    """ calculate DBSCAN eps value from given radius, in km """

    return dist_km / KMS_PER_RAD

def cluster_fire(nrt_points, db=None, position_key=None):
    """ perform clustering using DBSCAN by default

    Args:
        nrt_points (list[dict]):
            input data points
        db (sklearn.cluster) (optional):
            custom clustering model compatible with sklearn.cluster module
        position_key (list[str]) (optional)
            custom key for extracting location info from data points
            defaults to ['latitude', 'longitude']

    Returns:
        data points with new field 'cluster' indicate cluster the points
        belong to, -1 is noise by DBSCAN algorithm
    """
    # prepare data
    nrt_df = pd.DataFrame(nrt_points)
    key = COORDS_KEY if key is None else key
    coords = nrt_df[key].to_numpy()

    # do clustering using dbscan
    db = CLUSTER_DB if db is None else db
    db.fit(np.radians(coords))

    labels = db.labels_
    labels_series = pd.Series(labels)
    nrt_df[position_key] = labels_series

    return nrt_df.to_dict()

def get_centroid(cluster):
    """ get centroids from group of points """

    c = MultiPoint(cluster)
    centroid = (c.centroid.x, c.centroid.y)
    return tuple((*centroid, len(cluster))) # return: (x, y, count)

def find_cluster_centroids(
        clustered_data, coords_key=None, labels_key=None, noise_label=None
    ):
    """ find cluster centroids from given clustered data
        the input data MUST be clustered beforehand
    """
    nrt_df = pd.DataFrame(clustered_data)

    labels_key = CLUSTER_KEY if labels_key is None else labels_key
    coords_key = COORDS_KEY if coords is None else coords_key
    noise_label = -1 if noise_label is None else noise_label

    if labels_key not in nrt_df.columns:
        raise KeyError("Invalid cluster key")
    
    cluster_labels = nrt_df[labels_key]
    coords = nrt_df[coords_key].to_numpy()

    noise_exist = (1 if noise_label in cluster_labels else 0)
    num_clusters = len(set(cluster_labels)) - noise_exist
    
    clusters = pd.Series([
        coords[cluster_labels == n] 
        for n in range(num_clusters)
    ])

    centroids = clusters.map(get_centroid)
    c_lats, c_lons, c_count = zip(*centroids)
    rs = pd.DataFrame({ 
        'latitude': c_lats, 
        'longitude': c_lons, 
        'count': c_count
    })

    return rs.to_dict()