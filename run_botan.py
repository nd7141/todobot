# author: sivanov
# date: 15 Oct 2015
from __future__ import division
from BotanTodoBot import BotanTracker
import pymongo

# read token safely
def get_token(filename):
    with open(filename) as f:
        return f.readlines()[0]

# create a bot to send reminders
botan_token = int(get_token('botan_token.txt'))

# databases
client = pymongo.MongoClient()
db = client.db
botan_db = db['botan']

# listen to messages
botan_tracker = BotanTracker(botan_db, botan_token)
botan_tracker.listen()