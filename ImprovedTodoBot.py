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
from string import ascii_letters, digits
import random
import base64
import os

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

    def __init__(self, token, owm_token, users_db, groups_db, tasks_db, public_tasks_db, reminder_db, geopy_user, botan_token):
        super(self.__class__, self).__init__(token)
        self.users_db = users_db
        self.groups_db = groups_db
        self.tasks_db = tasks_db
        self.public_tasks_db = public_tasks_db
        self.reminder_db = reminder_db
        self.owm = pyowm.OWM(owm_token)
        self.geopy_user = geopy_user
        self.botan_token = botan_token

        self.commands = ['todo', 't',
                         ]
        self.commands += map(lambda s: s + "@todobbot", self.commands)
        self.todo_name = u'New task {}'.format(emoji_plus)
        self.addons_name = u'More {}'.format(emoji_rocket)
        self.support_name = u'Support {}'.format(emoji_email)
        self.notify_name = u'Remind me {}'.format(emoji_hourglass)
        self.settings_name = u'Settings {}'.format(emoji_wrench)
        self.notifications_name = u'Notifications {}'.format(emoji_alarm)
        self.current_tasks_name = u'All tasks {}'.format(emoji_memo)
        self.finished_tasks_name = u'Finished tasks {}'.format(emoji_check_mark)
        self.get_premium_name = u'Get Premium {}'.format(emoji_fire)

        self.commands_name = [self.todo_name, self.addons_name, self.notifications_name, self.notify_name, self.settings_name,
                         self.support_name]

        me = 80639335
        testdevgroup = -28297621
        yura_pekov = 1040729
        yura_oparin = 93518804
        founding_group = -27571522
        self.cools = [me]

        self.googlegeo = geocoders.GoogleV3()

    def get_update(self):
        new_messages = []
        try:
            updates = telebot.apihelper.get_updates(self.token, offset=(self.last_update_id + 1), timeout=20)
        except Exception as e:
            print e
            print("TeleBot: Exception occurred.")
            try:
                if os.path.getsize('log.txt') > 10*1024*1024: # 10mb
                    os.remove('log.txt')
            except:
                pass
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
            update = TDO.Update(msg)
            self.set_update(update)
            new_messages = self.execute()
            for kwargs in new_messages:
                if isinstance(kwargs, str):
                    print 'kwargs:', kwargs
                else:
                    print 'Text:', kwargs['text']
                try:
                    print 'Keyboard:', kwargs['reply_markup'].keyboard
                except (AttributeError, KeyError):
                    print 'Keyboard:', None
                print
                if kwargs['text']:
                    kwargs.setdefault('chat_id', msg['chat']['id'])
                    kwargs.setdefault('reply_to_message_id', msg['message_id'])
                    self.send_message(**kwargs)

    def set_update_listener(self):
        self.update_listener.append(self.listener)

    def set_update(self, update):
        self.update = update.update

    def _tasks_from(self, lst):
        return list(self.tasks_db.find({"chat_id": self.update['chat']['id'], 'to_id': lst, 'finished': False}))

    def premium_message(self):
        message = u" {} With premium account you can create named lists, set notifications, access new features first, and much more.\n".format(emoji_right_arrow)
        message += u" {}To get a Premium account go to {}\n".format(emoji_right_arrow, self._generate_link())
        message += u"{} Copy the code and paste in the chat with bot!\n".format(emoji_right_arrow)
        message += u" {} Contact us in case of trouble: support@thetodobot.com".format(emoji_email)
        return message

    def write_user(self):
        user = self.users_db.find_one({"user_id": self.update["from"]["id"]})
        if not user:
            user_json = TDO.User.from_json(self.update['from'], self.update['date'])
            self.users_db.insert_one(user_json.__dict__)
            # give free days of Premium
            self.users_db.update({"user_id": self.update['from']['id']},
                    {"$set": {'expiry_date': time.time() + 86400*7}})
            now = datetime.datetime.now() + datetime.timedelta(days=1)
            offset = float(now.strftime("%s"))
            self.reminder_db.insert_one({"chat_id": self.update['chat']['id'],
                                       "remind_at": offset, "repetitive": True,
                                       "from_id": self.update['from']['id']})
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

    def _all_lists(self):
        todos = dict()
        for task in self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": False}).sort('created'):
            if 'message_id' in task and 'text' in task:
                if task['to_id'] == '':
                    todos.setdefault('', []).append(task)
                else:
                    todos.setdefault(task['to_id'], []).append(task)
        return todos

    def _check_if_premium(self):
        if 'title' in self.update: # group
            group = self.groups_db.find_one({"chat_id": self.update['chat']['id']})
            if group:
                participants = group.get('participants', [])
                if participants:
                    for p in participants:
                        user = self.users_db.find_one({"user_id": p})
                        if float(user.get('expiry_date', 0)) > time.time():
                            return True
                    return False
        else:
            user = self.users_db.find_one({"user_id": self.update['from']['id']})
            if float(user.get('expiry_date', 0)) > time.time():
                return True
            return False

    def _create_initial(self):
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.row(self.todo_name, self.addons_name)
        if not self._check_if_premium():
            markup.row(self.get_premium_name)
        todos = self._all_lists()
        markup.add(*[task['text'] for task in todos.get('', []) if 'text' in task])
        lists = sorted([u"{} ({}) {}".format(todo, len(todos[todo]), emoji_memo) for todo in todos if todo], key=unicode.lower)
        l = 2
        for i in xrange(0, len(lists), l):
            markup.row(*lists[i:i+l])
        return markup

    def _generate_link(self):
        base_url = u'thetodobot.com/{}'
        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        link_code = user.get("link_code", "")
        if not link_code:
            link_code = base64.b64encode(os.urandom(6), "-_")
            payment_code = base64.b64encode(link_code).replace('=', '')
            self.users_db.update({"user_id": self.update['from']['id']},
                {"$set": {"link_code": link_code, "payment_code": payment_code}})
        link = base_url.format(link_code)
        return link

    # 0 menu
    def todo(self):
        todos = self._all_lists()
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
        markup.add(u'Create a new Todo list {}'.format(emoji_open_folder))
        i = 0
        # add lists as buttons
        for todo in todos:
            if todo:
                i+= 1
                markup.add(u"{}. {}".format(i, todo))
        markup.add(u'Cancel')
        message = u'Write task to Default list {} or Create a new one {}'.format(emoji_pencil, emoji_open_folder)
        self._change_state('todo_create_list')
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    # 1 menu
    def todo_create_list(self):
        todos = self._all_lists()
        if self.update['text'].startswith('Cancel'):
            markup = self._create_initial()
            message = u'Done {}'.format(emoji_boxcheck)
            self._change_state('initial')
        elif self.update['text'].startswith(u'Create a new Todo list'):
            user = self.users_db.find_one({"user_id": self.update['from']['id']})
            if float(user.get('expiry_date', 0)) < time.time(): # expired:
                message = self.premium_message()
                markup = self._create_initial()
                self._change_state('initial')
            else:
                message = u'How do you call this list?'
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                markup.add(u'Cancel')
                self._change_state('todo_write_list')
        else:
            idx = self.update['text'].find('.')
            lst = self.update['text'][idx+2:]
            if idx > 0 and lst in todos:
                message = u'Please, write your task {} For example: Buy shoes.'.format(emoji_pencil)
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                markup.add('Cancel')
                self._change_state('todo_write')
                self.users_db.update({"user_id": self.update['from']['id']},
                    {"$set": {u"tmp{}".format(self.update['chat']['id']): lst}})
            else:
                kw = self.todo_write()
                message = kw['text']
                markup = kw['reply_markup']
                self._change_state('initial')
        kwargs = {"text": message, "reply_markup": markup, "disable_web_page_preview": True}
        return kwargs

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
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    # 3 menu
    def todo_write(self):
        if self.update['text'].strip() == u'Cancel':
            message = u"Cancelled writing"
        else:
            if self.update['text'] in self.commands_name:
                message = u'Cannot write task: {}'.format(self.update['text'])
            else:
                user = self.users_db.find_one({"user_id": self.update['from']['id']})
                to_id = ''
                if u"tmp{}".format(self.update['chat']['id']) in user:
                    to_id = user[u"tmp{}".format(self.update['chat']['id'])]
                    self.users_db.update({"user_id": self.update['from']['id']},
                        {"$unset": {u"tmp{}".format(self.update['chat']['id']): ''}})

                tasks = self.update['text'].split(os.linesep)
                for t in tasks:
                    if t.strip():
                        public_task = TDO.PublicTask.from_json(self.update, to_id)
                        self.public_tasks_db.insert_one(public_task.__dict__)
                        task = TDO.Task.from_json(self.update, t, to_id)
                        self.tasks_db.insert_one(task.__dict__)

                message = u'Updated list {}'.format(emoji_floppy)
        markup = self._create_initial()
        self._change_state('initial')
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    def todo_choose_list(self):
        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        if float(user['expire_date']) > time.time(): # expired
            return self.todo()
        message = u'Not implemented'
        markup = self._create_initial()
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    def remove(self, text, lst):
        todos = self._all_lists()
        tasks = todos[lst]
        message, markup = '', None
        for task in tasks:
            if task['text'] == text:
                self.tasks_db.update({"_id": task["_id"]},
                    {"$set": {"finished": True, "end": time.time()}})
                self.public_tasks_db.update({"message_id": task["message_id"]},
                    {"$set": {"finished": True, "end": time.time()}})
                message = u'Finished "{}" {}'.format(self.update['text'], emoji_star)
                markup = self._create_initial()
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    def remove_from_list(self, lst):
        todos = self._all_lists()
        tasks = [task['text'] for task in todos[lst] if 'text' in task]
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, selective=True)
        markup.add(*tasks)
        markup.add(u'Cancel')
        message = u'Choose task'
        self._change_state('remove_list_task')
        self.users_db.update({"user_id": self.update['from']['id']},
                             {"$set": {u"tmp2{}".format(self.update['chat']['id']): lst}})
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    def remove_list_task(self):
        if self.update['text'] == u'Cancel':
            message = u'Done {}'.format(emoji_boxcheck)
        else:
            todos = self._all_lists()
            user = self.users_db.find_one({"user_id": self.update['from']['id']})
            lst = user.get(u"tmp2{}".format(self.update['chat']['id']), '')
            tasks = todos[lst]
            message = ''
            for task in tasks:
                if task['text'] == self.update['text']:
                    self.tasks_db.update({"_id": task["_id"]},
                        {"$set": {"finished": True, "end": time.time()}})
                    self.public_tasks_db.update({"message_id": task["message_id"]},
                        {"$set": {"finished": True, "end": time.time()}})
                    message = u'Finished "{}" {}'.format(self.update['text'], emoji_star)
            if not message:
                message = u'No such task'

        self._change_state('initial')
        markup = self._create_initial()
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs


    def addons(self):
        message = u'Choose add-on {}'.format(emoji_bomb)
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, selective=True)
        markup.row(self.notify_name, self.support_name)
        markup.row(self.notifications_name, self.settings_name)
        markup.row(self.current_tasks_name, self.finished_tasks_name)
        markup.row(self.get_premium_name)
        markup.row(u'Cancel')
        self._change_state('addons_choose')
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    def addons_choose(self):
        markup = self._create_initial()
        self._change_state('initial')
        if self.update['text'] == u'Cancel':
            message = u'Done {}'.format(emoji_boxcheck)
            return {"text": message, "reply_markup": markup}
        elif self.update['text'] == self.current_tasks_name:
            todos = self._all_lists()
            premessage = u'All tasks:\n'
            texts = [task['text'] for lst in todos for task in todos[lst] if 'text' in task]
            message = premessage + u'\n'.join(texts)
            return {"text": message, "reply_markup": markup}
        elif self.update['text'] == self.finished_tasks_name:
            cursor = self.tasks_db.find({"chat_id": self.update['chat']['id'], "finished": True, "to_id": ''}).sort("end", -1)
            texts = [(task['text'], task['end']) for task in cursor if 'text' in task and 'end' in task]
            premessage = u'Finished tasks:\n'
            message = premessage + u"\n".join([u"{} ({})".format(t, e) for (t,e) in texts])
            return {"text": message, "reply_markup": markup}
        elif self.update['text'] == self.notify_name:
            return self.notify()
        elif self.update['text'] == self.support_name:
            return self.support()
        elif self.update['text'] == self.notifications_name:
            return self.notifications()
        elif self.update['text'] == self.settings_name:
            return self.settings()
        elif self.update['text'] == self.get_premium_name:
            return self.get_premium()
        else:
            return {"text": ''}

    def get_premium(self):
        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        if float(user.get('expiry_date', 0)) < time.time(): # expired:
            message = self.premium_message()
            markup = self._create_initial()
            self._change_state('initial')
            kwargs = {"text": message, "reply_markup": markup}
        else:
            message = u"You already have a Premium account! {} You are awesome!!!".format(emoji_fire)
            kwargs = {"text": message}
        return kwargs

    def support(self):
        message = u'Support: To give feedback or report a bug, send an email to support@thetodobot.com or chat directly with my creators on thetodobot.com'.format(emoji_wink)
        markup = self._create_initial()
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    # notify 0
    def notify(self):
        message = u"When to remind?"
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, selective=True)
        markup.add(*[u'1 hour', u'3 Hours', u'1 day', u'Your time', u'Cancel'])
        self._change_state('notify_select')
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    # notify 1
    def notify_select(self):
        if self.update['text'] == u'Cancel':
            message = u'Done {}'.format(emoji_boxcheck)
            markup = self._create_initial()
            self._change_state('initial')
        else:
            message = None
            markup = None
            options = [u'1 hour', u'3 Hours', u'1 day', u'Your time', u'Cancel']
            idx = find_in_list(options, self.update['text'])
            if idx in [0,1,2,4]: # not your time
                markup = self._create_initial()
                self._change_state('initial')
                if idx == 0:
                    self.reminder_db.insert_one({"chat_id": self.update['chat']['id'],
                                           "remind_at": time.time() + 3600,
                                           "from_id": self.update['from']['id']})
                    message = u'Set a notification at {} {}'.format(datetime.datetime.fromtimestamp(time.time() + 3600).strftime('%-H:%M'),
                                                                    emoji_wink)
                elif idx == 1:
                    self.reminder_db.insert_one({"chat_id": self.update['chat']['id'],
                                           "remind_at": time.time() + 3600*3,
                                           "from_id": self.update['from']['id']})
                    message = u'Set a notification at {} {}'.format(datetime.datetime.fromtimestamp(time.time() + 3600*3).strftime('%-H:%M'),
                                                                    emoji_wink)
                elif idx == 2:
                    self.reminder_db.insert_one({"chat_id": self.update['chat']['id'],
                                           "remind_at": time.time() + 3600*24,
                                           "from_id": self.update['from']['id']})
                    message = u'Set a notification at {} {}'.format(datetime.datetime.fromtimestamp(time.time() + 3600*24).strftime('%-H:%M'),
                                                                    emoji_wink)
            elif idx == 3:
                user = self.users_db.find_one({"user_id": self.update['from']['id']})
                if not ('city' in user and user['city']):
                    message = u"First, let's configure your city. Type the name of your city."
                    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                    markup.add(u'Cancel')
                    self._change_state('notify_choose_city')
                else:
                    kwargs = self.notify_write_time()
                    message, markup = kwargs['text'], kwargs['reply_markup']

        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

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
                    kwargs = self.notify_write_time()
                    message, markup = kwargs['text'], kwargs['reply_markup']
                else:
                    message = u'Please, type your city again.'
                    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                    markup.add(u'Cancel')
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    # notify 3
    def notify_write_time(self):
        message = u'Write your time\n Example: Saturday 7:00\n12 Aug 12:30\n 7 pm'
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
        markup.add(u'Cancel')
        self._change_state('notify_get_time')

        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

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
                print offset, time.time()
                if offset > time.time():
                    message = u'Set a notification at {} {}'.format(datetime.datetime.fromtimestamp(offset).strftime('%-H:%M'),
                                                                    emoji_wink)
                    markup = self._create_initial()
                    self._change_state('initial')
                    self.reminder_db.insert_one({"chat_id": self.update['chat']['id'],
                                       "remind_at": offset,
                                       "from_id": self.update['from']['id']})
                else:
                    now = datetime.datetime.now() + datetime.timedelta(days=1)
                    message = u'Specify time in the future. For example, {} {}.'.format(now.strftime("%-d"), date.strftime("%-H%P"))
                    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                    markup.add(u'Cancel')
            else:
                message = u'The date is not correct.\n Example: Saturday 7:00\n 12 Aug 12:30'
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                markup.add(u'Cancel')
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    def _to_hours(self, time):
        return datetime.datetime.fromtimestamp(int(time)).strftime('%H:%M')

    # notifications 0
    def notifications(self):
        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        if 'lat' not in user:
            message = u"Let's first set up your city {}".format(emoji_globe)
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            for reminder in self.reminder_db.find({"chat_id": self.update['chat']['id']}):
                markup.add(self._to_hours(reminder['remind_at']))
            markup.add(u'Cancel')
            self._change_state('notifications_choose_city')
        else:
            message = u'We will send you an update daily. What time do you want?\nExample: 7:00'
            markup = telebot.types.ReplyKeyboardMarkup(selective=True, resize_keyboard=True, row_width=1)
            for reminder in self.reminder_db.find({"chat_id": self.update['chat']['id']}):
                markup.add(self._to_hours(reminder['remind_at']))
            markup.add(u'Cancel')
            self._change_state('notifications_choose_time')
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

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
                markup.add(u'Cancel')
                self._change_state('notifications_choose_time')
            else:
                message = u"Do not know this city. Type again."
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                markup.add(u'Cancel')
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    # notifications 2
    def notifications_choose_time(self):
        if self.update['text'] == u'Cancel':
            message = u'Done {}'.format(emoji_boxcheck)
            markup = self._create_initial()
            self._change_state('initial')
        else:
            date = parse_date(self.update['text'])
            if date is not None:
                for r in self.reminder_db.find({"chat_id": self.update['chat']['id']}):
                    d = datetime.datetime.fromtimestamp(int(r['remind_at']))
                    if d.hour == date.hour and d.minute == date.minute:
                        self.reminder_db.remove(r)
                        message = u'Removed notification at {}'.format(date.strftime("%-H:%M"))
                        markup = self._create_initial()
                        self._change_state('initial')
                        break
                else:
                    user = self.users_db.find_one({"user_id": self.update['from']['id']})
                    # tz = self.googlegeo.timezone((user['lat'], user['lng']))
                    # date = date.replace(tzinfo=tz)
                    now = datetime.datetime.now()
                    if date < now:
                        date = date.replace(year=now.year, month=now.month, day=now.day)
                        date += datetime.timedelta(days=1)
                    offset = float(date.strftime("%s"))

                    self.reminder_db.insert_one({"chat_id": self.update['chat']['id'],
                                                 "remind_at": offset, "repetitive": True,
                                                 "from_id": self.update['from']['id']})
                    message = u'Set a notification at {} {}'.format(date.strftime("%-H:%M"), emoji_wink)
                    markup = self._create_initial()
                    self._change_state('initial')
            else:
                message = u'The date is not correct.\n Example: Saturday 7:00\n 12 Aug 12:30'
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
                markup.add(u'Cancel')
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    # settings 0
    def settings(self):
        message = u'Choose'
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True, row_width=1)
        markup.add(u'City {}'.format(emoji_globe), u'Cancel')
        self._change_state('settings_select')
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

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
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

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
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    def cancel_all(self):
        message  = u'Please, write your task {} For example: Buy shoes.'.format(emoji_pencil)
        markup = self._create_initial()
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    def invalid_code(self):
        message = u'Code is invalid'
        return {"text": message}

    def extend_expire(self, user):
        # extend expiration and increment count of subscription
        self.users_db.update({"user_id": user["user_id"]},
                {"$set": {'expiry_date': time.time() + 86400*30,
                          'sub_count': user.get('sub_count', 0) + 1,
                          "premium": True}})
        # change link and payment code
        link_code = base64.b64encode(os.urandom(6), "-_")
        payment_code = base64.b64encode(link_code).replace('=', '')
        self.users_db.update({"user_id": self.update['from']['id']},
            {"$set": {"link_code": link_code, "payment_code": payment_code}})
        # return message, markup
        message = u"You received Premium subscription for 30 days! {}\nYou're awesome!!!".format(emoji_thumb)
        markup = self._create_initial()
        self._change_state('initial')
        kwargs = {"text": message, "reply_markup": markup}
        messages = [kwargs]
        for cool in self.cools:
            messages.append({"chat_id": cool,
                             "text": u"User {} ({}) paid for subscription".format(user['first_name'], user['user_id']),
                             'reply_to_message_id': None})
        return messages

    def add_to_end(self, el, lst):
        if isinstance(el, list):
            lst.extend(el)
        else:
            lst.append(el)
        return lst

    def greetings(self):
        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        if float(user['created']) + 60 > time.time(): # was just created
            message = u"Hey, {}!!! {}\n".format(user['first_name'], emoji_sun)
            message += u"Thank you for joining our community! {}\n".format(emoji_thumb)
            message += u"We give you 7 days Premium subscription! {}\n".format(emoji_fire)
            message += u"First things first, let's create your first task.\n"
            message += u"Press {}".format(self.todo_name)
        else:
            message = u'Type "cancel"" in case of trouble.\nPress {} to create another task'.format(self.todo_name)
        markup = self._create_initial()
        self._change_state('initial')
        kwargs = {"text": message, "reply_markup": markup}
        return kwargs

    def execute(self):
        new_messages = []
        kwargs = {"text": None, "reply_markup": None}

        if 'text' in self.update:
            print u'{} ({}): {}'.format(self.update['from']['first_name'], self.update['from']['id'], self.update['text'])
        print 'Chat id:', self.update['chat']['id']


        # Write new user, group into database
        user = self.write_user()
        self.write_group()

        user = self.users_db.find_one({"user_id": self.update['from']['id']})
        state = user.get('state{}'.format(self.update['chat']['id']), 'initial')

        print 'State:', state

        if 'text' not in self.update:
            return kwargs

        if state == 'initial':
            text= self.update['text'].strip()
            if text.lower() in ['cancel', '/cancel', '/help']:
                kwargs = self.cancel_all()
            elif text == '/start':
                kwargs = self.greetings()
            elif text == self.todo_name:
                kwargs = self.todo()
            elif text == self.addons_name:
                kwargs = self.addons()
            elif text == self.support_name:
                kwargs = self.support()
            elif text == self.notify_name:
                kwargs = self.notify()
            elif text == self.settings_name:
                kwargs = self.settings()
            elif text == self.notifications_name:
                kwargs = self.notifications()
            elif text == self.get_premium_name:
                kwargs = self.get_premium()
            else:
                s = self.update['text']
                if s.startswith('payment-'): # check payment code
                    code = s[8:]
                    user = self.users_db.find_one({"payment_code": code})
                    if user:
                        kwargs = self.extend_expire(user)
                    else:
                        kwargs = self.invalid_code()
                else: # check if it's list
                    todos = self._all_lists()
                    texts = []
                    if '' in todos: # default list
                        texts = [task['text'] for task in todos[''] if 'text' in task]
                    idx = s.find('(')
                    if s in texts: # check if non-default list
                        kwargs = self.remove(s, '')
                    elif s[:idx-1] in todos:
                        kwargs = self.remove_from_list(s[:idx-1])
        elif state == 'todo_write':
            kwargs = self.todo_write()
        elif state == 'todo_create_list':
            kwargs = self.todo_create_list()
        elif state == 'todo_write_list':
            kwargs = self.todo_write_list()
        elif state == 'addons_choose':
            kwargs = self.addons_choose()
        elif state == 'todo_choose_list':
            kwargs = self.todo_choose_list()
        elif state == 'remove_list_task':
            kwargs = self.remove_list_task()
        elif state == 'notify_select':
            kwargs = self.notify_select()
        elif state == 'notify_choose_city':
            kwargs = self.notify_choose_city()
        elif state == 'notify_get_time':
            kwargs = self.notify_get_time()
        elif state == 'settings_select':
            kwargs = self.settings_select()
        elif state == 'settings_choose_city':
            kwargs = self.settings_choose_city()
        elif state == 'notifications_choose_city':
            kwargs = self.notifications_choose_city()
        elif state == 'notifications_choose_time':
            kwargs = self.notifications_choose_time()
        else:
            message = u'Return to initial menu {}'.format(emoji_return_arrow)
            markup = self._create_initial()
            kwargs = {"text": message, "reply_markup": markup}
            self._change_state('initial')

        new_messages = self.add_to_end(kwargs, new_messages)

        return new_messages