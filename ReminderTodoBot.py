# author: sivanov
# date: 02 Oct 2015
from __future__ import division
import time
import traceback

class Reminder(object):
    def __init__(self, reminder_db, **kwargs):
        self.reminder_db = reminder_db

    def set_messaging(self, messaging):
        self.send_message = messaging

    def listen(self, pause=1):
        self.is_alive = True
        print 'Reminder starts listening...'
        while self.is_alive:
            try:
                for data in self.reminder_db.find({"remind_at": {"$lt": time.time()}}):
                    self.send_message(data)
                time.sleep(pause)
            except Exception, e:
                # self.is_alive = False
                print("Reminder. Stop listening. Safely recovering from error.")
                print(e)
                with open('reminder_log.txt', 'a+') as f:
                    f.write('''Exception in get_update at {0}.\n'''.format(time.strftime("%d-%m-%Y %H:%M:%S")))
                    f.write(traceback.format_exc() + '\n')
