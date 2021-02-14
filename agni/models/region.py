import mongoengine as me
import geojson

class Region(me.Document):
    name = me.StringField(required=True, unique=True)

    geometry = me.MultiPolygonField(required=True)
    type = me.StringField(required=True)
    properties = me.DictField()

    meta = {
        'collection': 'region'
    }

    def populate_feature(self, feature):
        self.type = feature.type
        self.properties = feature.properties
        self.geometry = feature.geometry
