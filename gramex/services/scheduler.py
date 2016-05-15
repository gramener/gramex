'Gramex scheduling service'

import logging
import tornado.ioloop
from crontab import CronTab
from ..transforms import build_transform


class Task(object):
    'Run a task. Then schedule it at the next occurrance.'

    def __init__(self, name, schedule, threadpool, ioloop=None):
        '''
        Create a new task based on a schedule in ioloop (default to current).

        The schedule configuration accepts:

        - startup: True to run at startup
        - minutes, hours, dates, months, weekdays, years: cron schedule
        - thread: True to run in a separate thread
        '''
        self.name = name
        self.function = build_transform(schedule, vars={})
        self.ioloop = ioloop or tornado.ioloop.IOLoop.current()
        self.callback = None

        if schedule.get('thread'):
            fn = self.function

            def on_done(future):
                exception = future.exception(timeout=0)
                if exception:
                    logging.error('%s (thread): %s', name, exception)

            self.function = lambda: threadpool.submit(fn).add_done_callback(on_done)

        # Run on schedule if any of the schedule periods are specified
        periods = 'minutes hours dates months weekdays years'.split()
        if any(schedule.get(key) for key in periods):
            # Convert all valid values into strings (e.g. 30 => '30'), and ignore any spaces
            cron = (str(schedule.get(key, '*')).replace(' ', '') for key in periods)
            self.cron = CronTab(' '.join(cron))
            self._schedule()
        elif not schedule.get('startup'):
            logging.warn('schedule: %s has no schedule nor startup', name)

        # Run now if the task is to be run on startup. Don't re-run if the config was reloaded
        if schedule.get('startup') and not self.ioloop._running:
            self.function()

    def run(self):
        'Run task. Then set up next callback.'
        logging.info('Running %s', self.name)
        try:
            self.function()
        finally:
            # Do not schedule if stopped (e.g. via self.stop())
            if self.callback is not None:
                self._schedule()

    def stop(self):
        'Suspend task, clearing any pending callbacks'
        if self.callback is not None:
            logging.debug('Stopping %s', self.name)
            self.ioloop.remove_timeout(self.callback)
            self.callback = None

    def _schedule(self):
        'Schedule next run. Do NOT call twice: creates two callbacks'
        delay = self.cron.next()
        logging.debug('Scheduling %s after %.0fs', self.name, delay)
        self.callback = self.ioloop.call_later(delay, self.run)


def setup(schedule, tasks, threadpool, ioloop=None):
    'Create tasks running on ioloop for the given schedule, store it in tasks'
    for name, task in tasks.items():
        task.stop()
    tasks.clear()
    for name, sched in schedule.items():
        try:
            tasks[name] = Task(name, sched, threadpool, ioloop)
        except Exception as e:
            logging.exception(e)
