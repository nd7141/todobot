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
import re
from geopy import geocoders
from dateutil.parser import parse
import datetime


def find_in_list(lst, el):
    try:
        idx = lst.index(el)
    except ValueError:
        idx = -1
    return idx

def parse_date(s):
    try:
        return parse(s)
    except:
        return None

class ToDoBot(telebot.TeleBot, object):

    def __init__(self, token, owm_token, users_db, groups_db, tasks_db, text_db, reminder_db, geopy_user, botan_token):
        super(self.__class__, self).__init__(token)
        self.users_db = users_db
        self.groups_db = groups_db
        self.tasks_db = tasks_db
        self.text_db = text_db
        self.reminder_db = reminder_db
        self.owm = pyowm.OWM(owm_token)
        self.geopy_user = geopy_user
        self.botan_token = botan_token

        self.commands = ['todo', 't',
                         ]
        self.commands += map(lambda s: s + "@todobbot", self.commands)
        self.todo_name = u'New task {}'.format(emoji_plus)
        self.addons_name = u'Add-ons {}'.format(emoji_rocket)
        self.support_name = u'Support {}'.format(emoji_email)
        self.notify_name = u'Remind me {}'.format(emoji_hourglass)
        self.settings_name = u'Settings {}'.format(emoji_wrench)
        self.notifications_name = u'Notifications {}'.format(emoji_alarm)

        self.googlegeo = geocoders.GoogleV3()

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
                self.send_message(msg['chat']['id'], result, reply_markup=markup, reply_to_message_id=msg['message_id'])

    def set_update_listener(self):
        self.update_listener.append(self.listener)

    def set_update(self, update):
        self.update = update.update

    def _tasks_from(self, lst):
        return list(self.tasks_db.find({"chat_id": self.update['chat']['id'], 'to_id': lst, 'finished': False}))

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

    def _change_state(self, state):
        self.users_db.update({"user_id": self.update['from']['id']},
                             {"$set": {'state{}'.format(self.update['chat']['id']): state}})

    def _get_text(self, message_id):
        try:
            record = self.text_db.find_one({"message_id": message_id})
        except KeyError:
            record = {'text': ""}
        print 'record', record
        return record['text']

    def _all_lists(self):
        todos = dict()
        for task in self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False}).sort('created'):
            if 'message_id' in task:
                if task['to_id'] == '':
                    todos.setdefault('', []).append(task)
                else:
                    todos.setdefault(task['to_id'], []).append(task)
        return todos

    def _create_initial(self):
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.row(self.todo_name, self.addons_name)
        markup.row(self.notify_name, self.support_name)
        markup.row(self.notifications_name, self.settings_name)
        todos = self._all_lists()
        if '' in todos:
            markup.add(*[self._get_text(task['message_id']) for task in todos[''] if 'message_id' in task])
        lists = sorted([u"{} ({})".format(todo, len(todos[todo])) for todo in todos if todo], key=unicode.lower)
        l = 2
        for i in xrange(0, len(lists), l):
            markup.row(*lists[i:i+l])
        return markup

    # 0 menu
    def todo(self):
        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        if  float(user.get('expiry_date', 0)) < time.time(): # expired
            self._change_state('todo_write')
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add(u'Cancel')
            message = u'Please, write your task {} For example: Buy shoes.'.format(emoji_pencil)
        else:
            todos = self._all_lists()
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add(u'Create a new Todo list {}'.format(emoji_open_folder))
            i = 0
            for todo in todos:
                if todo:
                    i+= 1
                    markup.add(u"{}. {}".format(i, todo))
            markup.add(u'Cancel')
            message = u'Write task to Default list {} or Create a new one {}'.format(emoji_pencil, emoji_open_folder)
            self._change_state('todo_create_list')
        return message, markup

    # 1 menu
    def todo_create_list(self):
        todos = self._all_lists()
        if self.update['text'].startswith('Cancel'):
            markup = self._create_initial()
            message = u'Done {}'.format(emoji_boxcheck)
            self._change_state('initial')
        elif self.update['text'].startswith(u'Create a new Todo list'):
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add(u'Cancel')
            message = u'How do you call this list?'
            self._change_state('todo_write_list')
        else:
            print self.update['text']
            idx = self.update['text'].find('.')
            lst = self.update['text'][idx+2:]
            print 'lst', lst
            if idx > 0 and lst in todos:
                message = u'Please, write your task {} For example: Buy shoes.'.format(emoji_pencil)
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                markup.add('Cancel')
                self._change_state('todo_write')
                self.users_db.update({"user_id": self.update['from']['id']},
                    {"$set": {u"tmp{}".format(self.update['chat']['id']): lst}})
            else:
                message, markup = self.todo_write()
                self._change_state('initial')
        return message, markup

    # 2 menu
    def todo_write_list(self):
        if self.update['text'] == 'Cancel':
            self._change_state('initial')
            markup = self._create_initial()
            message = u'Done {}'.format(emoji_boxcheck)
        else:
            message = u'Write task to {} list {}'.format(self.update['text'], emoji_pencil)
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            self.users_db.update({"user_id": self.update['from']['id']},
                {"$set": {u"tmp{}".format(self.update['chat']['id']): self.update['text']}})
            self._change_state('todo_write')
        return message, markup

    # 3 menu
    def todo_write(self):
        if self.update['text'].strip() == u'Cancel':
            message = u"Cancelled writing"
        else:
            if self.update['text'] in [self.todo_name, self.addons_name]:
                message = u'Cannot write task: {}'.format(self.update['text'])
            else:
                user = self.users_db.find_one({"user_id": self.update['from']['id']})
                to_id = ''
                if u"tmp{}".format(self.update['chat']['id']) in user:
                    to_id = user[u"tmp{}".format(self.update['chat']['id'])]
                    self.users_db.update({"user_id": self.update['from']['id']},
                        {"$unset": {u"tmp{}".format(self.update['chat']['id']): ''}})
                print 'to_id', to_id

                new_tsk = TDO.Task.from_json(self.update, to_id)
                new_txt = TDO.Text.from_json(self.update)
                self.tasks_db.insert_one(new_tsk.__dict__)
                self.text_db.insert_one(new_txt.__dict__)
                message = u'Wrote new task {}'.format(emoji_floppy)
        markup = self._create_initial()
        self._change_state('initial')
        return message, markup

    def todo_choose_list(self):
        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        if float(user['expire_date']) > time.time(): # expired
            return self.todo()
        message = u'Not implemented'
        markup = self._create_initial()
        return message, markup

    def remove(self, text, lst):
        todos = self._all_lists()
        tasks = todos[lst]
        for task in tasks:
            if self._get_text(task['message_id']) == text:
                self.tasks_db.update({"_id": task["_id"]},
                    {"$set": {"finished": True, "end": time.time()}})
                message = u'Finished "{}" {}'.format(self.update['text'], emoji_star)
                break
        else:
            message = u'No task'
        markup = self._create_initial()
        return message, markup

    def remove_from_list(self, lst):
        todos = self._all_lists()
        tasks = [self._get_text(task['message_id']) for task in todos[lst] if 'message_id' in task]
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, selective=True)
        markup.add(*tasks)
        markup.add(u'Cancel')
        message = u'Choose task'
        self._change_state('remove_list_task')
        self.users_db.update({"user_id": self.update['from']['id']},
                             {"$set": {u"tmp2{}".format(self.update['chat']['id']): lst}})
        return message, markup

    def remove_list_task(self):
        if self.update['text'] == u'Cancel':
            message = u'Done {}'.format(emoji_boxcheck)
        else:
            todos = self._all_lists()
            user = self.users_db.find_one({"user_id": self.update['from']['id']})
            lst = user.get(u"tmp2{}".format(self.update['chat']['id']), 'NONE')
            tasks = todos[lst]
            for task in tasks:
                if 'message_id' in task and self._get_text(task['message_id']) == self.update['text']:
                    self.tasks_db.update({"_id": task["_id"]},
                        {"$set": {"finished": True, "end": time.time()}})
                    message = u'Finished "{}" {}'.format(self.update['text'], emoji_star)
                    break
            else:
                message= u'No such task'

        self._change_state('initial')
        markup = self._create_initial()
        return message, markup


    def addons(self):
        message = u'Choose add-on {}'.format(emoji_bomb)
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, selective=True)
        markup.add(u'Current {}'.format(emoji_clipboard), u'Finished {}'.format(emoji_square), u'Cancel {}'.format(emoji_return_arrow))
        self._change_state('addons_choose')
        return message, markup

    def addons_choose(self):
        text = self.update['text']
        if text.startswith('Current'):
            todos = self._all_lists()
            message = '\n'.join([self._get_text(t['message_id']) for t in todos[''] if 'message_id' in t])
        elif text.startswith('Finished'):
            cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": True, "to_id": ''}).sort("end", -1)
            message = '\n'.join([u'{} ({})'.format(self._get_text(task['message_id']), TDO.Update.strtime(task['end']))
                                  for task in cursor if 'message_id' in task])
        elif text.startswith('Cancel'):
            message = u'Choose action'
        else:
            message = u'Unrecognized add-on.\n'
        markup = self._create_initial()
        self._change_state('initial')
        return message, markup

    def support(self):
        message = u'You can email us at support@thetodobot.com\n or chat with us at thetodobot.com {}'.format(emoji_wink)
        markup = self._create_initial()
        return message, markup

    # notify 0
    def notify(self):
        message = u"When to remind?"
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, selective=True)
        markup.add(*[u'1 hour', u'3 Hours', u'1 day', u'Specific time', u'Cancel'])
        self._change_state('notify_select')
        return message, markup

    # notify 1
    def notify_select(self):
        message = None
        markup = None
        options = [u'1 hour', u'3 Hours', u'1 day', u'Specific time', u'Cancel']
        idx = find_in_list(options, self.update['text'])
        if idx in [0,1,2,4]:
            message = u'Done {}'.format(emoji_boxcheck)
            markup = self._create_initial()
            self._change_state('initial')
            if idx == 0:
                self.reminder_db.insert_one({"chat_id": self.update['chat']['id'],
                                       "time_at": time.time() + 3600})
            elif idx == 1:
                self.reminder_db.insert_one({"chat_id": self.update['chat']['id'],
                                       "time_at": time.time() + 3600*3})
            elif idx == 2:
                self.reminder_db.insert_one({"chat_id": self.update['chat']['id'],
                                       "time_at": time.time() + 3600*24})
        elif idx == 3:
            user = self.users_db.find_one({"user_id": self.update['from']['id']})
            if not ('city' in user and user['city']):
                message = u"First, let's configure your city. Type the name of your city."
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                markup.add(u'Cancel')
                self._change_state('notify_choose_city')
            else:
                message, markup = self.notify_write_time()

        return message, markup

    # notify 2
    def notify_choose_city(self):
        if self.update['text'] == u'Cancel':
            message = u'Done {}'.format(emoji_boxcheck)
            markup = self._create_initial()
            self._change_state('initial')
        else:
            try:
                data = self.googlegeo.geocode(self.update['text'])
            except:
                message = u'Was unable to configure your city'
                markup = self._create_initial()
                self._change_state('initial')
            else:
                if data:
                    place, (lat, lng) = data
                    self.users_db.update({"user_id": self.update['from']['id']},
                        {"$set": {'city': place, 'lat': lat, 'lng': lng}})
                    message, markup = self.notify_write_time()
                else:
                    message = u'Please, type your city again.'
                    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                    markup.add(u'Cancel')
        return message, markup

    # notify 3
    def notify_write_time(self):
        message = u'Write your time\n Example: Saturday 7:00\n 12 Aug 12:30'
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
        markup.add(u'Cancel')
        self._change_state('notify_get_time')

        return message, markup

    # notify 4
    def notify_get_time(self):
        if self.update['text'] == u'Cancel':
            message = u'Done {}'.format(emoji_boxcheck)
            markup = self._create_initial()
            self._change_state('initial')
        else:
            date = parse_date(self.update['text'])
            if date is not None:
                user = self.users_db.find_one({"user_id": self.update['from']['id']})
                tz = self.googlegeo.timezone((user['lat'], user['lng']))
                offset = int(date.replace(tzinfo=tz).strftime('%s'))
                if offset > time.time():
                    message = u'Done {}'.format(emoji_boxcheck)
                    markup = self._create_initial()
                    self._change_state('initial')
                    self.reminder_db.insert_one({"chat_id": self.update['chat']['id'],
                                       "time_at": offset})
                else:
                    message = u'The date is passed. Please type again.'
                    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                    markup.add(u'Cancel')
            else:
                message = u'The date is not correct.\n Example: Saturday 7:00\n 12 Aug 12:30'
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                markup.add(u'Cancel')
        return message, markup

    # notifications 0
    def notifications(self):
        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        if 'lat' not in user:
            message = u"Let's first set up your city."
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add(u'Cancel')
            self._change_state('notifications_choose_city')
        else:
            message = u'We will send you an update daily. What time do you want?\nExample: 7:00'
            markup = telebot.types.ReplyKeyboardMarkup(selective=True, resize_keyboard=True, row_width=1)
            markup.add(u'Turn off', u'Cancel')
            self._change_state('notifications_choose_time')
        return message, markup

    # notifications 1
    def notifications_choose_city(self):
        if self.update['text'] == u'Cancel':
            message = u'Done {}'.format(emoji_boxcheck)
            markup = self._create_initial()
            self._change_state('initial')
        else:
            data = self.googlegeo.geocode(self.update['text'])
            if data:
                place, (lat, lng) = data
                self.users_db.update({"user_id": self.update['from']['id']},
                    {"$set": {'city': place, 'lat': lat, 'lng': lng}})
                message = u'City: {}'.format(place)
                message += u'\nWe will send you an update daily. What time do you want?\nExample: 7:00'
                markup = telebot.types.ReplyKeyboardMarkup(selective=True, resize_keyboard=True, row_width=1)
                markup.add(u'Turn off', u'Cancel')
                self._change_state('notifications_choose_time')
            else:
                message = u"Do not know this city. Type again."
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                markup.add(u'Cancel')
        return message, markup

    # notifications 2
    def notifications_choose_time(self):
        if self.update['text'] == u'Cancel':
            message = u'Done {}'.format(emoji_boxcheck)
            markup = self._create_initial()
            self._change_state('initial')
        elif self.update['text'] == u'Turn off':
            self.reminder_db.remove({"chat_id": int(self.update['chat']['id']), "repetitive": True})
            message = u'No more notifications'
            markup = self._create_initial()
            self._change_state('initial')
        else:
            date = parse_date(self.update['text'])
            if date is not None:
                user = self.users_db.find_one({"user_id": self.update['from']['id']})
                tz = self.googlegeo.timezone((user['lat'], user['lng']))
                date = date.replace(tzinfo=tz)
                now = datetime.datetime.now().replace(tzinfo=tz)
                if date < now:
                    offset = float(now.replace(day=now.day+1, hour=date.hour, minute=date.minute, second=date.second).strftime("%s"))
                else:
                    offset = float(now.replace(hour=date.hour, minute=date.minute, second=date.second).strftime("%s"))

                self.reminder_db.insert_one({"chat_id": self.update['chat']['id'],
                                             "time_at": offset, "repetitive": True})
                message = u'Set a notification at {:02d}:{:02d} {}'.format(date.hour, date.minute, emoji_wink)
                markup = self._create_initial()
                self._change_state('initial')
            else:
                message = u'The date is not correct.\n Example: Saturday 7:00\n 12 Aug 12:30'
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                markup.add(u'Cancel')
        return message, markup

    # settings 0
    def settings(self):
        message = u'Choose'
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True, row_width=1)
        markup.add(u'City {}'.format(emoji_globe), u'Cancel')
        self._change_state('settings_select')
        return message, markup

    # settings 1
    def settings_select(self):
        message, markup = None, None
        if self.update['text'] == u'Cancel':
            message = u'Done {}'.format(emoji_boxcheck)
            markup = self._create_initial()
            self._change_state('initial')
        elif self.update['text'] == u'City {}'.format(emoji_globe):
            user = self.users_db.find_one({'user_id': self.update['from']['id']})
            message = u''
            if 'city' in user:
                message = u"Your current city: {}\n".format(user['city'])
            message += u"Type the name of your city."
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add(u'Cancel')
            self._change_state('settings_choose_city')
        return message, markup

    # settings 2
    def settings_choose_city(self):
        if self.update['text'] == u'Cancel':
            message = u'Done {}'.format(emoji_boxcheck)
            markup = self._create_initial()
            self._change_state('initial')
        else:
            data = self.googlegeo.geocode(self.update['text'])
            if data:
                place, (lat, lng) = data
                self.users_db.update({"user_id": self.update['from']['id']},
                    {"$set": {'city': place, 'lat': lat, 'lng': lng}})
                message = u'City: {}'.format(place)
                markup = self._create_initial()
                self._change_state('initial')
            else:
                message = u"Do not know this city. Type again."
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                markup.add(u'Cancel')
        return message, markup

    def execute(self):
        mm = None, None

        print 'chat id', self.update['chat']['id']

        # Write new user, group into database
        user = self.write_user()
        self.write_group()

        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        state = user.get('state{}'.format(self.update['chat']['id']), 'initial')

        print
        print 'Started with state', state

        if 'text' not in self.update:
            return mm

        if state == 'initial':
            text= self.update['text'].strip()
            if text == 'Cancel':
                message  = u'Please, write your task {} For example: Buy shoes.'.format(emoji_pencil)
                markup = self._create_initial()
                return message, markup
            if text == self.todo_name:
                mm = self.todo()
            elif text == self.addons_name:
                mm = self.addons()
            elif text == self.support_name:
                mm = self.support()
            elif text == self.notify_name:
                mm = self.notify()
            elif text == self.settings_name:
                mm = self.settings()
            elif text == self.notifications_name:
                mm = self.notifications()
            else:
                s = self.update['text']
                todos = self._all_lists()
                texts = []
                if '' in todos:
                    texts = [self._get_text(task['message_id']) for task in todos[''] if 'message_id' in task]
                idx = s.find('(')
                if s in texts:
                    mm = self.remove(s, '')
                elif s[:idx-1] in todos:
                    mm = self.remove_from_list(s[:idx-1])
        elif state == 'todo_write':
            mm = self.todo_write()
        elif state == 'todo_create_list':
            mm = self.todo_create_list()
        elif state == 'todo_write_list':
            mm = self.todo_write_list()
        elif state == 'addons_choose':
            mm = self.addons_choose()
        elif state == 'todo_choose_list':
            mm = self.todo_choose_list()
        elif state == 'remove_list_task':
            mm = self.remove_list_task()
        elif state == 'notify_select':
            mm = self.notify_select()
        elif state == 'notify_choose_city':
            mm = self.notify_choose_city()
        elif state == 'notify_get_time':
            mm = self.notify_get_time()
        elif state == 'settings_select':
            mm = self.settings_select()
        elif state == 'settings_choose_city':
            mm = self.settings_choose_city()
        elif state == 'notifications_choose_city':
            mm = self.notifications_choose_city()
        elif state == 'notifications_choose_time':
            mm = self.notifications_choose_time()
        else:
            mm = u'Return to initial menu {}'.format(emoji_return_arrow), self._create_initial()
            self._change_state('initial')

        return mm