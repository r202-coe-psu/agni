# from . import users
# from . import oauth2

# from .users import User
from .oauth2 import OAuth2Token
from .region import Region, UserRegionNotify

__all__ = [
           # oauth2,
           ]


from flask_mongoengine import MongoEngine
from ..database import HotspotDatabase, create_influxdb

db = MongoEngine()
influxdb = HotspotDatabase()

def init_db(app):
    db.init_app(app)
    influxdb.init_db(app.config)

def init_mongoengine(settings):
    import mongoengine as me
    dbname = settings.get('MONGODB_DB')
    host = settings.get('MONGODB_HOST', 'localhost')
    port = int(settings.get('MONGODB_PORT', '27017'))
    username = settings.get('MONGODB_USERNAME', '')
    password = settings.get('MONGODB_PASSWORD', '')

    me.connect(db=dbname,
               host=host,
               port=port,
               username=username,
               password=password)