# author: sivanov
# date: 05 Oct 2015
from __future__ import division

import time
import traceback
from emoji_chars import *
import os

class Subscription(object):
    def __init__(self, subscription_db, users_db, todobot, **kwargs):
        self.subscription_db = subscription_db
        self.users_db = users_db
        self.todobot = todobot

        me = 80639335
        testdevgroup = -28297621
        yura_pekov = 1040729
        yura_oparin = 93518804
        founding_group = -27571522
        self.cools = [me, testdevgroup]
        # self.cools = [me]

    def extend_expire(self, data):
        for i, user in enumerate(self.users_db.find({"subscription_code": data["code"]})):
            self.users_db.update({"user_id": user["user_id"]},
                {"$set": {'expiry_date': time.time() + 86400*30}})
            self.todobot.send_message(user["user_id"], u"You received Premium subscription for 30 days! {}".format(emoji_thumb))
            # send to founders that there was subscription
            for cool in self.cools:
                print cool, u"User {} ({}) paid for subscription".format(user['first_name'], user['user_id'])
                try:
                    self.todobot.send_message(cool, u"User {} ({}) paid for subscription".format(user['first_name'], user['user_id']))
                except:
                    print u'Failed to send message to {0}'.format(cool)
            if i > 0:
                try:
                    self.todobot.send_message(self.cools[0],
                                              u"More than one user has acquired subscription by the same code. {} ({})".format(user['first_name'],
                                                                                                                               user['user_id']))
                except:
                    print u'Failed to send message to {0} ({1})'.format(user['first_name'], user['user_id'])
            print u"New subscription: {} ({})".format(user['first_name'], user['user_id'])

    def listen(self, pause=1):
        self.is_alive = True
        print 'Subscription starts listening...'
        while self.is_alive:
            try:
                for data in self.subscription_db.find():
                    self.extend_expire(data)
                    self.subscription_db.remove(data)
                time.sleep(pause)
            except Exception, e:
                self.is_alive = False
                print("Subscription. Stop listening. Safely recovering from error.")
                print(e)
                try:
                    if os.path.getsize('reminder_log.txt') > 10*1024*1024: # 10mb
                        os.remove('log.txt')
                except:
                    pass
                with open('subscription_log.txt', 'a+') as f:
                    f.write('''Exception in get_update at {0}.\n'''.format(time.strftime("%d-%m-%Y %H:%M:%S")))
                    f.write(traceback.format_exc() + '\n')

if __name__ == "__main__":
    console = []