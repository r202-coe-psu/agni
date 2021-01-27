import datetime

import os
from os import listdir
from os.path import isfile, join

import pathlib

from agni.acquisitor import fetch_nrt, service 

FILEPATH = '/home/tk3/viirs-data'

onlyfiles = [f for f in listdir(FILEPATH) if isfile(join(FILEPATH, f))]

csv_file = [f for f in onlyfiles if '.csv' in f]

settings = {
    'INFLUXDB_PORT': 8087
}

db = service.FetcherDatabase(settings)
db.wait_server()

print(csv_file)

for filename in csv_file:
    with open(os.path.join(FILEPATH, filename), 'r') as f:
        text = f.read()
        df = fetch_nrt.process_csv_pandas(text)
        print("writing {} entries from {} ...".format(len(df), filename))
        db.write(df, measure='hotspots', database='hotspots', precision=None)
        print("{} import done".format(filename))
        