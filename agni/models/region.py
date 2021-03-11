import mongoengine as me
import geojson

class Region(me.Document):
    name = me.StringField(required=True, unique=True)
    human_name = me.StringField(required=True)

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

class UserRegionNotifications(me.Document):
    user_id = me.StringField(required=True, unique=True)
    notification = me.BooleanField(default=True)
    regions = me.ListField(me.ReferenceField(Region))

    def to_json(self):
        return {
            "user_id": self.user_id,
            "notification": self.notification,
            "regions": [
                r.human_name for r in self.regions
            ]
        }
