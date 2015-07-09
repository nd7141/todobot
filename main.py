'''

'''
from __future__ import division
import telebot, os, json, time
__author__ = 'sivanov'

class Listener(object):
    def __init__(self, nbr, dbfile):
        self.nbr = nbr
        self.dbfile = dbfile

    def listener(self, *messages):
        try:
            with open(self.dbfile) as fp:
                db = json.load(fp)
        except IOError:
            db = dict()

        print 'Existing db:', db
        for m in messages:
            chatid = m.chat.id
            content_type = m.content_type
            print "Message %s from %s has type %s" %(self.nbr, chatid, content_type)
            self.nbr += 1
            if content_type == "text":
                text = m.text
                if text[:5].lower() == '/todo':
                    db.setdefault(str(chatid), []).append(text[5:])
                    print 'Changed db:', db
                    with open(self.dbfile, 'w+') as fp:
                        json.dump(db, fp)
                    tb.send_message(chatid, 'Wrote new task')
                elif text[:5].lower() == '/list':
                    if not len(db.get(str(chatid), [])):
                        tb.send_message(chatid, 'No tasks in the list')
                    else:
                        s = 'Tasks:\n' + '\n'.join([str(ix+1) + '.' + task for ix, task in enumerate(db[str(chatid)])])
                        tb.send_message(chatid, s)
                elif text[:5].lower() == '/done':
                    try:
                        tsk = int(text[5:])
                        del db[str(chatid)][tsk-1]
                        tb.send_message(chatid, 'Removed task %s for you' % tsk)
                        with open(self.dbfile, 'w+') as fp:
                            json.dump(db, fp)
                    except ValueError:
                        tb.send_message(chatid, 'Provide number of the existing task')
                    except IndexError:
                        tb.send_message(chatid, 'No such task exist')
                    except KeyError:
                        tb.send_message(chatid, 'No tasks in the list')
                elif text[:5].lower() == '/help':
                    s = '''This is a simple todo bot -- it will help you to keep track of you tasks.

                    Write /help -- to get this message.
                    Write /todo "Name of the task" -- to write new task in the list.
                    Write /list -- to get the list of existing tasks.
                    Write /done "Number of the task" -- to remove task from the list.'''
                    tb.send_message(chatid, s)



if __name__ == "__main__":

    with open('token.txt') as f:
        TOKEN = f.read().split()[0]

    l = Listener(0, 'db.json')
    tb = telebot.TeleBot(TOKEN)
    tb.set_update_listener(l.listener)
    tb.polling()

    while True:
        pass

    console = []