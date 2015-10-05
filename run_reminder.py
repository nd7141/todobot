# author: sivanov
# date: 23 Sep 2015
from __future__ import division
import pymongo
from threading import Timer
from telebot import TeleBot
import time, datetime
import logging
from ReminderTodoBot import Reminder
import urllib
import pyowm
from emoji_chars import *

# read token safely
def get_token(filename):
    with open(filename) as f:
        return f.readlines()[0]

# create a bot to send reminders
token = get_token('token.txt')
owm_token = get_token('owm_token.txt')
tb = TeleBot(token)
owm = pyowm.OWM(owm_token)

# databases
client = pymongo.MongoClient()
db = client.db
tasks_db = db.tasks_db
reminder_db = db.reminder_db
users_db = db.users_db

rd = Reminder(reminder_db, users_db, tasks_db, tb, owm)
rd.listen(1)