#!/usr/bin/python
'''

'''
from __future__ import division
__author__ = 'sivanov'
import pymongo, sys, time, os
import ToDoBot as TDB
from emoji_chars import *
import KeyTodoBot as KTDB
import ImprovedTodoBot as ITDB
from pubsub import Publisher

import urllib3
urllib3.disable_warnings()

def get_token(filename):
    with open(filename) as f:
        return f.readlines()[0].strip()

if __name__ == "__main__":


    # setup databases
    client = pymongo.MongoClient()
    db = client.db
    users_db = db['users_db']
    groups_db = db['groups_db']
    tasks_db = db['tasks_db']
    text_db = db['text_db']
    reminder_db = db['reminder_db']
    public_tasks_db = db['public']
    botan_db = db['botan']

    token = get_token('token.txt')
    owm_token = get_token('owm_token.txt')
    geopy_user = get_token('geopy_username.txt')
    botan_token = get_token('botan_token.txt')

    td_bot = ITDB.ToDoBot(token, owm_token, users_db, groups_db, tasks_db, public_tasks_db, reminder_db, botan_db, geopy_user, botan_token)
    td_bot.set_update_listener()
    td_bot.polling()

    period = 600 # seconds to relaunch script
    start = time.time()

    while True:
        if time.time() > start + period:
            print 'Relaunching the script...'
            os.execv(__file__, sys.argv)

    console = []