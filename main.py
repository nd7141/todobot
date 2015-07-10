'''

'''
from __future__ import division
import telebot, os, json, time
__author__ = 'sivanov'
from ToDoBot import ToDoBot

class Listener(object):
    def __init__(self, nbr, dbfile, td):
        self.nbr = nbr
        self.dbfile = dbfile
        self.td = td

    def listener(self, *messages):
        print 'In listener'
        try:
            with open(self.dbfile) as fp:
                db = json.load(fp)
        except IOError:
            db = dict()

        print 'Existing db:', db
        for msg in messages:
            m = msg[0]
            user = msg[1]
            print user.__dict__
            chatid = m.chat.id
            content_type = m.content_type
            print "Message %s from %s has type %s" %(self.nbr, chatid, content_type)
            self.nbr += 1
            if content_type == "text":
                text = m.text
                command = td.extract_command(text)
                if command.lower() == 'todo':
                    db.setdefault(str(chatid), []).append(text[5:])
                    print 'Changed db:', db
                    with open(self.dbfile, 'w+') as fp:
                        json.dump(db, fp)
                    self.td.send_message(chatid, 'Wrote new task')
                elif command.lower() == 'list':
                    if not len(db.get(str(chatid), [])):
                        self.td.send_message(chatid, 'No tasks in the list')
                    else:
                        s = 'Tasks:\n' + '\n'.join([str(ix+1) + '.' + task for ix, task in enumerate(db[str(chatid)])])
                        self.td.send_message(chatid, s)
                elif command.lower() == 'done':
                    try:
                        tsk = int(text[5:])
                        del db[str(chatid)][tsk-1]
                        self.td.send_message(chatid, 'Removed task %s for you' % tsk)
                        with open(self.dbfile, 'w+') as fp:
                            json.dump(db, fp)
                    except ValueError:
                        self.td.send_message(chatid, 'Provide number of the existing task')
                    except IndexError:
                        self.td.send_message(chatid, 'No such task exist')
                    except KeyError:
                        self.td.send_message(chatid, 'No tasks in the list')
                elif command.lower() == 'help':
                    s = '''This is a simple todo bot -- it will help you to keep track of you tasks.

                    Write /help -- to get this message.
                    Write /todo "Name of the task" -- to write new task in the list.
                    Write /list -- to get the list of existing tasks.
                    Write /done "Number of the task" -- to remove task from the list.'''
                    self.td.send_message(chatid, s)
                elif str(chatid) not in db:
                    pass
                    #TODO create another database with users (even if those did't write todo task)
                    # and prompt them with description of bot



if __name__ == "__main__":

    with open('token.txt') as f:
        TOKEN = f.read().split()[0]

    print TOKEN

    #TODO check that command is working
    td = ToDoBot(TOKEN)
    l = Listener(0, 'db.json', td)
    td.set_update_listener(l.listener)
    td.polling()

    while True:
        pass

    console = []