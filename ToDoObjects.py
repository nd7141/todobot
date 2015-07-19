'''

'''
from __future__ import division
import json, string
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

    def write(self, db):
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
    def from_json(cls, json_string, text, to_id=None):
        obj = cls.check_json(json_string)
        message_id = obj['message_id']
        chat_id = obj['chat']['id']
        from_id = obj['from']['id']
        created = obj['date']
        if to_id is None:
            to_id = ''
        return Task(message_id, text, chat_id, from_id, created, to_id)

    def __init__(self, message_id, text, chat_id, from_id, created, to_id):
        self.message_id = message_id
        self.text = text
        self.chat_id = chat_id
        self.from_id = from_id
        self.created = created
        self.finished = False
        self.to_id = to_id

    def write(self, db):
        db.insert(self.__dict__)

    def finish(self):
        self.finished = True

class Update(object):
    def __init__(self, update):
        self.update = update

    def write_user(self, db):
        if not db.find_one({"user_id": self.update["from"]["id"]}):
            user = User.from_json(self.update['from'], self.update['date'])
            user.write(db)

    def get_command(self):
        if 'text' in self.update and self.update['text'].startswith('/'):
            return self.update['text'].split()[0][1:].lower()

    def get_text(self, command):
        return self.update['text'][1 + len(command):]


class ToDoUpdate(Update):
    def __init__(self, update):
        super(self.__class__, self).__init__(update)
        self.commands = ['todo', 'list', 'done', 'help', 'cheer', 'make', 'for', 'over']

    def list(self, db):
        cursor = db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": ''}).sort("created")
        tasks = [u"{0}. {1}".format(ix + 1, task['text']) for (ix, task) in enumerate(cursor)]
        return 'Common list:\n' + '\n'.join(tasks) if tasks else "My lord, you have no tasks!"

    def done(self, db, number):
        try:
            number = int(number)
        except ValueError:
            return "I'm very sorry, my lord. You specified wrong task.".format(number)
        cursor = db.find({"chat_id": self.update['chat']['id'], "finished": False, 'to_id': ''}).sort("created")
        for ix, task in enumerate(cursor):
            if ix + 1 == number:
                db.update({"_id": task["_id"]},
                          {"set": {"finished": True}})
                return "I'm pleased to claim that you finished task {0}, my lord!".format(number)
        return "I'm very sorry, my lord. Task {0} does not exist in your list.".format(number)


    def todo(self, db, text):
        if not text:
            return "Please, provide non-empty task, my lord!"
        new_tsk = Task.from_json(self.update, text)
        new_tsk.write(db)
        return "You wrote new task!"

    def help(self):
        return ''' This is a Telegram ToDo bot, my lord.

        Write /help - to get this message.
        Write /todo Description_of_the_task - to write another task.
        Write /list - to list all tasks in your ToDo list.
        Write /done Number_of_the_task - to finish the task.

        The bot is under heavy self-development. Official release soon.
        Having more ideas or want to contribute? Write to ivanovserg990@gmail.com.
        '''

    def cheer(self):
        return '''You're not a man, You're God!'''

    def make(self, db, text):
        words = text.split()
        try:
            who = words[0]
        except IndexError:
            return "Please provide to whom you want assign a task, my lord."
        if len(words) < 2:
            return "Please provide a task, my lord."
        else:
            new_tsk = Task.from_json(self.update, ' '.join(words[1:]), who)
            new_tsk.write(db)
            return u"You assigned task to {0}, my lord".format(who)

    def for_f(self, db, text):
        words = text.split()
        try:
            who = words[0]
        except IndexError:
            return "Please provide for whom you want to show ToDo list, my lord."
        cursor = db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": who}).sort("created")
        tasks = [u"{0}. {1}".format(ix + 1, task['text']) for (ix, task) in enumerate(cursor)]
        return who + ':\n' + '\n'.join(tasks) if tasks else u"{0} has no tasks!".format(who)

    def over(self, db, text):
        words = text.split()
        try:
            who = words[0]
        except IndexError:
            return "Please provide for whom you want to remove a task, my lord."
        try:
            number = int(' '.join(words[1:]))
        except ValueError:
            return u"I'm very sorry, my lord. You specified wrong number of task: {0}.".format(' '.join(words[1:]))

        cursor = db.find({"chat_id": self.update['chat']['id'], "finished": False, "to_id": who}).sort("created")
        for ix, task in enumerate(cursor):
            if ix + 1 == number:
                db.update({"_id": task["_id"]},
                          {"set": {"finished": True}})
                return u"I'm pleased to claim that {0} finished task {1}, my lord!".format(who, number)
        return u"I'm very sorry, my lord. Task {0} does not exist in the list of {1}.".format(number, who)


    #TODO write more commands here

    def execute(self, users_db, tasks_db):
        # Write new user into database
        self.write_user(users_db)

        # Execute command
        command = self.get_command()
        if command in self.commands:
            text = self.get_text(command)
            if command == 'list':
                result = self.list(tasks_db)
            elif command == 'todo':
                result = self.todo(tasks_db, text)
            elif command == 'done':
                result = self.done(tasks_db, text)
            elif command == 'help':
                result = self.help()
            elif command == 'cheer':
                result = self.cheer()
            elif command == 'make':
                result = self.make(tasks_db, text)
            elif command == 'for':
                result = self.for_f(tasks_db, text)
            elif command == 'over':
                result = self.over(tasks_db, text)
            return result

if __name__ == "__main__":
    console = []