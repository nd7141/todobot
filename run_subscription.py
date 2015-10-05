# author: sivanov
# date: 05 Oct 2015
from __future__ import division
from telebot import TeleBot
import pymongo
from SubscriptionTodoBot import Subscription


# read token safely
def get_token(filename):
    with open(filename) as f:
        return f.readlines()[0]

# create a bot to send reminders
token = get_token('token.txt')
tb = TeleBot(token)

# databases
client = pymongo.MongoClient()
db = client.db
tasks_db = db.tasks_db
subscription_db = db.subscription_db
users_db = db.users_db

sb = Subscription(subscription_db, users_db, tb)
sb.listen()