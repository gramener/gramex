from . import TestGramex
from datetime import datetime
from dateutil.tz import tzlocal, tzutc
from gramex.http import OK
from gramex.services import info
from nose.tools import eq_, ok_


class TestSchedule(TestGramex):
    def test_startup(self):
        # Check if code in schedules with startup: true are executed
        self.check('/schedule-key', text='1', code=OK)

    def test_long_running_threads(self):
        # Start utils.slow_count in a thread and wait till the scheduler starts.
        # It increases info['schedule-count'] every 10ms.
        self.check('/slow-count-start', code=OK)
        # Check that the counter has increased after a small delay
        self.check('/slow-count-check', code=OK)

    def test_timed_schedule(self):
        # TODO: This test only works when we run at 5 am in the server's time zone. Not robust
        # Check that schedules are present and created
        ok_('schedule-timed' in info.schedule)
        ok_('schedule-timed-utc' in info.schedule)
        # Check that the schedules will run at 5 am in the appropriate time zone
        for key, tz in (('schedule-timed', tzlocal()), ('schedule-timed-utc',
                                                        tzutc())):
            t = datetime.fromtimestamp(info.schedule[key].next, tz)
            eq_(t.hour, 5)
            # Ideally, this should be 0, but there may be a short delay
            ok_(t.minute < 2)
