import io
import os
import six
import sys
import time
from pydoc import locate
from . import TestGramex

# Since watch loads functions using locate(), we need to load it the same way.
# Otherwise, the utils imported by watch is different from utils imported here.
_folder = os.path.dirname(os.path.abspath(__file__))
if _folder not in sys.path:
    sys.path.append(_folder)
watch_info = locate('utils.watch_info')


class TestWatcher(TestGramex):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'watcher.txt')

    def wait_for(self, event, delay=0.1, times=10):
        got_event = False
        for index in range(times):
            got_event = any(info['type'] == event for info in watch_info)
            if got_event:
                break
            time.sleep(delay)
        self.assertTrue(got_event, 'Watch event %s not fired' % event)

    def test_watcher(self):
        # Delete the watch file and ensure that it does not exist
        if os.path.exists(self.path):
            os.unlink(self.path)
        self.check('/watcher', code=404)

        # Create the watcher
        del watch_info[:]
        with io.open(self.path, 'w', encoding='utf-8') as handle:
            handle.write(six.text_type('created'))
        self.wait_for('created')
        self.check('/watcher', text='created')

        # Modify the watcher
        del watch_info[:]
        with io.open(self.path, 'a', encoding='utf-8') as handle:
            handle.write(six.text_type('modified'))
        self.wait_for('modified')
        self.check('/watcher', text='createdmodified')

        # Delete the watcher
        os.unlink(self.path)
        self.wait_for('deleted')
        self.check('/watcher', code=404)
