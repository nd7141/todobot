'''

'''
from __future__ import division
__author__ = 'sivanov'
import pymongo
import ToDoObjects as TDO
import ToDoBot as TDB


def get_token(filename):
    with open(filename) as f:
        return f.readlines()[0]


def wrapper(td, users_db, tasks_db):
    def listener(*messages):
        for msg in messages:
            print msg['text'] if 'text' in msg else ''
            update = TDO.ToDoUpdate(msg)
            result = update.execute(users_db, tasks_db)
            if result:
                td.send_message(msg['chat']['id'], result)
    return listener

if __name__ == "__main__":

    # setup databases
    client = pymongo.MongoClient()
    db = client.db
    users_db = db['users_db']
    tasks_db = db['tasks_db']

    token = get_token('token.txt')

    td_bot = TDB.ToDoBot(token)
    td_bot.set_update_listener(wrapper(td_bot, users_db, tasks_db))
    td_bot.polling()

    while True:
        pass

    console = []