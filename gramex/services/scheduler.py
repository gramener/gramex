'''Gramex scheduling service'''

import re
import time
import tornado.ioloop
from crontab import CronTab
from concurrent.futures import ThreadPoolExecutor
from gramex.transforms import build_transform
from gramex.config import app_log, ioloop_running


class Task:
    '''Run a task. Then schedule it at the next occurrance.'''

    def __init__(
        self,
        name: str,
        schedule: dict,
        threadpool: ThreadPoolExecutor,
        ioloop: tornado.ioloop = None,
    ):
        '''Create a new task based on a schedule.

        Parameters:
            name: Name of the schedule
            schedule: Schedule configuration (see below)
            threadpool: Threadpool to use for running the task
            ioloop: IOLoop to run the task on. If None, use main IOLoop

        Schedule configurations are dicts with these keys:

        - `minutes`: minutes to run at (as per cron spec below)
        - `hours`: hours to run at (as per cron spec below)
        - `dates`: dates to run at (as per cron spec below)
        - `months`: months to run at (as per cron spec below)
        - `weekdays`: weekdays to run at (as per cron spec below)
        - `years`: years to run at (as per cron spec below)
        - `utc`: True for UTC time zone, else local time zone (default: False)
        - `every`: interval to run at (e.g. "3h 30m" or "90s")
        - `startup`: `True` to run at startup, `'*'` to run on every config change
        - `thread`: `True` to run in a separate thread (default: False)

        The minutes, hours, dates, months, weekdays, years keys can take these values:

        - `*`: use all possible values, i.e. every minute, every hour, etc.
        - `3,4,5`: use multiple values separated by commas
        - `1-5`: use range of values
        - `*/4`: repeat every 4th time, i.e. every 4th minute, 4th hour, etc.
        - `8-16/2`: repeat every 2nd time between 8 to 16. Same as 8,10,12,14,16

        To specify a schedule, you must specify at least one of these:

        - `minutes`, `hours`, `dates`, `months`, `weekdays`, `years`
        - `every`
        - `startup`
        '''
        self.name = name
        self.utc = schedule.get('utc', False)
        self.thread = schedule.get('thread', False)
        startup = schedule.get('startup')
        if 'function' not in schedule:
            raise ValueError(f'schedule {name} has no function:')
        if callable(schedule['function']):
            self.function = schedule['function']
        else:
            self.function = build_transform(
                schedule, vars={}, iter=False, filename=f'schedule:{name}'
            )
        self.ioloop = ioloop or tornado.ioloop.IOLoop.current()
        self.every = None  # If set, Task runs every self.every seconds
        self.cron = None  # If set, Task runs on cron.next()
        self.callback = None  # Handle for next scheduled run (or None)
        self.next = None  # Time of next scheduled run (for tests/test_schedule.py)

        if self.thread:
            fn = self.function

            def on_done(future):
                exception = future.exception(timeout=0)
                if exception:
                    app_log.error(f'schedule:{name}: {exception}')

            def run_function(*args, **kwargs):
                future = threadpool.submit(fn, *args, **kwargs)
                future.add_done_callback(on_done)
                return future

            self.function = run_function

        # Run on schedule if any of the schedule periods are specified
        periods = ['minutes', 'hours', 'dates', 'months', 'weekdays', 'years']
        if any(key in schedule for key in periods):
            # Convert all period values into strings (e.g. 30 => '30'), and ignore any spaces
            cron_str = (str(schedule.get(key, '*')).replace(' ', '') for key in periods)
            self.cron = CronTab(' '.join(cron_str))

        # But if every: is present, run at a fixed interval
        if 'every' in schedule:
            every = schedule['every']
            match = re.match(
                r'''
                (?:([\d\.]+)\s*w[a-z]*\s*)?     # weeks
                (?:([\d\.]+)\s*d[a-z]*\s*)?     # days
                (?:([\d\.]+)\s*h[a-z]*\s*)?     # hours
                (?:([\d\.]+)\s*m[a-z]*\s*)?     # minutes
                (?:([\d\.]+)\s*s[a-z]*\s*)?     # seconds
                $
            ''',
                every,
                re.IGNORECASE + re.VERBOSE,
            )
            if match is None:
                app_log.error(f'schedule:{name} has invalid every: {every}')
            else:
                w, d, h, m, s = (float(v or 0) for v in match.groups())
                self.every = s + 60 * (m + 60 * (h + 24 * (d + 7 * w)))

        # Schedule next run if there's a schedule.
        if self.every or self.cron:
            self.call_later()
        elif startup is None:
            app_log.error(f'schedule:{name} has no schedule nor startup')

        # Run now if the task is to be run on startup. Don't re-run if the config was reloaded
        if startup == '*' or (startup is True and not ioloop_running(self.ioloop)):
            self.function()

    def run(self, *args, **kwargs):
        '''Run task. Then set up next callback.'''
        app_log.info(f'Running {self.name}')
        try:
            self.result = self.function(*args, **kwargs)
        finally:
            # Run again, if not stopped via self.stop() or end of schedule
            if self.callback is not None:
                self.call_later()

    def stop(self):
        '''Suspend task, clearing any pending callbacks'''
        if self.callback is not None:
            app_log.debug(f'Stopping {self.name}')
            self.ioloop.remove_timeout(self.callback)
            self._schedule_next_run(None)

    def call_later(self):
        '''Schedule next run automatically. Clears any previous scheduled runs'''
        if self.every:
            if self.cron:
                app_log.warning(
                    f'scheduler:{self.name} has BOTH schedule & every:. '
                    f'Running every: {self.every}s'
                )
            # Run "every" seconds after last scheduled time
            delay = (self.next or time.time()) + self.every - time.time()
            while delay < 0:
                delay += self.every
        elif self.cron:
            delay = self.cron.next(default_utc=self.utc)
        else:
            delay = None
        self._schedule_next_run(delay)
        if delay is not None:
            app_log.debug(f'schedule:{self.name}: Next run in {delay:.1f}s')
        else:
            app_log.debug(f'schedule:{self.name}: No more runs')

    def _schedule_next_run(self, delay):
        '''Schedule next run after delay seconds. If delay is None, no more runs.'''
        if delay is not None:
            if self.callback is not None:
                self.ioloop.remove_timeout(self.callback)
            self.callback = self.ioloop.call_later(delay, self.run)
            self.next = time.time() + delay
        else:
            self.callback, self.next = None, None
