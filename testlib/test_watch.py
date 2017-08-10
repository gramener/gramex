from __future__ import unicode_literals

import io
import os
import time
import warnings
import unittest
from collections import defaultdict
from orderedattrdict import AttrDict
import gramex.services.watcher as watcher
from nose.tools import eq_, ok_

_folder = os.path.dirname(os.path.abspath(__file__))


class TestWatch(unittest.TestCase):
    '''Test watcher API'''

    @classmethod
    def setUpClass(cls):
        cls.events = defaultdict(list)
        cls.files = AttrDict()
        cls.files['x'] = os.path.join(_folder, 'x.txt')
        cls.files['y'] = os.path.join(_folder, 'y.txt')
        cls.files['z'] = os.path.join(_folder, 'z.txt')

    def on(self, event_type, queue):
        '''
        Return event handler for event type that adds to the named queue.
        When handler(event) is called, it adds {type:event_type, event:event}
        to self.events[queue].
        '''
        def handler(event):
            self.events[queue].append(AttrDict(type=event_type, event=event))
        return handler

    delays = (0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5)

    def wait_for(self, queue, value, limit=None):
        '''
        Wait until self.events[queue] to have a length of value. Since watchdog
        fires on a separate thread, we'll have to poll periodically.
        '''
        for delay in self.delays:
            time.sleep(delay)
            if len(self.events[queue]) >= value:
                break
        if limit is None:
            eq_(len(self.events[queue]), value)
        else:
            count = len(self.events[queue])
            if count > value:
                warnings.warn('Modified count %d higher than expected %d' % (count, value))
                ok_(value <= count <= limit)

    def other_events(self, key):
        '''
        Get count of all event queues except for the current key. Used to ensure
        that when a file is changed, events for other files are not triggered.
        '''
        return {
            (event, other_key): len(self.events.get((event, other_key), []))
            for event in ('created', 'modified', 'deleted')
            for other_key in self.files.keys()
            if other_key != key
        }

    def register_and_check_watch(self, key, name='watch', times=1, result_count=1):
        # Register the watcher multiple times. This is to test that
        # re-registering the same watcher does not create multiple events.
        for reregistration_count in range(times):
            watcher.watch(
                name + '-' + key, [self.files[key]],
                on_created=self.on('created', ('created', key)),
                on_modified=self.on('modified', ('modified', key)),
                on_deleted=self.on('deleted', ('deleted', key)))
        # Capture the count of other event queues. This should not change
        other_events = self.other_events(key)
        # Create and delete the file
        with io.open(self.files[key], 'w', encoding='utf-8') as handle:
            handle.write(key)
        os.unlink(self.files[key])
        # Ensure that created & deleted event fired exactly once.
        self.wait_for(('created', key), result_count)
        self.wait_for(('deleted', key), result_count)
        # Modified should also be fired only once. In Python 2, this works. But
        # in Python 3, modified is *sometimes* fired twice. Maybe once on
        # creation and once on change.
        self.wait_for(('modified', key), result_count, result_count * 2)
        # Ensure other events have not fired in the meantime
        eq_(other_events, self.other_events(key))

    def test_watch(self):
        # When a file is changed, fire events
        self.remove_files()

        # Set up events for each file
        self.events.clear()
        for key in self.files.keys():
            self.register_and_check_watch(key, name='watch', times=15, result_count=1)

        # Test multiple watches
        self.events.clear()
        for key in self.files.keys():
            self.register_and_check_watch(key, name='new-watch', times=15, result_count=2)
        self.events.clear()
        for key in self.files.keys():
            self.register_and_check_watch(key, name='third-watch', times=15, result_count=3)

        # Test unwatch
        self.events.clear()
        for key in self.files.keys():
            watcher.unwatch('watch-' + key)
            watcher.unwatch('new-watch-' + key)
            watcher.unwatch('third-watch-' + key)

        # eq_(list(watcher.observer._handlers.values()), [set()])
        for key in self.files.keys():
            self.register_and_check_watch(key, name='fresh-watch', times=10, result_count=1)

    @classmethod
    def remove_files(cls):
        for path in cls.files.values():
            if os.path.exists(path):
                os.unlink(path)

    @classmethod
    def tearDownClass(cls):
        # Remove temporary files
        cls.remove_files()
