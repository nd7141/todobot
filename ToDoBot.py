'''
'''
from __future__ import division
__author__ = 'sivanov'
import telebot, threading, traceback, time, os
import ToDoObjects as TDO
import pyowm
import urllib
from geopy import geocoders
import pprint
import botan
from emoji_chars import *
from messages import *

class ToDoBot(telebot.TeleBot, object):
    """ ToDoBot overrides the functionality of get_update function of TeleBot.
    In addition to getting array of updates (messages), we also get User and (optional) Group object.
    """

    def __init__(self, token, owm_token, users_db, groups_db, tasks_db, geopy_user, botan_token):
        super(self.__class__, self).__init__(token)
        self.users_db = users_db
        self.groups_db = groups_db
        self.tasks_db = tasks_db
        self.owm = pyowm.OWM(owm_token)
        self.geopy_user = geopy_user
        self.botan_token = botan_token

        self.commands = ['todo', 't',
                         'list', 'l',
                         'done', 'd',
                         'completed', 'c',
                         'start', 'help', 's', 'h',
                         'all', 'a',
                         'tutorial',
                         'feedback',
                         'weather', 'city', 'me', 'cheer',
                         'countu', 'countg']

        self.commands += map(lambda s: s + "@todobbot", self.commands)

    def get_update(self):
        new_messages = []
        try:
            updates = telebot.apihelper.get_updates(self.token, offset=(self.last_update_id + 1), timeout=20)
        except Exception as e:
            print e
            print("TeleBot: Exception occurred.")
            with open('log.txt', 'a+') as f:
                f.write('''Exception in get_update at {0}.\n'''.format(time.strftime("%d-%m-%Y %H:%M:%S")))
                f.write(traceback.format_exc() + '\n')
        else:
            for update in updates:
                if update['update_id'] > self.last_update_id:
                    self.last_update_id = update['update_id']

                new_messages.append(update['message'])

        if len(new_messages) > 0:
            self.__notify_update(new_messages)
            self._notify_command_handlers(new_messages)

    def __notify_update(self, new_messages):
        for listener in self.update_listener:
            t = threading.Thread(target=listener, args=new_messages)
            t.start()

    def polling(self):
        """
        This function creates a new Thread that calls an internal __polling function.
        This allows the bot to retrieve Updates automagically and notify listeners and message handlers accordingly.

        Do not call this function more than once!

        Always get updates.
        :return:
        """
        self.__stop_polling = False
        self.polling_thread = threading.Thread(target=self.__polling, args=())
        self.polling_thread.daemon = True
        self.polling_thread.start()

    def __polling(self):
        print('TeleBot: Started polling.')
        while not self.__stop_polling:
            try:
                self.get_update()
            except Exception as e:
                print("TeleBot: Exception occurred.")
                print(e)
                with open('log.txt', 'a+') as f:
                    f.write('''Exception in get_update at {0}.\n'''.format(time.strftime("%d-%m-%Y %H:%M:%S")))
                    f.write(traceback.format_exc() + '\n')
                self.__stop_polling = True

        print('TeleBot: Stopped polling.')

    def listener(self, *messages):
        for msg in messages:
            print u"{0}: {1}".format(msg['from']['first_name'], msg['text']) if 'text' in msg else ''
            update = TDO.Update(msg)
            self.set_update(update)
            result = self.execute()
            if result:
                self.send_message(msg['chat']['id'], result)

    def set_update_listener(self):
        self.update_listener.append(self.listener)

    def set_update(self, update):
        self.update = update.update

    def write_user(self):
        user = self.users_db.find_one({"user_id": self.update["from"]["id"]})
        if not user:
            user_json = TDO.User.from_json(self.update['from'], self.update['date'])
            self.users_db.insert_one(user_json.__dict__)
            return self.users_db.find_one({"user_id": self.update["from"]["id"]})
        return user

    def write_group(self):
        if "title" in self.update["chat"]:
            group = self.groups_db.find_one({"group_id": self.update["chat"]["id"]})
            if group:
                prts = group["participants"]
                if self.update["from"]["id"] not in prts:
                    prts.append(self.update["from"]["id"])
                    self.groups_db.update({"_id": group["_id"]},
                              {"$set": {"participants": prts}})
            else:
                group = TDO.Group.from_json(self.update["chat"], self.update["date"], self.update["from"]["id"])
                self.groups_db.insert_one(group.__dict__)

    def change_user_state(self, user_id, field, state):
        user = self.users_db.find_one({"user_id": self.update["from"]["id"]})
        if user:
            self.users_db.update({"user_id": user_id},
                {"$set": {field: state}})

    # Commands for bot
    def list(self, address):
        if address == 'Group':
            address = ''
        cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": address}).sort("created")
        tasks = [u"{0}. {1}".format(ix + 1, task['text']) for (ix, task) in enumerate(cursor)]
        return list0.format(address if address else "Group") + '\n'.join(tasks) if tasks else \
            list_er0.format(address if address else "Group")

    def done(self, text, address):
        if address:
            numbers = text[len(address) + 2:]
            if numbers.strip().startswith("all"):
                if address == 'Group':
                    address = ''
                for task in self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, 'to_id': address}):
                    self.tasks_db.update({"_id": task["_id"]},
                          {"$set": {"finished": True, "end": time.time()}})
                if not address:
                    address = 'Group'
                return done1.format(address)
        else:
            numbers = text
        try:
            numbers = map(int, numbers.split(','))
        except ValueError:
            return done_er0
        cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, 'to_id': address}).sort("created")
        finished_tsk = []
        for ix, task in enumerate(cursor):
            if ix + 1 in numbers:
                self.tasks_db.update({"_id": task["_id"]},
                          {"$set": {"finished": True, "end": time.time()}})
                finished_tsk.append(u'"{0}. {1}"'.format(ix+1, task['text']))
        if finished_tsk:
            return done0.format('; '.join(finished_tsk))
        return done_er0

    def todo(self, text, address):
        if address:
            tasks = text[len(address) + 2:].split(os.linesep)
        else:
            tasks = text.split(os.linesep)
        count = 0
        out = []

        for t in tasks:
            if t.strip():
                words = t.split()
                new_tsk = TDO.Task.from_json(self.update, t, address)
                out.append(u'"{0}..."'.format(words[0]))
                self.tasks_db.insert_one(new_tsk.__dict__)
                count += 1

        if count:
            return todo0.format(', '.join(out), address if address else 'Group')
        return todo_er0

    def help(self):
        return help0

    def cheer(self):
        return u'''You're not a man, You're God!'''

    def count(self, db):
        return str(db.count())

    def completed(self, text):
        try:
            k = int(text)
        except ValueError:
            if text.strip().startswith("all"):
                k = float("+inf")
            else:
                k = 3
        cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": True, "to_id": ''}).sort("end", -1)
        i = 0
        tasks = [u"{0}. {1} ({2})".format(i + 1, task['text'], TDO.Update.strtime(task["end"]))
                 for i, task in enumerate(cursor) if "end" in task and i < k]
        tasks.append(u"Use /completed {0} to show all tasks".format(i)) if i+1-k > 0 else None
        return completed0.format('\n'.join(tasks)) if tasks else completed_er0

    def weather(self, name):
        try:
            url_place = urllib.quote(name.encode('utf-8'))
            observation = self.owm.weather_at_place(url_place)
        except Exception as e:
            print e
            return 'No weather for this place!'
        if observation:
            w = observation.get_weather()
            return u"{0} {1}".format((w.get_temperature('celsius')['temp']), u"\u2103")
        else:
            return 'No weather for this place!'

    def get_city(self, name):
        err_s = 'Provide the name of your city!'
        if len(name) > 1:
            gn = geocoders.GeoNames(username=self.geopy_user)
            g = gn.geocode(name)
            if g:
                try:
                    city = g.raw['name']
                except:
                    return err_s
                self.users_db.update({"user_id": self.update["from"]["id"]},
                    {"$set": {"info.city": city}})
                return 'Updated your current city!'
            else:
                return err_s
        else:
            return err_s

    def get_info(self):
        s = "Name: {0}\nID: {1}\nCity: {2}\n"
        count = 0
        for user in self.users_db.find({"user_id": self.update["from"]["id"]}):
            count += 1
            city = 'Use /city command to specify your city!'
            if 'info' in user:
                if 'city' in user['info']:
                    city = user['info']['city']
            s = s.format(user['first_name'] + ' ' + user['last_name'], user['user_id'], city)
        return s

    def list_all(self):
        todos = dict()
        for task in self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False}):
            if not task['to_id']:
                todos['Group'] = todos.setdefault('Group', 0) + 1
            else:
                todos[task['to_id']] = todos.setdefault(task['to_id'], 0) + 1
        return u"\n".join([u"{}. {} ({})".format(i+1, k, v) for (i,(k,v)) in enumerate(todos.iteritems())])

    def tutorial(self, user, command):
        # extract text and address
        if command in self.commands:
            text = TDO.Update.get_text(self.update, command)
            words = text.split()
            if len(words) and words[0].startswith("@") and len(words[0]) > 1:
                address = words[0][1:]
            else:
                address = ''
        if not user['state']:
            self.change_user_state(user['user_id'], 'state', 'training0')
            return tutorial0.format(user['first_name'], emoji_smile)
        elif user['state'] == 'training0':
            if command in ['todo', 'todo@todobbot', 't']:
                self.change_user_state(user['user_id'], 'state', 'training1')
                print 'Sent todo to botan:', botan.track(self.botan_token, self.update['chat']['id'], self.update, '/todo')
                result = self.todo(text, address)
                return result + tutorial1.format(emoji_wink)
            else:
                return tutorial_er0
        elif user['state'] == 'training1':
            if command in ['list', 'list@todobbot', 'l']:
                self.change_user_state(user['user_id'], 'state', 'training2')
                print 'Sent list to botan:', botan.track(self.botan_token, self.update['chat']['id'], self.update, '/list')
                result = self.list(address)
                return result + tutorial2.format(emoji_thumb)
            else:
                return tutorial_er1
        elif user['state'] == 'training2':
            if command in ['done', 'done@todobbot', 'd']:
                self.change_user_state(user['user_id'], 'state', 'training3')
                print 'Sent done to botan:', botan.track(self.botan_token, self.update['chat']['id'], self.update, '/done')
                result = self.done(text, address)
                return result + tutorial3.format(emoji_clap)
            else:
                return tutorial_er2
        elif user['state'] == 'training3':
            if command in ['completed', 'completed@todobbot', 'c']:
                self.change_user_state(user['user_id'], 'state', 'training4')
                self.change_user_state(user['user_id'], 'trained', True)
                result = self.completed(text)
                return result + tutorial4.format(emoji_one, emoji_two, emoji_sparkles)
            else:
                return tutorial_er3

    def feedback(self):
        return feedback0

    #TODO write more commands here

    def execute(self):

        # Send user statistics to botan
        print 'Sent user to botan:', botan.track(self.botan_token, self.update['from']['id'], self.update, 'User')
        if "title" in self.update["chat"]:
            print 'Sent group to botan:', botan.track(self.botan_token, self.update['chat']['id'], self.update, 'Group')

        # Write new user, group into database
        user = self.write_user()
        self.write_group()

        # extract command, text, address
        command = TDO.Update.get_command(self.update)

        # Train new user (if not in the group)
        if not user.setdefault('trained', False) and "title" not in self.update["chat"]:
            user["state"] = user.setdefault("state", "")
            result = self.tutorial(user, command)
            return result
        else:
            # Execute command
            if command in self.commands:
                text = TDO.Update.get_text(self.update, command)
                words = text.split()
                if len(words) and words[0].startswith("@") and len(words[0]) > 1:
                    address = words[0][1:]
                else:
                    address = ''
                if command in ['list', 'list@todobbot', 'l']:
                    print 'Sent list to botan:', botan.track(self.botan_token, self.update['chat']['id'], self.update, '/list')
                    result = self.list(address)
                elif command in ['todo', 'todo@todobbot', 't']:
                    print 'Sent todo to botan:', botan.track(self.botan_token, self.update['chat']['id'], self.update, '/todo')
                    result = self.todo(text, address)
                elif command in ['done', 'done@todobbot', 'd']:
                    print 'Sent done to botan:', botan.track(self.botan_token, self.update['chat']['id'], self.update, '/done')
                    result = self.done(text, address)
                elif command in ['help', 'start', 'help@todobbot', 'start@todobbot', 'h', 's', 'h@todobbot', 's@todobbot']:
                    result = self.help()
                elif command in ['completed', 'completed@todobbot', 'c']:
                    result = self.completed(text)
                elif command in ['all', 'a@todobbot', 'a']:
                    result = self.list_all()
                elif command in ['tutorial', 'tutorial@todobbot']:
                    if "title" not in self.update["chat"]:
                        user['state'] = ''
                        self.change_user_state(user['user_id'], 'trained', False)
                        result = self.tutorial(user, command)
                    else:
                        result = 'Please, use personal chat with @Todobbot to take tutorial.'
                elif command in ['feedback', 'feedback@todobbot']:
                    result = self.feedback()
                elif command.startswith('cheer'):
                    result = self.cheer()
                elif command.startswith('make'):
                    result = self.make(text)
                elif command.startswith('for'):
                    result = self.for_f(text)
                elif command.startswith('over'):
                    result = self.over(text)
                elif command.startswith('countu'):
                    result = self.count(self.users_db)
                elif command.startswith('countg'):
                    result = self.count(self.groups_db)
                elif command.startswith('weather'):
                    result = self.weather(text)
                elif command.startswith('city'):
                    result = self.get_city(text)
                elif command.startswith('me'):
                    result = self.get_info()
                return result