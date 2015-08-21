# author: sivanov
# date: 20 Aug 2015
from __future__ import division
import telebot, threading, traceback, time, os
import ToDoObjects as TDO
import pyowm
import urllib
from geopy import geocoders
import pprint
import botan
from emoji_chars import *
from messages import *
import markups

class ToDoBot(telebot.TeleBot, object):

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
            result, markup = self.execute()
            print 'Result', result
            try:
                print 'Keyboard', markup.keyboard
            except AttributeError:
                print 'Keyboard', None
            if result:
                self.send_message(msg['chat']['id'], result, reply_markup=markup)

    def set_update_listener(self):
        self.update_listener.append(self.listener)

    def set_update(self, update):
        self.update = update.update

    def _all_lists(self):
        todos = dict()
        for task in self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False}):
            if not task['to_id']:
                todos.setdefault('Group', []).append(task)
            else:
                todos.setdefault(task['to_id'], []).append(task)
        return todos

    def todo_initial(self):
        markup = markups.cancel_btn
        message = "What is the task?"
        self.users_db.update({"user_id": self.update['from']['id']},
            {"$set": {"state": "bot_todo"}})
        return message, markup

    def todo_respond(self):
        self.users_db.update({"user_id": self.update['from']['id']},
                {"$set": {"state": "bot_initial"}})

        if self.update['text'].strip().split()[0] == 'Cancel':
            message = u"{0} Do you wanna write another task? {1}".format(emoji_right_arrow, emoji_pencil)
        else:
            #TODO write task to db
            message = u"Well done! {0}".format(emoji_clap)

        markup = markups.initial

        return message, markup

    def list_initial(self):
        self.users_db.update({"user_id": self.update['from']['id']},
                {"$set": {"state": "bot_list"}})
        todos = [u"{} ({})".format(k, len(v)) for k,v in self._all_lists().iteritems()]
        todos.append('Cancel')
        n = len(todos)
        rows = [todos[i:i + n//3] for i in range(0, n, n//3)]
        markup = telebot.types.ReplyKeyboardMarkup()
        for r in rows:
            markup.add(*r)
        message = u"{0} What Todo list?".format(emoji_right_arrow)
        return message, markup

    def list_respond(self):
        self.users_db.update({"user_id": self.update['from']['id']},
                {"$set": {"state": "bot_initial"}})
        markup = markups.initial

        message = u"{0} Do you wanna write another task? {1}".format(emoji_right_arrow, emoji_pencil)
        todos = self._all_lists()
        address = self.update['text'].strip().split()[0]
        if address != 'Cancel' and address in todos.keys():
            if address == 'Group':
                address = ''
            cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": address}).sort("created")
            tasks = [u"{0}. {1}".format(ix + 1, task['text']) for (ix, task) in enumerate(cursor)]
            message = list0.format(address if address else "Group") + '\n'.join(tasks)
        return message, markup

    def done_initial(self):
        self.users_db.update({"user_id": self.update['from']['id']},
                {"$set": {"state": "bot_done0"}})
        message = u"{0} What Todo list?".format(emoji_right_arrow)
        todos = self._all_lists()
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1)
        markup.add(*[u"{0} ({1})".format(l, len(v)) for l,v in todos.iteritems()])
        markup.add('Cancel')
        return message, markup

    def done0(self):
        address = self.update['text'].strip().split()[0]
        todos = self._all_lists()
        if address != 'Cancel' and address in todos.keys():
            self.users_db.update({"user_id": self.update['from']['id']},
                {"$set": {"state": "bot_done1", "tmp": address}})
            tasks = sorted(todos[address], key=lambda task: task['created'], reverse=True)
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1)
            markup.add(*[u"{1}. {0} ...".format(' '.join(task['text'].split()[:5]), i+1) for i, task in enumerate(tasks)])
            markup.add("Cancel")
            print 'markup', markup.keyboard
            message = u"{0} What task is done?".format(emoji_right_arrow)
        else:
            self.users_db.update({"user_id": self.update['from']['id']},
                {"$set": {"state": "bot_initial"}})
            markup = markups.initial
            message = u"{0} Do you wanna write another task? {1}".format(emoji_right_arrow, emoji_pencil)
        return message, markup

    def done1(self):
        self.users_db.update({"user_id": self.update['from']['id']},
            {"$set": {"state": "bot_initial"}})
        todos = self._all_lists()
        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        address = user["tmp"]
        tasks = sorted(todos[address], key=lambda task: task['created'], reverse=True)
        number = self.update['text'].split('.')[0]
        try:
            number = int(number)
        except ValueError:
            pass
        else:
            self.tasks_db.update({"_id": tasks[number-1]["_id"]},
                                 {"$set": {"finished": True, "end": time.time()}})
        markup = markups.initial
        message = u"{0} Do you wanna write another task? {1}".format(emoji_right_arrow, emoji_pencil)
        return message, markup


    # Remove all command as ambiguous 
    def all_initial(self):
        todos = self._all_lists()
        return u"\n".join([u"{}. {} ({})".format(i+1, k, v) for (i,(k,v)) in enumerate(todos.iteritems())]), None

    def execute(self):
        message = None
        markup = None
        # print self.update

        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        print 'State:', user['state']

        command = TDO.Update.get_command(self.update)

        state = user.setdefault('state', 'bot_initial')
        if state == 'bot_initial':
            if command in self.commands:
                if command in ['todo', 'todo@todobbot', 't']:
                    message, markup  = self.todo_initial()
                elif command in ['list', 'list@todobbot', 'l']:
                    message, markup = self.list_initial()
                elif command in ['done', 'done@todobbot', 'd']:
                    message, markup = self.done_initial()
                elif command in ['all', 'all@todobbot', 'a']:
                    message, markup = self.all_initial()
        elif state == 'bot_todo':
            message, markup  = self.todo_respond()
        elif state == 'bot_list':
            message, markup = self.list_respond()
        elif state == 'bot_done0':
            message, markup = self.done0()
        elif state == 'bot_done1':
            message, markup = self.done1()

        return message, markup
