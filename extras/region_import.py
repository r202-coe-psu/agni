import os

import geojson
import mongoengine as me

from agni.models import region

GJFILE = 'agni/web/regions/kuankreng.geojson'
DBNAME = 'agnidb'

me.connect(DBNAME)

# assumes FeatureCollection -> Features[0] -> MultiPolygon
with open(GJFILE, 'r') as f:
    name = os.path.basename(f.name)
    bname = os.path.splitext(name)[0]

    gj = geojson.load(f)
    gjf = gj.features[0]

    gjr = region.Region()
    gjr.populate_feature(gjf)
    gjr.name = bname
    gjr.human_name = gjf.properties['name']

    rlist = region.Region.objects(name=bname)
    if len(rlist) > 0:
        for r in rlist:
            r.delete()

    gjr.save()
