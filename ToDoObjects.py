'''

'''
from __future__ import division
import json, os, time, datetime
__author__ = 'sivanov'

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
        self.info = {'city': ''}
        self.trained = False

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
    def from_json(cls, json_string, to_id=None):
        obj = cls.check_json(json_string)
        message_id = obj['message_id']
        chat_id = obj['chat']['id']
        from_id = obj['from']['id']
        created = obj['date']
        if to_id is None:
            to_id = ''
        return Task(message_id, obj.get('text', ''), chat_id, from_id, created, to_id)

    def __init__(self, message_id, text, chat_id, from_id, created, to_id):
        self.message_id = message_id
        self.text = text
        self.chat_id = chat_id
        self.from_id = from_id
        self.created = created
        self.end = None
        self.finished = False
        self.to_id = to_id

    def finish(self):
        self.finished = True

class Update(object):
    def __init__(self, update):
        self.update = update

    @staticmethod
    def get_command(update):
        if 'text' in update and update['text'].startswith('/'):
            return update['text'].split()[0][1:].lower(), update['text']

    @staticmethod
    def get_text(update, command):
        return update['text'][1 + len(command):]

    @staticmethod
    def strtime(unix):
        return datetime.datetime.utcfromtimestamp(int(unix)).strftime('%d %B %Y %H:%M:%S')


if __name__ == "__main__":
    console = []