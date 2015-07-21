#!/usr/bin/python
'''

'''
from __future__ import division
__author__ = 'sivanov'
import pymongo, sys, time, os
import ToDoObjects as TDO
import ToDoBot as TDB


def get_token(filename):
    with open(filename) as f:
        return f.readlines()[0]


def wrapper(td, users_db, groups_db, tasks_db):
    def listener(*messages):
        for msg in messages:
            print u"{0}: {1}".format(msg['from']['first_name'], msg['text']) if 'text' in msg else ''
            update = TDO.ToDoUpdate(msg)
            result = update.execute(users_db, groups_db, tasks_db)
            if result:
                td.send_message(msg['chat']['id'], result)
    return listener

if __name__ == "__main__":

    # setup databases
    client = pymongo.MongoClient()
    db = client.db
    users_db = db['users_db']
    groups_db = db['groups_db']
    tasks_db = db['tasks_db']

    token = get_token('token.txt')

    td_bot = TDB.ToDoBot(token)
    td_bot.set_update_listener(wrapper(td_bot, users_db, groups_db, tasks_db))
    td_bot.polling()

    period = 3600 # seconds to relaunch script
    start = time.time()

    while True:
        if time.time() > start + period:
            print 'Relaunching the script...'
            os.execv(__file__, sys.argv)

    console = []