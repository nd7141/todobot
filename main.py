#!/usr/bin/python
'''

'''
from __future__ import division
__author__ = 'sivanov'
import pymongo, sys, time, os
import ToDoBot as TDB
from emoji_chars import *


def get_token(filename):
    with open(filename) as f:
        return f.readlines()[0]


def send_update(bot, users_db, groups_db, message):
    countu = 0
    countg = 0
    for user in users_db.find():
        try:
            bot.send_message(user['user_id'], message.format(user['first_name'], emoji_smile, emoji_right_arrow, emoji_right_arrow))
        except:
            print u'Failed to send message to {0}({1})'.format(user['first_name'], user['user_id'])
        else:
            countu += 1

    for group in groups_db.find():
        try:
            bot.send_message(group['group_id'], message.format(group['title'], emoji_smile, emoji_right_arrow, emoji_right_arrow))
        except:
            print u'Failed to send message to {0}({1})'.format(group['title'], group['group_id'])
        else:
            countg += 1
    print 'Sent an update to {0} users and {1} groups'.format(countu, countg)


if __name__ == "__main__":

    # setup databases
    client = pymongo.MongoClient()
    db = client.db
    users_db = db['users_db']
    groups_db = db['groups_db']
    tasks_db = db['tasks_db']
    # test_users = db['test_users']
    # test_groups = db['test_groups']

    token = get_token('token.txt')
    owm_token = get_token('owm_token.txt')
    geopy_user = get_token('geopy_username.txt')
    botan_token = int(get_token('botan_token.txt'))

    td_bot = TDB.ToDoBot(token, owm_token, users_db, groups_db, tasks_db, geopy_user, botan_token)
    td_bot.set_update_listener()
    td_bot.polling()


    # send update if file exists
    if os.path.isfile('update.txt'):
        with open('update.txt') as f:
            message = f.read().decode('utf8')
        send_update(td_bot, users_db, groups_db, message)
        os.remove('update.txt')


    period = 3600 # seconds to relaunch script
    start = time.time()

    while True:
        if time.time() > start + period:
            print 'Relaunching the script...'
            os.execv(__file__, sys.argv)

    console = []