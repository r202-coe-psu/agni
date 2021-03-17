import os
from os import listdir
from os.path import isfile, join

import pandas as pd
from pandas.api.types import is_numeric_dtype, is_string_dtype

from agni.acquisitor import fetch_nrt
from agni.database import HotspotDatabase

FILEPATH = '/mnt/e/viirs-data'

onlyfiles = [f for f in listdir(FILEPATH) if isfile(join(FILEPATH, f))]
csv_file = [f for f in onlyfiles if '.csv' in f]

settings = {
    'INFLUXDB_PORT': 8087,
    'INFLUXDB_DATABASE': 'hotspots'
}
db = HotspotDatabase(settings)
db.wait_server()

print(csv_file)

for filename in csv_file:
    with open(os.path.join(FILEPATH, filename), 'r') as f:
        text = f.read()
        df = fetch_nrt.process_csv_pandas(text)
        confidence = df['confidence']
        if is_numeric_dtype(confidence):
            print('confidence is numerical, renaming keys..')
            df['confidence_percent'] = confidence
            del df['confidence']
            print(df.columns)
        elif is_string_dtype(confidence):
            print('confidence is categorical, mapping names...')
            df['confidence'] = confidence.map({
                'l': 'low',
                'n': 'nominal',
                'h': 'high'                
            })
            print(df['confidence'].unique())
        print("writing {} entries from {} ...".format(len(df), filename))
        db.write(df, measure='hotspots', precision=None, batch_size=5000)
        print("{} import done".format(filename))
        