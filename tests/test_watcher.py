from __future__ import unicode_literals
import io
import os
import sys
import time
from pydoc import locate
from contextlib import contextmanager
from . import TestGramex

_folder = os.path.dirname(os.path.abspath(__file__))
if _folder not in sys.path:
    sys.path.append(_folder)
# Since watch loads functions using locate(), we need to load it the same way.
# Otherwise, the utils imported by watch is different from utils imported here.
watch_info = locate('utils.watch_info')


class TestWatcher(TestGramex):
    @contextmanager
    def wait_for(self, event, url=None, delay=0.1, times=10, **kwargs):
        del watch_info[:]
        yield
        got_event = False
        for index in range(times):
            got_event = any(info['type'] == event for info in watch_info)
            if got_event:
                break
            time.sleep(delay)
        self.assertTrue(got_event, 'Watch event %s not fired' % event)
        if url:
            self.check(url, **kwargs)

    def test_watcher(self):
        for name in ['watcher.txt', 'dir/watch.test', 'watch.1.test', 'watch.2.test']:
            path = os.path.join(_folder, name)
            if os.path.exists(path):
                os.unlink(path)

            with self.wait_for('created', url='/' + name, text='created'):
                with io.open(path, 'w', encoding='utf-8') as handle:
                    handle.write('created')

            with self.wait_for('modified', url='/' + name, text='modified'):
                with io.open(path, 'a', encoding='utf-8') as handle:
                    handle.write('modified')

            with self.wait_for('deleted', url='/' + name, code=404):
                os.unlink(path)

    def test_watcher_api(self):
        # TODO: When an event happens, check that the event is captured
        # watcher.watch('name1', paths, on_modified=init)
        # TODO: Sub folders don't lead to multiple triggers
        # TODO: Refreshing doesn't lead to multiple triggers
        pass
