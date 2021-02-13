# from . import users
# from . import oauth2

# from .users import User
# from .oauth2 import OAuth2Token

__all__ = [
           # oauth2,
           ]


from flask_mongoengine import MongoEngine

db = MongoEngine()
influxdb = None

def init_db(app):
    db.init_app(app)
    global influxdb
    if influxdb is None:
        influxdb = create_influxdb(app.config)

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

def create_influxdb(settings):
    from influxdb import InfluxDBClient
    host = settings.get('INFLUXDB_HOST', 'localhost')
    port = settings.get('INFLUXDB_PORT', '8086')
    username = settings.get('INFLUXDB_USER', 'root')
    password = settings.get('INFLUXDB_PASSWORD', 'root')
    database = settings.get('INFLUXDB_DATABASE', None)

    influxdb = InfluxDBClient(host=host,
                              port=port,
                              username=username,
                              password=password,
                              database=database)
    return influxdb
