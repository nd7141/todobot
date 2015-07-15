'''
'''
from __future__ import division
__author__ = 'sivanov'
import telebot, json, threading
import time
import logging

class ToDoBot(telebot.TeleBot):
    """ ToDoBot overrides the functionality of get_update function of TeleBot.
    In addition to getting array of updates (messages), we also get User and (optional) Group object.
    """
    def get_update(self):
        logging.basicConfig(level=logging.DEBUG, filename='log.txt')
        new_messages = []
        try:
            updates = telebot.apihelper.get_updates(self.token, offset=(self.last_update_id + 1), timeout=20)
        except Exception:
            print("TeleBot: Exception occurred.")
            logging.exception("An error retrieving updates!")
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
        logging.basicConfig(level=logging.DEBUG, filename='log.txt')
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        print('TeleBot: Started polling.')
        while not self.__stop_polling:
            try:
                self.get_update()
            except Exception as e:
                print("TeleBot: Exception occurred.")
                print(e)
                logging.exception("TeleBot: Exception occurred.")
                self.__stop_polling = True

        print('TeleBot: Stopped polling.')