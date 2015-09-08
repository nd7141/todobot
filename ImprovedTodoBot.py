# author: sivanov
# date: 07 Sep 2015
from __future__ import division

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
                         ]

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


    def _tasks_from(self, lst):
        return list(self.tasks_db.find({"chat_id": self.update['chat']['id'], 'to_id': lst, 'finished': False}))

    def _change_state(self, state):
        self.users_db.update({"user_id": self.update['from']['id']},
                             {"$set": {'state{}'.format(self.update['chat']['id']): state}})

    def _all_lists(self):
        todos = dict()
        for task in self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False}):
            if 'text' in task:
                if task['to_id'] == '':
                    todos.setdefault('', []).append(task)
                else:
                    todos.setdefault(task['to_id'], []).append(task)
        return todos

    def _create_initial(self):
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(u'/todo', u'/completed')
        tasks = self.tasks_db.find({"chat_id": self.update['chat']['id'], 'finished': False, 'to_id': ''}).sort('created')
        for task in tasks:
            if 'text' in task:
                markup.add(task['text'])
        return markup

    def todo(self):
        self._change_state('todo_write')
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(u'Cancel')
        message = u'Please, write your task'
        return message, markup

    def todo_write(self):
        if self.update['text'].strip() == u'Cancel':
            message = u"Cancelled writing"
        else:
            if self.update['text'] in ['/todo', '/completed']:
                message = u'Cannot write task: {}'.format(self.update['text'])
            else:
                new_tsk = TDO.Task.from_json(self.update)
                self.tasks_db.insert_one(new_tsk.__dict__)
                message = u'New task {}'.format(emoji_sparkles)
        markup = self._create_initial()
        self._change_state('initial')
        return message, markup

    def remove_task(self, text):
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(u'Yes', u'No')
        message = u'Do you want to delete this task:\n{}'.format(text)
        self._change_state('remove_confirm')
        self.users_db.update({"user_id": self.update['from']['id']},
            {"$set":  {u"tmp{}".format(self.update['chat']['id']): text}})
        return message, markup

    def remove_confirm(self):
        if self.update['text'] == u'Yes':
            user = self.users_db.find_one({"user_id": self.update['from']['id']})
            tmp = user[u"tmp{}".format(self.update['chat']['id'])]
            todos = self._all_lists()
            tasks = todos['']
            for task in tasks:
                if task['text'] == tmp:
                    print 'task', task
                    self.tasks_db.update({"_id": task["_id"]},
                        {"$set": {"finished": True, "end": time.time()}})
                    message = u'Just finished task:\n{}'.format(tmp)
                    break
            else:
                message = u"Didn't find that task"
            markup = self._create_initial()
            self._change_state('initial')
        elif self.update['text'] == u'No':
            message = u'Ahh... Okay'
            markup = self._create_initial()
            self._change_state('initial')
        else:
            message = u"Please, enter Yes or No!"
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add([u'Yes', u'No'])
        return message, markup

    def completed(self):
        cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": True, "to_id": ''}).sort("end", -1)
        markup = self._create_initial()
        message = u'Here are your completed tasks:\n'
        message += '\n'.join([u'{} ({})'.format(task['text'], TDO.Update.strtime(task['end']))
                              for task in cursor if 'text' in task])
        return message, markup

    def execute(self):
        mm = None, None

        print 'chat id', self.update['chat']['id']

        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        state = user.get('state{}'.format(self.update['chat']['id']), 'initial')

        print
        print 'Started with state', state

        if state == 'initial':
            text= self.update['text'].strip()
            if text in ['/todo']:
                mm = self.todo()
            elif text in ['/completed']:
                mm = self.completed()
            else:
                texts = [task['text'] for task in self._tasks_from(lst='') if 'text' in task]
                if text in texts:
                    mm = self.remove_task(text)
        elif state == 'todo_write':
            mm = self.todo_write()
        elif state == 'todo_choose_list':
            mm = self.todo_choose_list()
        elif state == 'remove_confirm':
            mm = self.remove_confirm()

        return mm