'''Gramex scheduling service'''

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
        if 'function' not in schedule:
            raise ValueError('schedule %s has no function:' % name)
        if callable(schedule['function']):
            self.function = schedule['function']
        else:
            self.function = build_transform(schedule, vars={}, filename='schedule:%s' % name)
        self.ioloop = ioloop or tornado.ioloop.IOLoop.current()
        self.callback = None

        if schedule.get('thread'):
            fn = self.function

            def on_done(future):
                exception = future.exception(timeout=0)
                if exception:
                    app_log.error('%s (thread): %s', name, exception)

            self.function = lambda: threadpool.submit(fn).add_done_callback(on_done)

        # Run on schedule if any of the schedule periods are specified
        periods = 'minutes hours dates months weekdays years'.split()
        if any(schedule.get(key) for key in periods):
            # Convert all valid values into strings (e.g. 30 => '30'), and ignore any spaces
            cron = (str(schedule.get(key, '*')).replace(' ', '') for key in periods)
            self.cron = CronTab(' '.join(cron))
            self._schedule()
        elif not schedule.get('startup'):
            app_log.warning('schedule:%s has no schedule nor startup', name)

        # Run now if the task is to be run on startup. Don't re-run if the config was reloaded
        startup = schedule.get('startup')
        if startup == '*' or (startup is True and not ioloop_running(self.ioloop)):
            self.function()

    def run(self):
        '''Run task. Then set up next callback.'''
        app_log.info('Running %s', self.name)
        try:
            self.result = self.function()
        finally:
            # Do not schedule if stopped (e.g. via self.stop())
            if self.callback is not None:
                self._schedule()

    def stop(self):
        '''Suspend task, clearing any pending callbacks'''
        if self.callback is not None:
            app_log.debug('Stopping %s', self.name)
            self.ioloop.remove_timeout(self.callback)
            self.callback = None

    def _schedule(self):
        '''Schedule next run. Do NOT call twice: creates two callbacks'''
        delay = self.cron.next(default_utc=False)
        if delay is not None:
            app_log.debug('Scheduling %s after %.0fs', self.name, delay)
            self.callback = self.ioloop.call_later(delay, self.run)
        else:
            app_log.debug('No further schedule for %s', self.name)
