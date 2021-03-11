import time
import os
from apscheduler.schedulers.background import BackgroundScheduler

#set time zone
os.environ['TZ']="UTC"
import line
import request_nrt
import csv

def new_viirs_hotspots_data_check():

    time_now = time.strftime("%A, %d. %B %Y %I:%M:%S %p %Z")
    print(time_now)

    #request hotspots
    r = request_nrt.request_nrt()

    #check result
    if r.status_code == 404:
        output_str = 'status code: '+str(r.status_code)  + '\ntime: '+str(time_now)
        line.send('404 not found')

    else :
        #split in to lines
        result = [row for row in csv.reader(r.text.splitlines(), delimiter='\n')]

        #output string
        output_str = 'status code: '+str(r.status_code)  + '\ncount: ' + str(len(result)) + '\ntime: '+str(time_now)

        #sent to line
        line.send(output_str)

scheduler = BackgroundScheduler(daemon=True) 
scheduler.add_job(new_viirs_hotspots_data_check,'cron',hour='*',minute='00,30')
scheduler.start()
