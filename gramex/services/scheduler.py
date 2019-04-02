'''Gramex scheduling service'''

import time
import tornado.ioloop
from crontab import CronTab
from gramex.transforms import build_transform
from gramex.config import app_log, ioloop_running


class Task(object):
    '''Run a task. Then schedule it at the next occurrance.'''

    def __init__(self, name, schedule, threadpool, ioloop=None):
        '''
        Create a new task based on a schedule in ioloop (default to current).

        The schedule configuration accepts:

        - startup: True to run at startup, '*' to run on every config change
        - minutes, hours, dates, months, weekdays, years: cron schedule
        - thread: True to run in a separate thread
        '''
        self.name = name
        self.utc = schedule.get('utc', False)
        self.thread = schedule.get('thread', False)
        if 'function' not in schedule:
            raise ValueError('schedule %s has no function:' % name)
        if callable(schedule['function']):
            self.function = schedule['function']
        else:
            self.function = build_transform(schedule, vars={}, filename='schedule:%s' % name)
        self.ioloop = ioloop or tornado.ioloop.IOLoop.current()
        self._call_later(None)

        if self.thread:
            fn = self.function

            def on_done(future):
                exception = future.exception(timeout=0)
                if exception:
                    app_log.error('%s (thread): %s', name, exception)

            def run_function(*args, **kwargs):
                future = threadpool.submit(fn, *args, **kwargs)
                future.add_done_callback(on_done)
                return future

            self.function = run_function

        # Run on schedule if any of the schedule periods are specified
        periods = 'minutes hours dates months weekdays years'.split()
        if any(schedule.get(key) for key in periods):
            # Convert all valid values into strings (e.g. 30 => '30'), and ignore any spaces
            cron = (str(schedule.get(key, '*')).replace(' ', '') for key in periods)
            self.cron_str = ' '.join(cron)
            self.cron = CronTab(self.cron_str)
            self.call_later()
        elif not schedule.get('startup'):
            app_log.warning('schedule:%s has no schedule nor startup', name)

        # Run now if the task is to be run on startup. Don't re-run if the config was reloaded
        startup = schedule.get('startup')
        if startup == '*' or (startup is True and not ioloop_running(self.ioloop)):
            self.function()

    def run(self, *args, **kwargs):
        '''Run task. Then set up next callback.'''
        app_log.info('Running %s', self.name)
        try:
            self.result = self.function(*args, **kwargs)
        finally:
            # Run again, if not stopped via self.stop() or end of schedule
            if self.callback is not None:
                self.call_later()

    def stop(self):
        '''Suspend task, clearing any pending callbacks'''
        if self.callback is not None:
            app_log.debug('Stopping %s', self.name)
            self.ioloop.remove_timeout(self.callback)
            self._call_later(None)

    def call_later(self):
        '''Schedule next run automatically. Clears any previous scheduled runs'''
        delay = self.cron.next(default_utc=self.utc) if hasattr(self, 'cron') else None
        self._call_later(delay)
        if delay is not None:
            app_log.debug('Scheduling %s after %.0fs', self.name, delay)
        else:
            app_log.debug('No further schedule for %s', self.name)

    def _call_later(self, delay):
        '''Schedule next run after delay seconds. If delay is None, no more runs.'''
        if delay is not None:
            if self.callback is not None:
                self.ioloop.remove_timeout(self.callback)
            self.callback = self.ioloop.call_later(delay, self.run)
            self.next = time.time() + delay
        else:
            self.callback, self.next = None, None
