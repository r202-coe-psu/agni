import requests
from authlib.integrations.requests_client import OAuth2Auth

NOTIFY_URL = 'https://notify-api.line.me/api/notify'

def send(message, token, **kwargs):
    req = send_message(message=message, token=token, **kwargs)
    return req.status_code

def send_message(message, token, **kwargs):
    auth = OAuth2Auth(token)
    payload = {
        'message': message,
        **kwargs
    }
    req = requests.post(NOTIFY_URL, auth=auth, params=payload)
    req.raise_for_status()
    return req