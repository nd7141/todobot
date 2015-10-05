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

def get_traffic(lat, lng):
    ya_url = "https://static-maps.yandex.ru/1.x/?ll={lng},{lat}&spn=0.05,0.05&l=map,trf".format(lat=lat, lng=lng)
    return ya_url

def get_weather(place):
    try:
        url_place = urllib.quote(place.encode('utf-8'))
        observation = owm.weather_at_place(url_place)
    except Exception as e:
        print e
        return u'Temperature: N/A'
    if observation:
        w = observation.get_weather()
        return u"Temperature: {} {}".format(w.get_temperature('celsius')['temp'], u"\u2103")
    else:
        return u'Temperature: N/A'


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
    city = ''
    user = users_db.find_one({"user_id": data.get('from_id', '')})
    if user:
        city = user.get('city', '')
        lat = user.get('lat', 55.75396) # Moscow by default
        lng = user.get('lng', 37.620393)

    # compose a message
    messages = ['Pending tasks:']
    messages += get_tasks(chat_id)
    messages.append(u"City: {}".format(city))
    messages.append(get_weather(city))
    messages.append(u"Traffic: {}".format(get_traffic(lat, lng)))
    message = '\n'.join(messages)

    print chat_id, remind_at
    tb.send_message(chat_id, message)

    # set another reminder or remove reminder
    if data.get('repetitive', False):
        reminder_db.update(data, {"$set": {'remind_at': remind_at + 30}})
    else:
        reminder_db.remove(data)

rd = Reminder(reminder_db)
rd.set_messaging(messaging)
rd.listen(1)