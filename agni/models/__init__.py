# from . import users
# from . import oauth2

# from .users import User
# from .oauth2 import OAuth2Token

__all__ = [
           # oauth2,
           ]


from flask_mongoengine import MongoEngine
from flask_influxdb import InfluxDB

db = MongoEngine()
influxdb = InfluxDB()

def init_db(app):
    db.init_app(app)
    influxdb.init_app(app=app)


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

