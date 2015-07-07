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
                    db.setdefault(chatid, []).append((len(db.get(chatid, 0)), text[5:]))
                    with open(self.dbfile, 'w+') as fp:
                        json.dump(db, fp)
                    print 'Wrote new task into todo'
                    tb.send_message(chatid, 'Wrote new task into todo')



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