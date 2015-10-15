# author: sivanov
# date: 15 Oct 2015
from __future__ import division

import time
import traceback
import os
import botan

class BotanTracker(object):
    def __init__(self, botan_db, botan_token, **kwargs):
        self.botan_db = botan_db
        self.botan_token = botan_token

    def send_to_botan(self, data):
        name = data['name']
        message = {}
        if 'title' in data:
            uid = data['chat_id']
        else:
            uid = data['user_id']
            print 'Sending data to botan', data
        botan.track(self.botan_token, uid, message, name)

    def listen(self, pause=1):
        self.is_alive = True
        print 'Botan tracker starts listening...'
        while self.is_alive:
            try:
                for data in self.botan_db.find():
                    self.send_to_botan(data)
                    self.botan_db.remove(data)
                time.sleep(pause)
            except Exception, e:
                self.is_alive = False
                print("Botan tracker. Stop listening. Safely recovering from error.")
                print(e)
                try:
                    if os.path.exists('botan_log.txt') and os.path.getsize('botan_log.txt') > 10*1024*1024: # 10mb
                        os.remove('log.txt')
                except:
                    pass
                with open('botan_log.txt', 'a+') as f:
                    f.write('''Exception in get_update at {0}.\n'''.format(time.strftime("%d-%m-%Y %H:%M:%S")))
                    f.write(traceback.format_exc() + '\n')

if __name__ == "__main__":
    console = []