from . import TestGramex
from datetime import datetime
from gramex.http import OK
from gramex.services import info
from nose.tools import eq_


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
        # Check that the next scheduled event is at 5 am in relevant time zone
        date = datetime.fromtimestamp(info.schedule['schedule-timed'].next)
        eq_((date.hour, date.minute, date.second), (5, 0, 0))
        date = datetime.utcfromtimestamp(info.schedule['schedule-timed-utc'].next)
        eq_((date.hour, date.minute, date.second), (5, 0, 0))
        # schedule-every runs every 1.5 hours 1.5m 2.5 sec = 5400 + 90 + 2.5 = 5492.5s
        eq_(info.schedule['schedule-every'].every, b=5492.5)
