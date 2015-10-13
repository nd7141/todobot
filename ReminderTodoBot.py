# author: sivanov
# date: 02 Oct 2015
from __future__ import division
import time
import traceback
from emoji_chars import *
import urllib
import datetime
import os

class Reminder(object):
    def __init__(self, reminder_db, users_db, tasks_db, todobot, owm, **kwargs):
        self.reminder_db = reminder_db
        self.users_db = users_db
        self.tasks_db = tasks_db
        self.todobot = todobot
        self.owm = owm
        self.messages = []

    def set_messaging(self, messaging):
        self.send_message = messaging

    def get_traffic(self, lat, lng):
        ya_url = "https://static-maps.yandex.ru/1.x/?ll={lng},{lat}&spn=0.05,0.05&l=map,trf".format(lat=lat, lng=lng)
        return ya_url

    # message 1
    def get_greetings(self, data):
        user = self.users_db.find_one({"user_id": data['from_id']})
        if user:
            first_name = user['first_name']
        else:
            first_name = ""
        self.messages.append(u"Hey {} {}".format(first_name, emoji_smile))

    # message 2
    def get_city_info(self, city):
        # day
        day = datetime.datetime.now().strftime("%-d %B")
        # temperature
        try:
            url_place = urllib.quote(city.encode('utf-8'))
            observation = self.owm.weather_at_place(url_place)
        except Exception as e:
            print e
            temperature = u'Sunny {}'.format(emoji_sun)
        else:
            if observation:
                w = observation.get_weather()
                try:
                    t = int(float(w.get_temperature('celsius')['temp']))
                    temperature = u"{:+}{}".format(t, u"\u2103")
                except:
                    temperature = u'Sunny {}'.format(emoji_sun)
            else:
                temperature = u'Sunny {}'.format(emoji_sun)
        self.messages.append(u"It's {} and {} in {} {}".format(day, temperature, city.split(',')[0], emoji_city))

    # message 3
    def get_number_completed(self, data):
        # number of completed
        completed = self.tasks_db.count({"chat_id": data['chat_id'], "finished": True})
        if completed:
            self.messages.append(u"You already completed {} tasks {}".format(completed, emoji_check_mark))
        else:
            self.messages.append(u"Get your first task done! {}".format(emoji_bomb))

    # message 4
    def get_tasks(self, chat_id):
        texts = []
        count = 0
        for task in self.tasks_db.find({"chat_id": chat_id, "finished": False}).sort('created'):
            if 'text' in task:
                count += 1
                number = u"".join([emoji_numbers[d] for d in map(int, list(str(count)))])
                texts.append(u"{} {}".format(number, task['text']))
        if count:
            self.messages.append(u"\n".join(texts))
        else:
            self.messages.append(u"It's time to create another task! {}".format(emoji_bomb))

    def send_reminder(self, data):
        remind_at = float(data['remind_at'])
        chat_id = int(data['chat_id'])
        city = 'Moscow'
        user = self.users_db.find_one({"user_id": data.get('from_id', '')})
        if user:
            city = user.get('city', 'Moscow') # Moscow by default
            lat = user.get('lat', 55.75396)
            lng = user.get('lng', 37.620393)

        # compose messages
        self.get_greetings(data)
        self.get_city_info(city)
        self.get_number_completed(data)
        self.get_tasks(chat_id)

        print u'Chat {} reminds at {}'.format(chat_id, datetime.datetime.fromtimestamp(remind_at).strftime("%-d %B %-H:%M"))
        for message in self.messages:
            try:
                self.todobot.send_message(chat_id, message)
            except:
                print u'Failed to send message to {0}'.format(chat_id)
        self.messages = []

        # set another reminder or remove reminder
        if data.get('repetitive', False):
            self.reminder_db.update(data, {"$set": {'remind_at': remind_at + 86400}})
        else:
            self.reminder_db.remove(data)

    def listen(self, pause=1):
        self.is_alive = True
        print 'Reminder starts listening...'
        while self.is_alive:
            try:
                for data in self.reminder_db.find({"remind_at": {"$lt": time.time()}}):
                    self.send_reminder(data)
                time.sleep(pause)
            except Exception, e:
                # self.is_alive = False
                print("Reminder. Stop listening. Safely recovering from error.")
                print(e)
                try:
                    if os.path.getsize('reminder_log.txt') > 10*1024*1024: # 10mb
                        os.remove('log.txt')
                except:
                    pass
                with open('reminder_log.txt', 'a+') as f:
                    f.write('''Exception in get_update at {0}.\n'''.format(time.strftime("%d-%m-%Y %H:%M:%S")))
                    f.write(traceback.format_exc() + '\n')
