'''
'''
from __future__ import division
__author__ = 'sivanov'
import telebot, json, threading

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

            new_messages.append(update['message'])

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
        #TODO relaunch the procedure