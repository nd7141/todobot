# author: sivanov
# date: 23 Sep 2015
from __future__ import division
import pymongo
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

print 'Start listening...'
while True:
    for data in reminder_db.find():
        time_at = float(data['time_at'])
        if time_at < time.time():
            chat_id = int(data['chat_id'])
            # compose a message
            messages = ['Your tasks']
            count = 0
            texts = []
            for task in tasks_db.find({"chat_id": chat_id, "finished": False}).sort('created'):
                for text in text_db.find({"message_id": task["message_id"]}):
                    count += 1
                    messages.append(u"{}. {}".format(count, text['text']))
            message = '\n'.join(messages)

            print chat_id, time_at
            tb.send_message(chat_id, message)

            # set another reminder or remove reminder
            if data.get('repetitive', False):
                reminder_db.update(data, {"$set": {'time_at': time_at + 86400}})
            else:
                reminder_db.remove(data)
    time.sleep(1)