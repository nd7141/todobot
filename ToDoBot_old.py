'''
'''
from __future__ import division
__author__ = 'sivanov'
import telebot, json, threading

class Jsonish(object):
    """
    Subclasses of this class are guaranteed to be able to be created from a json-style dict or json formatted string.
    All subclasses of this class must override de_json.
    """
    @classmethod
    def from_json(cls, json_type):
        """
        Returns an instance of this class from the given json dict or string.

        This function must be overridden by subclasses.
        :return: an instance of this class created from the given json dict or string.
        """
        raise NotImplementedError

    @staticmethod
    def check_json(json_type):
        """
        Checks whether json_type is a dict or a string. If it is already a dict, it is returned as-is.
        If it is not, it is converted to a dict by means of json.loads(json_type)
        :param json_type:
        :return:
        """
        if type(json_type) == dict:
            return json_type
        elif type(json_type) == str:
            return json.loads(json_type)
        else:
            raise ValueError("json_type should be a json dict or string.")

class User(Jsonish):
    @classmethod
    def from_json(cls, json_string, timestamp):
        obj = cls.check_json(json_string)
        user_id = obj['id']
        first_name = obj['first_name']
        last_name = ''
        username = ''
        if 'last_name' in obj:
            last_name = obj['last_name']
        if 'username' in obj:
            username = obj['username']
        return User(user_id, first_name, timestamp, last_name, username)

    def __init__(self, user_id, first_name, created, last_name=None, username=None):
        self.user_id = user_id
        self.first_name = first_name
        self.created = created
        self.last_name = last_name
        self.username = username

    def present(self, db):
        if db.find_one({'user_id': self.user_id}):
            return True
        return False

    def write(self, db):
        if not self.present(db):
            db.insert_one(self.__dict__)

class Group(Jsonish):
    @classmethod
    def from_json(cls, json_string, timestamp, participant):
        obj = cls.check_json(json_string)
        group_id = obj['id']
        title = obj['title']
        return Group(group_id, title, timestamp, participant)

    def __init__(self, group_id, title, created, participant):
        self.group_id = group_id
        self.title = title
        self.created = created
        self.participants = [participant]

class Task(Jsonish):
    @classmethod
    def from_json(cls, json_string, to_id):
        obj = cls.check_json(json_string)
        message_id = obj['message_id']
        chat_id = obj['chat']['id']
        from_id = obj['from']['id']
        created = obj['date']
        if to_id is None:
            to_id = ''
        return Task(message_id, chat_id, from_id, created, to_id)

    def __init__(self, message_id, chat_id, from_id, created, to_id):
        self.message_id = message_id
        self.chat_id = chat_id
        self.from_id = from_id
        self.created = created
        self.finished = False
        self.to_id = to_id

    def write(self, db):
        db.insert(self.__dict__)

    def finish(self):
        self.finished = True

class ToDoBot(telebot.TeleBot):
    """ ToDoBot overrides the functionality of get_update function of TeleBot.
    In addition to getting array of updates (messages), we also get User and (optional) Group object.
    """
    def get_update(self):
        updates = telebot.apihelper.get_updates(self.token, offset=(self.last_update_id + 1), timeout=20)
        new_messages = []
        for update in updates:
            if update['update_id'] > self.last_update_id:
                self.last_update_id = update['update_id']

            msg = telebot.types.Message.de_json(update['message'])
            user = User.from_json(update['message']['from'], update['message']['date']) # create a User object
            #TODO return pure message json object; move user/group/task creation to main file

            new_messages.append([msg, user])

        if len(new_messages) > 0:
            self.__notify_update(new_messages)
            self._notify_command_handlers(new_messages)

    def __notify_update(self, new_messages):
        for listener in self.update_listener:
            t = threading.Thread(target=listener, args=new_messages)
            t.start()

    def __polling(self):
        print('TeleBot: Started polling.')
        while not self.__stop_polling:
            try:
                self.get_update()
            except Exception as e:
                print("TeleBot: Exception occurred. Stopping.")
                self.__stop_polling = True
                print(e)

        print('TeleBot: Stopped polling.')