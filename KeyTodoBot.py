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
        # markup = markups.cancel_btn
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard= True)
        markup.add('Cancel')
        message = "What is the task?"
        self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_todo')
        return message, markup

    def todo_respond(self):
        self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')

        if self.update['text'].strip().split()[0] == 'Cancel':
            message = u"{0} Do you wanna write another task? {1}".format(emoji_right_arrow, emoji_pencil)
        else:
            words = self.update['text'].split()
            if len(words) and words[0].startswith("@") and len(words[0]) > 1:
                address = words[0][1:]
            else:
                address = ''
            if address:
                tasks = self.update['text'][len(address) + 2:].split(os.linesep)
            else:
                tasks = self.update['text'].split(os.linesep)

            for t in tasks:
                if t.strip():
                    new_tsk = TDO.Task.from_json(self.update, t, address)
                    self.tasks_db.insert_one(new_tsk.__dict__)
            message = u"Well done! {0}".format(emoji_clap)

        markup = markups.initial

        return message, markup

    def list_initial(self):
        self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_list')
        todos = [u"{} ({})".format(k, len(v)) for k,v in self._all_lists().iteritems()]
        todos.append('Cancel')
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(*todos)
        message = u"{0} What Todo list?".format(emoji_right_arrow)
        return message, markup

    def list_respond(self):
        self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
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
        self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_done0')
        message = u"{0} What Todo list?".format(emoji_right_arrow)
        todos = self._all_lists()
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(*[u"{0} ({1})".format(l, len(v)) for l,v in todos.iteritems()])
        markup.add('Cancel')
        return message, markup

    def done0(self):
        address = self.update['text'].strip().split()[0]
        todos = self._all_lists()
        if address == 'Cancel':
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
            markup = markups.initial
            message = u"{0} Do you wanna write another task? {1}".format(emoji_right_arrow, emoji_pencil)
        else:
            if address in todos.keys():
                self._set_field(self.users_db, {"user_id": self.update['from']['id']},
                                {"tmp{}".format(self.update["chat"]["id"]): address})
                self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_done1')
                tasks = sorted(todos[address], key=lambda task: task['created'], reverse=True)
                markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                markup.add(*[u"{1}. {0} ...".format(' '.join(task['text'].split()[:5]), i+1) for i, task in enumerate(tasks) if 'text' in task])
                markup.add(u"Finish all", u"Cancel")
                message = u"{0} What task is done?".format(emoji_right_arrow)
            else:
                message = u"{0} Please, choose list.".format(emoji_right_arrow)
                todos = self._all_lists()
                markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                markup.add(*[u"{0} ({1})".format(l, len(v)) for l,v in todos.iteritems()])
                markup.add('Cancel')
        return message, markup

    def done1(self):
        if self.update['text'] == u'Cancel':
            markup = markups.initial
            message = u"{}".format(emoji_check_mark)
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
        elif self.update['text'] == u'Finish all':
            user = self.users_db.find_one({"user_id": self.update['from']['id']})
            address = user["tmp{}".format(self.update["chat"]["id"])]
            if address == 'Group':
                address = ''
            for task in self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, 'to_id': address}):
                self._set_field(self.tasks_db, {"_id": task["_id"]}, {"finished": True, "end": time.time()})
            message = u"Removed {} list {}".format(user["tmp{}".format(self.update["chat"]["id"])], emoji_check_mark)
            markup = markups.initial
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
        else:
            todos = self._all_lists()
            user = self.users_db.find_one({"user_id": self.update['from']['id']})
            address = user["tmp{}".format(self.update["chat"]["id"])]
            tasks = sorted(todos[address], key=lambda task: task['created'], reverse=True)
            try:
                idx = int(self.update['text'].split('.')[0])
            except ValueError:
                message = u"No such task {}".format(emoji_sad)
                markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                markup.add(*[u"{1}. {0} ...".format(' '.join(task['text'].split()[:5]) + '...'
                                                    if task['text'].split() > 5
                                                    else task['text'], i+1) for i, task in enumerate(tasks) if 'text' in task])
                markup.add(u"Finish all", u"Cancel")
            else:
                if idx > len(tasks):
                    message = u"No such task {}".format(emoji_sad)
                    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                    markup.add(*[u"{1}. {0} ...".format(' '.join(task['text'].split()[:5]), i+1) for i, task in enumerate(tasks)])
                    markup.add(u"Finish all", u"Cancel")
                else:
                    self._set_field(self.tasks_db, {"_id": tasks[idx-1]["_id"]}, {"finished": True, "end": time.time()})
                    message = u"{}".format(emoji_check_mark)
                    markup = markups.initial
                    self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
        return message, markup

    def completed_initial(self):
        text = self.update['text']
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
        message = completed0.format('\n'.join(tasks)) if tasks else completed_er0
        return message, markups.initial

    def tutorial_initial(self):
        # message: write your first task. Press to_do
        # markup: initial
        # state: to tutorial0
        if self.update['chat']['id'] < 0:
            return u'Please, use personal chat with @Todobbot to take tutorial.', markups.initial
        message = u"First, let's create a task.\nPress /todo {0}".format(emoji_memo)
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(u'/todo {}'.format(emoji_memo), u'Cancel tutorial {}'.format(emoji_cross))
        self._change_state(self.update['from']['id'], self.update['chat']['id'], "bot_tutorial0")
        return message, markup

    def tutorial0(self):
        # message: (a) Write a task (b) Something was wrong. Press button to_do
        # markup: (a) Cancel tutorial (b) Initial
        # state: (a) tutorial1 (b) nothing
        if self.update['text'].strip().startswith(u'/todo'):
            message = u'{0} Now type "My first task"'.format(emoji_right_arrow)
            markup = markups.cancel_ttrl
            self._change_state(self.update['from']['id'], self.update['chat']['id'], "bot_tutorial1")
        elif self.update['text'].strip().startswith(u'Cancel tutorial'):
            self._change_state(self.update['from']['id'], self.update['chat']['id'], "bot_initial")
            markup = markups.initial
            message = u"{}".format(emoji_check_mark)
        else:
            message = u"Hmmm, something's wrong. Please, press /todo {}".format(emoji_memo)
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(u'/todo {}'.format(emoji_memo), u'Cancel tutorial {}'.format(emoji_cross))
        return message, markup

    def tutorial1(self):
        # message: (a) Great. Now let's create a named list (b) Do you want to write task
        # markup: (a) initial (b) initial
        # state: (a) tutorial2 (b) initial
        if not self.update['text'].strip().startswith('Cancel tutorial'):
            new_tsk = TDO.Task.from_json(self.update, self.update['text'], '')
            self.tasks_db.insert_one(new_tsk.__dict__)
            message = u"{0} Great! Now let's assign a task to someone.\nFirst, press /todo button".format(emoji_sparkles)
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(u'/todo {}'.format(emoji_memo), u'Cancel tutorial {}'.format(emoji_cross))
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_tutorial2')
        else:
            markup = markups.initial
            message = u"Tutorial stopped {}".format(emoji_no_entry)
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
        return message, markup

    def tutorial2(self):
        # message:
        # markup:
        # state:
        if self.update['text'].startswith(u'Cancel tutorial'):
            markup = markups.initial
            message = u"Tutorial stopped {}".format(emoji_no_entry)
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
        elif self.update['text'].startswith('/todo'):
            markup = markups.cancel_ttrl
            message = u'Now type "@{} Create first named list"'.format(self.update['from']['username']
                                                                      if 'username' in self.update['from']
                                                                      else self.update['from']['first_name'])
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_tutorial3')
        else:
            message = u"Hmmm, something's wrong. Please, press /todo {}".format(emoji_memo)
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(u'/todo {}'.format(emoji_memo), u'Cancel tutorial {}'.format(emoji_cross))
        return message, markup

    def tutorial3(self):
        if self.update['text'].startswith(u'Cancel tutorial'):
            markup = markups.initial
            message = u"Tutorial stopped {}".format(emoji_no_entry)
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
        elif self.update['text'].startswith('@'):
            words = self.update['text'].split()
            address = words[0][1:]
            new_tsk = TDO.Task.from_json(self.update, ' '.join(words[1:]), address)
            self.tasks_db.insert_one(new_tsk.__dict__)
            message = u"Great! {}\nLet's now see your tasks.\nPress /list {}".format(emoji_clap, emoji_clipboard)
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(u'/list {}'.format(emoji_clipboard), u'Cancel tutorial {}'.format(emoji_cross))
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_tutorial4')
        else:
            message = u"You task should begin with @ symbol.\nFor example: @Jack Buy milk."
            markup = markups.cancel_ttrl
        return message, markup

    def tutorial4(self):
        if self.update['text'].startswith(u'Cancel tutorial'):
            markup = markups.initial
            message = u"Tutorial stopped {}".format(emoji_no_entry)
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
        else:
            todos = [u"{} ({})".format(k, len(v)) for k,v in self._all_lists().iteritems()]
            todos.append(u"Cancel tutorial {}".format(emoji_cross))
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add(*todos)
            message = u"These are your Todo lists.\nSelect Group."
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_tutorial5')
        return message, markup

    def tutorial5(self):
        if self.update['text'].startswith(u'Cancel tutorial'):
            markup = markups.initial
            message = u"Tutorial stopped {}".format(emoji_no_entry)
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
        elif self.update['text'].startswith('Group'):
            cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": ''}).sort("created")
            tasks = [u"{0}. {1}".format(ix + 1, task['text']) for (ix, task) in enumerate(cursor) if 'text' in task]
            message = list0.format("Group") + '\n'.join(tasks) + \
                      u"\n\nNow, get our first task done.\nPress /done {}".format(emoji_hammer)
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(u'/done {}'.format(emoji_hammer), u'Cancel tutorial {}'.format(emoji_cross))
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_tutorial6')
        else:
            message = u"You should select Group list."
            todos = [u"{} ({})".format(k, len(v)) for k,v in self._all_lists().iteritems()]
            todos.append(u"Cancel tutorial {}".format(emoji_cross))
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add(*todos)
        return message, markup

    def tutorial6(self):
        if self.update['text'].startswith(u'Cancel tutorial'):
            markup = markups.initial
            message = u"Tutorial stopped {}".format(emoji_no_entry)
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
        elif self.update['text'].startswith('/done'):
            todos = [u"{} ({})".format(k, len(v)) for k,v in self._all_lists().iteritems()]
            todos.append(u"Cancel tutorial {}".format(emoji_cross))
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add(*todos)
            message = u"Then you should select Todo list. Select Group list."
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_tutorial7')
        else:
            message = u"Please, press /done {}".format(emoji_hammer)
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(u'/done {}'.format(emoji_hammer), u'Cancel tutorial {}'.format(emoji_cross))
        return message, markup

    def tutorial7(self):
        if self.update['text'].startswith(u'Cancel tutorial'):
            markup = markups.initial
            message = u"Tutorial stopped {}".format(emoji_no_entry)
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
        elif self.update['text'].startswith('Group'):
            cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": ''}).sort("created")
            tasks = [u"{0}. {1}".format(ix + 1, task['text']) for (ix, task) in enumerate(cursor) if 'text' in task]
            message = u"Choose the task you want to delete."
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            markup.add(*tasks)
            markup.add(u'Cancel tutorial {}'.format(emoji_cross))
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_tutorial8')
        else:
            message = u"You should select Group list."
            todos = [u"{} ({})".format(k, len(v)) for k,v in self._all_lists().iteritems()]
            todos.append(u"Cancel tutorial {}".format(emoji_cross))
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add(*todos)
        return message, markup

    def tutorial8(self):
        if self.update['text'].startswith(u'Cancel tutorial'):
            markup = markups.initial
            message = u"Tutorial stopped {}".format(emoji_no_entry)
            self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
        else:
            cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": ''}).sort("created")
            try:
                idx = int(self.update['text'].split('.')[0])
                for ix, task in enumerate(cursor):
                    if ix == idx - 1:
                        self.tasks_db.update({"_id": task['_id']},
                            {"$unset": {"$set": {"finished": True, "end": time.time()}}})
                        message = u"Great! You just removed the task! Now you're ready to use Todo Bot"
                        markup = markups.initial
                        self._change_state(self.update['from']['id'], self.update['chat']['id'], 'bot_initial')
                        break
                else:
                    cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": ''}).sort("created")
                    tasks = [u"{0}. {1}".format(ix + 1, task['text']) for (ix, task) in enumerate(cursor) if 'text' in task]
                    message = u"No such task. Choose from the list."
                    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
                    markup.add(*tasks)
                    markup.add(u'Cancel tutorial {}'.format(emoji_cross))

            except ValueError:
                cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": ''}).sort("created")
                tasks = [u"{0}. {1}".format(ix + 1, task['text']) for (ix, task) in enumerate(cursor) if 'text' in task]
                message = u"Ahh? What task?"
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
                markup.add(*tasks)
                markup.add(u'Cancel tutorial {}'.format(emoji_cross))
        return message, markup

    # TODO Remove all command as ambiguous
    def all_initial(self):
        todos = self._all_lists()
        return u"\n".join([u"{}. {} ({})".format(i+1, k, len(v)) for (i,(k,v)) in enumerate(todos.iteritems())]), None

    def _change_state(self, user_id, chat_id, state):
        self.users_db.update({"user_id": user_id}, {"$set": {'state:{}'.format(chat_id): state}})

    def _set_field(self, collection, record, field):
        collection.update(record, {"$set": field})

    def execute(self):
        mm = None, None

        user = self.users_db.find_one({"user_id": self.update['from']['id']})

        try:
            state = user['state:{}'.format(self.update['chat']['id'])]
        except KeyError:
            state = 'bot_initial'
            self._change_state(self.update['from']['id'], self.update['chat']['id'], state)

        print 'Started with state:', state

        command = TDO.Update.get_command(self.update)
        if state == 'bot_initial':
            if command in self.commands:
                if command in ['todo', 'todo@todobbot', 't']:
                    mm  = self.todo_initial()
                elif command in ['list', 'list@todobbot', 'l']:
                    mm = self.list_initial()
                elif command in ['done', 'done@todobbot', 'd']:
                    mm = self.done_initial()
                elif command in ['all', 'all@todobbot', 'a']:
                    mm = self.all_initial()
                elif command in ['completed', 'completed@todobbot', 'c']:
                    mm = self.completed_initial()
                elif command in ['tutorial', 'tutorial@todobbot', 't']:
                    mm = self.tutorial_initial()
        elif state == 'bot_todo':
            mm = self.todo_respond()
        elif state == 'bot_list':
            mm = self.list_respond()
        elif state == 'bot_done0':
            mm = self.done0()
        elif state == 'bot_done1':
            mm = self.done1()
        elif state == 'bot_tutorial0':
            mm = self.tutorial0()
        elif state == 'bot_tutorial1':
            mm = self.tutorial1()
        elif state == 'bot_tutorial2':
            mm = self.tutorial2()
        elif state == 'bot_tutorial3':
            mm = self.tutorial3()
        elif state == 'bot_tutorial4':
            mm = self.tutorial4()
        elif state == 'bot_tutorial5':
            mm = self.tutorial5()
        elif state == 'bot_tutorial6':
            mm = self.tutorial6()
        elif state == 'bot_tutorial7':
            mm = self.tutorial7()
        elif state == 'bot_tutorial8':
            mm = self.tutorial8()
        return mm
