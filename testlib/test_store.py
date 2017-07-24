# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import json
import time
import shutil
import unittest
from nose.tools import eq_, ok_
from gramex.handlers.basehandler import JSONStore, BaseMixin

folder = os.path.dirname(os.path.abspath(__file__))
folder = os.path.join(folder, 'store')


class TestJSONStore(unittest.TestCase):

    @classmethod
    def setupClass(cls):
        # Delete the directory to check if the directory is auto-created.
        # Ignore errors, because this is not critical.
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)
        # Do not set up a scheduled flush - IOLoop is not available here
        cls.path = os.path.join(folder, 'data.json')
        cls.store = JSONStore(cls.path, flush=None, purge=BaseMixin._purge)

    def test_store(self):
        self.store.dump('►', 'α')
        self.store.flush()
        with open(self.path, 'r') as handle:    # noqa: no encoding for json
            data = json.load(handle)
        eq_(data, {'►': 'α'})

        self.store.dump('λ', {'α': 1, 'β': None})
        self.store.flush()
        with open(self.path, 'r') as handle:    # noqa: no encoding for json
            data = json.load(handle)
        eq_(data, {'►': 'α', 'λ': {'α': 1, 'β': None}})

    def test_expiry(self):
        self.store.dump('►', {'_t': 0})
        self.store.dump('λ', {'_t': time.time() - 1})
        self.store.dump('x', None)
        self.store.flush()
        with open(self.path, 'r') as handle:    # noqa: no encoding for json
            data = json.load(handle)
        eq_(data, {})

    @classmethod
    def teardownClass(cls):
        # Close the store and ensure that the handle is closed
        cls.store.close()
        ok_(cls.store.handle.closed)

        # Delete folder to cleanup
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)
