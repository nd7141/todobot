# author: sivanov
# date: 02 Oct 2015
from __future__ import division
import time
import traceback
from emoji_chars import *
import urllib
import datetime

class Reminder(object):
    def __init__(self, reminder_db, users_db, tasks_db, todobot, owm, **kwargs):
        self.reminder_db = reminder_db
        self.users_db = users_db
        self.tasks_db = tasks_db
        self.todobot = todobot
        self.owm = owm

    def set_messaging(self, messaging):
        self.send_message = messaging

    def get_traffic(self, lat, lng):
        ya_url = "https://static-maps.yandex.ru/1.x/?ll={lng},{lat}&spn=0.05,0.05&l=map,trf".format(lat=lat, lng=lng)
        return ya_url

    def get_weather(self, place):
        try:
            url_place = urllib.quote(place.encode('utf-8'))
            observation = self.owm.weather_at_place(url_place)
        except Exception as e:
            print e
            return u'Temperature: N/A'
        if observation:
            w = observation.get_weather()
            return u"{} {} {}".format(emoji_suncloud, w.get_temperature('celsius')['temp'], u"\u2103")
        else:
            return u'Temperature: N/A'


    def get_tasks(self, chat_id):
        texts = []
        count = 0
        for task in self.tasks_db.find({"chat_id": chat_id, "finished": False}).sort('created'):
            if 'text' in task:
                count += 1
                number = u"".join([emoji_numbers[d] for d in map(int, list(str(count)))])
                texts.append(u"{}. {}".format(number, task['text']))
        return texts


    def send_reminder(self, data):
        remind_at = float(data['remind_at'])
        chat_id = int(data['chat_id'])
        city = 'Moscow'
        user = self.users_db.find_one({"user_id": data.get('from_id', '')})
        if user:
            city = user.get('city', 'Moscow') # Moscow by default
            lat = user.get('lat', 55.75396)
            lng = user.get('lng', 37.620393)

        # compose a message
        messages = [u'{fire}'.format(fire=emoji_fire*3),
                    u"{} {}".format(emoji_fuji, datetime.date.today().strftime("%-d %B, %A")), '']
        messages += self.get_tasks(chat_id)
        messages.extend([u'', u"{} {}".format(emoji_globe, city), self.get_weather(city),
                         u"{} {}".format(emoji_car, self.get_traffic(lat, lng))])
        messages.append(u'{fire}'.format(fire=emoji_fire*3))
        message = '\n'.join(messages)

        print u'Chat {} reminds at {}'.format(chat_id, datetime.datetime.fromtimestamp(remind_at).strftime("%-d %B %-H:%M"))
        try:
            self.todobot.send_message(chat_id, message)
        except:
            print u'Failed to send message to {0}'.format(chat_id)

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
                with open('reminder_log.txt', 'a+') as f:
                    f.write('''Exception in get_update at {0}.\n'''.format(time.strftime("%d-%m-%Y %H:%M:%S")))
                    f.write(traceback.format_exc() + '\n')
