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
        if not self.users_db.find_one({"user_id": self.update["from"]["id"]}):
            user = TDO.User.from_json(self.update['from'], self.update['date'])
            self.users_db.insert_one(user.__dict__)

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

    # Commands for bot

    def list(self, address):
        cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": address}).sort("created")
        tasks = [u"{0}. {1}".format(ix + 1, task['text']) for (ix, task) in enumerate(cursor)]
        return u'{} list:\n'.format(address if address else "Group") + '\n'.join(tasks) if tasks else u"There is no tasks in {} list!".format(address)

    def done(self, text, address):
        if address:
            numbers = text[len(address) + 2:]
            if numbers.strip().startswith("#all"):
                for task in self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, 'to_id': address}):
                    self.tasks_db.update({"_id": task["_id"]},
                          {"$set": {"finished": True, "end": time.time()}})
                return u"I removed {} list.".format(address)
        else:
            numbers = text
        try:
            numbers = map(int, numbers.split(','))
        except ValueError:
            return u"I'm very sorry. Some of the tasks do not exist."
        cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, 'to_id': address}).sort("created")
        finished_tsk = []
        for ix, task in enumerate(cursor):
            if ix + 1 in numbers:
                self.tasks_db.update({"_id": task["_id"]},
                          {"$set": {"finished": True, "end": time.time()}})
                finished_tsk.append(u'"{0}. {1}"'.format(ix+1, task['text']))
        if finished_tsk:
            return u"I'm pleased to claim that you finished {0}!\n {1}".format('; '.join(finished_tsk), self.list(address))
        return u"I'm very sorry. All of the tasks {0} do not exist.".format(', '.join(map(str, numbers)))

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


        return u'Saved {0} to {1} list'.format(', '.join(out), address if address else 'Group')
        return u"You wrote {0} to {1} list, my lord!\n {2}".format(count, who, self.list(who)) if count else "Please, provide non-empty task."

    def help(self):
        return ''' This is a Telegram ToDo bot.

        Write /help - to get this message.
        Write /todo task - to write another task. You can provide multiple tasks, where each task in a new line.
        Write /list - to list current tasks in your ToDo list.
        Write /done task1, task2, ... - to finish the task.
        Write /completed - to list completed tasks in your ToDo list. (new)

        Having more ideas or want to contribute? Write a comment to http://storebot.me/bot/todobbot.
        '''

    def cheer(self):
        return '''You're not a man, You're God!'''

    def make(self, text):
        lines = text.split(os.linesep)
        try:
            who = lines[0].split()[0]
        except IndexError:
            return "Please provide to whom you want assign a task."

        if lines[0] < 2:
            return "Please provide a task."
        else:
            tsks = [' '.join(lines[0].split()[1:])] + lines[1:]
            count = 0
            for t in tsks:
                if t.strip():
                    new_tsk = TDO.Task.from_json(self.update, t, who)
                    self.tasks_db.insert_one(new_tsk.__dict__)
                    count += 1
            return u"You wrote {0} task to {1}, my lord!".format(count, who) if count else "Please, provide non-empty task."

    def for_f(self, text):
        words = text.split()
        try:
            who = words[0]
        except IndexError:
            return "Please provide for whom you want to show ToDo list."
        cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": who}).sort("created")
        tasks = [u"{0}. {1}".format(ix + 1, task['text']) for (ix, task) in enumerate(cursor)]
        return who + ':\n' + '\n'.join(tasks) if tasks else u"{0} has no tasks!".format(who)

    def over(self, text):
        words = text.split()
        try:
            who = words[0]
        except IndexError:
            return "Please provide for whom you want to remove a task."
        try:
            numbers = map(int, ' '.join(words[1:]).split(','))
        except ValueError:
            return u"I'm very sorry. Some of the tasks are not numeric."

        cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": who}).sort("created")
        finished_tsk = []
        for ix, task in enumerate(cursor):
            if ix + 1 in numbers:
                self.tasks_db.update({"_id": task["_id"]},
                          {"$set": {"finished": True, "end": time.time()}})
                finished_tsk.append(str(ix+1))
        if finished_tsk:
            return u"I'm pleased to claim that {0} finished tasks {1}!".format(who, ','.join(finished_tsk))
        return u"I'm very sorry. Tasks {0} do not exist in the list of {1}.".format(','.join(map(str, numbers)), who)

    def count(self, db):
        return str(db.count())

    def completed(self):
        cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": True, "to_id": ''}).sort("created")
        tasks = []
        i = 0
        for task in cursor:
            if "end" in task:
                tasks.append(u"{0}. {1} ({2})".format(i + 1, task['text'], TDO.Update.strtime(task["end"])))
                i += 1
        return 'Completed tasks:\n' + '\n'.join(tasks) if tasks else "You have no finished tasks!"

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


    #TODO write more commands here

    def execute(self):
        self.commands = ['todo', 't',
                         'list', 'l',
                         'done', 'd',
                         'completed',
                         'start', 'help', 's', 'h',
                         'all',
                         'make', 'for', 'over',
                         'weather', 'city', 'me', 'cheer',
                         'countu', 'countg']

        self.commands += map(lambda s: s + "@todobbot", self.commands)

        print botan.track(self.botan_token, int(self.update['from']['id']), {}, 'Search')

        # Write new user, group into database
        self.write_user()
        self.write_group()

        # Execute command
        command = TDO.Update.get_command(self.update)
        if command in self.commands:
            text = TDO.Update.get_text(self.update, command)
            words = text.split()
            if len(words) and words[0].startswith("@") and len(words[0]) > 1 and words[0][1:] != "Group":
                address = words[0][1:]
            else:
                address = ''
            if command in ['list', 'list@todobbot', 'l']:
                result = self.list(address)
            elif command in ['todo', 'todo@todobbot', 't']:
                result = self.todo(text, address)
            elif command in ['done', 'done@todobbot', 'd']:
                result = self.done(text, address)
            elif command in ['help', 'start', 'help@todobbot' 'start@todobbot', 'h', 's', 'h@todobbot', 's@todobbot']:
                result = self.help()
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
            elif command.startswith('completed'):
                result = self.completed()
            elif command.startswith('weather'):
                result = self.weather(text)
            elif command.startswith('city'):
                result = self.get_city(text)
            elif command.startswith('me'):
                result = self.get_info()
            elif command.startswith('all'):
                result = self.list_all()
            return result