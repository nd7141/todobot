# author: sivanov
# date: 23 Sep 2015
# taken from: https://github.com/patrys/pymongo-pubsub/tree/master/pymongo_pubsub
from __future__ import division

import time, pymongo

class Publisher(object):

    max_size = 1000000
    max_length = None

    def __init__(self, database, collection_name,
                 max_size=1000000, max_length=None):
        self.collection = self.init_collection(database, collection_name)
        self.max_size = max_size
        self.max_length = max_length

    def init_collection(self, database, collection_name):
        if collection_name not in database.collection_names():
            collection = database.create_collection(collection_name,
                                                    capped=True,
                                                    size=self.max_size,
                                                    max=self.max_length)
        else:
            collection = database[collection_name]
            if not collection.options().get('capped'):
                raise TypeError(
                    'Collection "{0}" is not capped'.format(collection_name))
        return collection

    def push(self, data):
        record = dict(data, _id=time.time())
        self.collection.insert(record)


class Subscriber(object):

    callbacks = None
    check_interval = 1.0
    iterator = None

    def __init__(self, database, collection_name, callback,
                 matching=None, check_interval=1.0):
        self.collection = self.init_collection(database, collection_name)
        self.callback = callback
        self.check_interval = check_interval
        self.iterator = self.collection.find(matching, cursor_type=pymongo.cursor.CursorType.TAILABLE)

    def init_collection(self, database, collection_name):
        if not collection_name in database.collection_names():
            raise KeyError(
                'Collection "{0}" does not exist'.format(collection_name))
        collection = database[collection_name]
        if not collection.options().get('capped'):
            raise TypeError(
                'Collection "{0}" is not capped'.format(collection_name))
        return collection

    def register(self, callback):
        self.callbacks.add(callback)

    def listen(self, since=None):
        for record_available in self.steps():
            if not record_available:
                time.sleep(self.check_interval)

    def steps(self):
        while self.iterator.alive:
            try:
                record = self.iterator.next()
                self.callback(record)
                yield True
            except StopIteration:
                yield False


if __name__ == "__main__":
    console = []