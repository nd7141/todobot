# author: sivanov
# date: 20 Aug 2015
from __future__ import division
import telebot
from emoji_chars import *

initial = telebot.types.ReplyKeyboardMarkup(row_width=1)
initial.add(u'/todo {}'.format(emoji_memo), u'/list {}'.format(emoji_clipboard), u'/done {}'.format(emoji_hammer), '/completed', '/tutorial')

cancel_btn = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
cancel_btn.add('Cancel')

cancel_ttrl = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
cancel_ttrl.add(u'Cancel tutorial {}'.format(emoji_cross))

if __name__ == "__main__":
    console = []