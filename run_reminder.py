# author: sivanov
# date: 23 Sep 2015
from __future__ import division
import pymongo
from threading import Timer
from telebot import TeleBot
import time, datetime
import logging
from ReminderTodoBot import Reminder

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
reminder_db = db.reminder_db


def get_tasks(chat_id):
    texts = []
    count = 0
    for task in tasks_db.find({"chat_id": chat_id, "finished": False}).sort('created'):
        if 'text' in task:
            count += 1
            texts.append(u"{}. {}".format(count, task['text']))
    return texts


def messaging(data):
    remind_at = float(data['remind_at'])
    chat_id = int(data['chat_id'])

    # compose a message
    messages = ['Your tasks']
    messages += get_tasks(chat_id)
    message = '\n'.join(messages)

    print chat_id, remind_at
    tb.send_message(chat_id, message)

    # set another reminder or remove reminder
    if data.get('repetitive', False):
        reminder_db.update(data, {"$set": {'remind_at': remind_at + 86400}})
    else:
        reminder_db.remove(data)

rd = Reminder(reminder_db)
rd.set_messaging(messaging)
rd.listen(1)