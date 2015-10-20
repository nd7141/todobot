# author: sivanov
# date: 19 Oct 2015
from __future__ import division
from emoji_chars import *
import pymongo, os
from telebot import TeleBot
import time
import codecs

def send_update(bot, users_db, groups_db, message):
    countu = 0
    countg = 0


    for user in users_db.find():
        try:
            bot.send_message(user['user_id'], message.format(user_name=user['first_name'], emoji_alarm=emoji_alarm,
                                     emoji_lightning=emoji_lightning, emoji_abc=emoji_abc,
                                     emoji_star_shine=emoji_star_shine, emoji_diamond=emoji_diamond,
                                     emoji_plus=emoji_plus),
                             disable_web_page_preview=True)
            countu += 1
            if not countu%10:
                time.sleep(1)
        except Exception, e:
            print e
            print u'Failed to send message to {0}({1})'.format(user['first_name'], user['user_id'])
            print

    for group in groups_db.find():
        try:
            bot.send_message(group['group_id'], message.format(user_name=group['title'], emoji_alarm=emoji_alarm,
                                                             emoji_lightning=emoji_lightning, emoji_abc=emoji_abc,
                                                             emoji_star_shine=emoji_star_shine, emoji_diamond=emoji_diamond,
                                                             emoji_plus=emoji_plus),
                             disable_web_page_preview=True)
            countg += 1
            if not countg%10:
                time.sleep(1)
        except:
            print u'Failed to send message to {0}({1})'.format(group['title'], group['group_id'])

    print u'Sent an update to {0} users and {1} groups'.format(countu, countg)
    bot.send_message(80639335, u'Sent an update to {0} users and {1} groups'.format(countu, countg)) # send to me

def get_token(filename):
    with open(filename) as f:
        return f.readlines()[0].strip()

if __name__ == '__main__':

    me = 80639335
    yura_pekov = 1040729
    yura_oparin = 93518804

    # setup databases
    client = pymongo.MongoClient()
    db = client.db
    # users_db = db['users_db']
    # groups_db = db['groups_db']
    users_db = db.test_users
    groups_db = db.test_groups

    for u in users_db.find():
        print u
    for g in groups_db.find():
        print g

    # # create bot instance
    token = get_token('token.txt')
    tb = TeleBot(token)

    # send update if file exists
    if os.path.isfile('update.txt'):
        with codecs.open('update.txt', "r", "utf-8") as f:
            message = f.read()
            send_update(tb, users_db, groups_db, message)
        # os.remove('update.txt')

