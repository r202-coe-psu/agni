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
        self.geometry = feature.geometry
        self.properties = {
            k: v
            for k, v in feature.properties.items()
        }
        self.name = self.properties.get('name', self.name)
        self.human_name = self.properties.get('human_name', self.human_name)

    def to_dict(self):
        props = {k: v for k, v in self.properties.items()}
        props = dict(props, name=self.name, human_name=self.human_name)
        return {
            'id': str(self.id),
            'type': self.type,
            'geometry': self.geometry,
            'properties': props
        }

    def to_geojson(self):
        return geojson.Feature(**self.to_dict())
    
    @classmethod
    def region_choices(cls, swap=False):
        reglist = cls.objects.only('name', 'human_name')
        if swap:
            return list((r.human_name, r.name) for r in reglist)
        return list((r.name, r.human_name) for r in reglist)


class UserRegionNotify(me.Document):
    name = me.StringField(required=True)
    notification = me.BooleanField(default=True)
    regions = me.ListField(me.ReferenceField(Region))
    
    access_token = me.StringField()
    token_type = me.StringField(default="bearer")

    meta = {
        'collection': 'user_region_notify'
    }

    def to_json(self):
        return {
            "user_id": self.user_id,
            "notification": self.notification,
            "regions": [
                r.human_name for r in self.regions
            ],
            "token": self.token
        }
    
    @property
    def token(self):
        return dict(
            access_token=self.access_token,
            token_type=self.token_type
        )
