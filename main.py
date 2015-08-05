#!/usr/bin/python
'''

'''
from __future__ import division
__author__ = 'sivanov'
import pymongo, sys, time, os
import ToDoBot as TDB


def get_token(filename):
    with open(filename) as f:
        return f.readlines()[0]

def send_update(bot, users_db, groups_db, message):
    for user in users_db.find():
        bot.send_message(user['user_id'], message)
    for group in groups_db.find():
        bot.send_message(group['group_id'], message)

if __name__ == "__main__":

    # setup databases
    client = pymongo.MongoClient()
    db = client.db
    users_db = db['users_db']
    groups_db = db['groups_db']
    tasks_db = db['tasks_db']

    token = get_token('token.txt')
    owm_token = get_token('owm_token.txt')

    td_bot = TDB.ToDoBot(token, owm_token, users_db, groups_db, tasks_db)
    td_bot.set_update_listener()
    td_bot.polling()

    if os.path.isfile('update.txt'):
        with open('update.txt') as f:
            message = f.read()
        os.remove('update.txt')
        send_update(td_bot, users_db, groups_db, message)    



    period = 3600 # seconds to relaunch script
    start = time.time()

    while True:
        if time.time() > start + period:
            print 'Relaunching the script...'
            os.execv(__file__, sys.argv)

    console = []