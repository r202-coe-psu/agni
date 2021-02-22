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
    bname = os.path.splitext(name)

    gj = geojson.load(f)
    gjf = gj.features[0]
    gjr = region.Region(name=bname)
    gjr.populate_feature(gjf)

    rlist = region.Region.objects(name=bname)
    if len(rlist) > 0:
        r = rlist[0]
        r.delete()

    gjr.save()
