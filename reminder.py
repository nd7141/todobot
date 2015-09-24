# author: sivanov
# date: 23 Sep 2015
from __future__ import division
import pymongo
from pubsub import Subscriber
from threading import Timer
from telebot import TeleBot
import time

# read token safely
def get_token(filename):
    with open(filename) as f:
        return f.readlines()[0]

# create a bot to send reminders
token = get_token('token.txt')
tb = TeleBot(token)

# retrieve information from tasks_db collection
client = pymongo.MongoClient()
db = client.db
tasks_db = db.tasks_db
text_db = db.text_db
reminder_db = db.reminder_db


# a wrapper to send a message (used inside Timer)
def wrapper(chat_id, message):
    def send_reminder():
        print 'inside send_reminder'
        tb.send_message(chat_id, message)
    return send_reminder


# a function to release a Timer (used inside subscriber)
def create_timer(data):
    chat_id = int(data['chat_id'])
    time_at = float(data['time_at'])
    offset = time_at - time.time()
    if offset > 0:
        messages = ['Your tasks']
        count = 0
        for task in tasks_db.find({"chat_id": chat_id, "finished": False}).sort('created'):
            content = text_db.find_one({"message_id": task["message_id"]})
            if 'text' in content:
                count += 1
                messages.append(u"{}. {}".format(count, content['text']))
        message = '\n'.join(messages)
        func = wrapper(chat_id, message)
        Timer(offset, func).start()
        print 'Just released another timer'
    else:
        print 'The date is passed'

print 'Start listening...'
while True:
    if reminder_db.count():
        for data in reminder_db.find():
            create_timer(data)
            reminder_db.remove(data)
    time.sleep(1)

# create a subscriber to listen to reminder_db for next record to send to create_timer
# subscriber = Subscriber(db, 'reminder_db', callback=create_timer)
# print 'Starting subscriber...'
# subscriber.listen()