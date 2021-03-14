"""line_notify.py
  
For sending a LINE Notify message (with or without image)
  
Reference: https://engineering.linecorp.com/en/blog/using-line-notify-to-send-messages-to-line-from-the-command-line/
"""

import requests

def send_message(token, msg, img=None):
    URL = 'https://notify-api.line.me/api/notify'
    """Send a LINE Notify message (with or without an image)."""
    headers = {'Authorization': 'Bearer ' + token}
    payload = {'message': msg}
    files = {'imageFile': open(img, 'rb')} if img else None
    r = requests.post(URL, headers=headers, params=payload, files=files)
    return r.status_code

def send(message, token=None):
    if token is None:
        token = "uqDJpms2istxrdDUF5Eim858ZFIoW5SitexwV5zc2Sq"

    status_code = send_message(token, message)
    print('status_code = {}'.format(status_code))
