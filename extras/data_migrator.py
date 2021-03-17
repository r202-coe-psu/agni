import os
from os import listdir
from os.path import isfile, join

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
        print("writing {} entries from {} ...".format(len(df), filename))
        db.write(df, measure='hotspots', precision=None, batch_size=10000)
        print("{} import done".format(filename))
        