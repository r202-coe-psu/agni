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
    # if files:
    #     files['imageFile'].close()
    return r.status_code

def send(message):
    import os
    import sys
    #import argparse

    try:
        token = "uqDJpms2istxrdDUF5Eim858ZFIoW5SitexwV5zc2Sq"
    except KeyError:
        sys.exit('LINE_TOKEN is not defined!')

    # parser = argparse.ArgumentParser(
    #     description='Send a LINE Notify message, possibly with an image.')
    # # parser.add_argument('--img_file', help='the image file to be sent')
    # parser.add_argument(message)
    # args = parser.parse_args()
    status_code = send_message(token, message)
    print('status_code = {}'.format(status_code))
