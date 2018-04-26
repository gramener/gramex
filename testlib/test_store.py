# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import six
import json
import time
import shutil
import unittest
from nose.tools import eq_, ok_
from gramex.handlers.basehandler import JSONStore, SQLiteStore, HDF5Store, BaseMixin

folder = os.path.dirname(os.path.abspath(__file__))
folder = os.path.join(folder, 'store')


def setUp():
    # Delete the directory to check if the directory is auto-created.
    # Ignore errors, because this is not critical.
    if os.path.exists(folder):
        shutil.rmtree(folder, ignore_errors=True)


def tearDown():
    if os.path.exists(folder):
        shutil.rmtree(folder)


class TestJSONStore(unittest.TestCase):
    store_class = JSONStore
    store_file = 'data.json'

    @classmethod
    def setupClass(cls):
        # Do not set up a scheduled flush - IOLoop is not available here
        cls.path = os.path.join(folder, cls.store_file)
        cls.plainstore = cls.store_class(cls.path, flush=None)
        cls.store = cls.store_class(cls.path, flush=None, purge_keys=BaseMixin._purge_keys)
        cls.store2 = cls.store_class(cls.path, flush=None, purge_keys=BaseMixin._purge_keys)

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, 'r') as handle:    # noqa: no encoding for json
                data = json.load(handle)
            return data
        return {}

    def test_01_flush(self):
        # Run this test first to ensure flush() without dump() is possible
        # https://stackoverflow.com/a/18627017/100904
        self.store.flush()

    def test_conflict(self):
        expiry = time.time() + 1000
        keystores = (('x', self.store), ('y', self.store2), ('z', self.plainstore))

        # Test writing and flushing each store one after another
        for key, store in keystores:
            store.dump(key, {'v': 1, '_t': expiry})
            store.flush()
        data = self.load()
        for key, store in keystores:
            eq_(data.get(key), {'v': 1, '_t': expiry})

        # Test writing all and then flushing
        for key, store in keystores:
            store.dump(key, {'v': 2, '_t': expiry})
        for key, store in keystores:
            store.flush()
        data = self.load()
        for key, store in keystores:
            eq_(data.get(key), {'v': 2, '_t': expiry})

    def test_expiry(self):
        # purge removes expired items
        original = self.load()
        self.store.dump('►', {'_t': 0})
        self.store.dump('λ', {'_t': time.time() - 1})
        self.store.dump('x', None)
        self.plainstore.dump('y', None)
        self.store.purge()
        self.plainstore.purge()
        original.pop('x')
        original.pop('y')
        eq_(self.load(), original)

        # plainstore doesn't remove _t items
        self.plainstore.dump('►', {'_t': 0})
        self.plainstore.dump('λ', {'_t': time.time() - 1})
        self.plainstore.purge()
        result = self.load()
        ok_('►' in result)
        ok_('λ' in result)

    def test_store(self):
        data = self.load()
        expiry = time.time() + 1000
        self.store.dump('►', {'_t': expiry, 'α': True})
        self.store.flush()
        data.update({'►': {'_t': expiry, 'α': True}})
        eq_(self.load(), data)

        self.store.dump('λ', {'α': 1, 'β': None, '_t': expiry})
        self.store.purge()
        data.update({'λ': {'α': 1, 'β': None, '_t': expiry}})
        eq_(self.load(), data)

    @classmethod
    def teardownClass(cls):
        # Close the store and ensure that the handle is closed
        cls.plainstore.close()
        cls.store.close()
        cls.store2.close()


class TestSQLiteStore(TestJSONStore):
    store_class = SQLiteStore
    store_file = 'data.db'

    def load(self):
        return {
            (key.decode('utf-8') if isinstance(key, six.binary_type) else key): val
            for key, val in self.store.store.items()
        }


class TestHDF5Store(TestSQLiteStore):
    store_class = HDF5Store
    store_file = 'data.h5'

    def load(self):
        return {
            json.loads('"%s"' % key).replace('\t', '/'): json.loads(val.value)
            for key, val in self.store.store.items()
        }
