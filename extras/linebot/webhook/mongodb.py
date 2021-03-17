import mongoengine as me
dbname = "line_db"
DB_URI = "mongodb+srv://jkpctn:5986@cluster0.o9dmh.mongodb.net/myFirstDatabase?retryWrites=true&w=majority&ssl_cert_reqs=CERT_NONE"
password = ""

me.connect(host=DB_URI)

class User(me.Document):
    user_id = me.StringField(required=True,unique = True)
    notification = me.BooleanField(default = True)
    region = me.MultiPointField()
    def to_json(self):
        return {
            "user_id":self.user_id,
            "notification":self.notification,
            "region":self.region
        }

    def get_user_id(self):
        return self.user_id

def add_user(new_id):
    users = get_all_user()
    if new_id in users:     #duplicated
        enable_user_notification(new_id)
    else:                   #not duplicated
        user = User(user_id=new_id)
        user.save()
    return 1                #ใช้แทน await

def update_user(target_id,target_notification,target_region):
    user = User.objects(user_id=target_id).first()
    user.update(notification=target_notification,region=target_region)

def get_all_user():
    users = []
    for user in User.objects():
        users.append(user.get_user_id())
    print(users)
    return users

def disable_user_notification(target_id):
    user = User.objects(user_id=target_id).first()
    user.update(notification=False)

def enable_user_notification(target_id):
    user = User.objects(user_id=target_id).first()
    user.update(notification=True)

def delete_user(target_id):
    user = User.objects(user_id=target_id).first()
    user.delete()

