'Gramex scheduling service'

import logging
import tornado.ioloop
from crontab import CronTab
from zope.dottedname.resolve import resolve


class Task(object):
    'Run a task. Then schedule it at the next occurrance.'

    _units = 'minutes hours dates months weekdays years'.split()

    def __init__(self, name, schedule, ioloop=None):
        'Create a new task based on a schedule in ioloop (default to current)'
        self.name = name
        self.function = resolve(schedule.function)
        self.kwargs = schedule.get('kwargs', {})
        cron = (str(schedule.get(key, '*')).replace(' ', '') for key in self._units)
        self.cron = CronTab(' '.join(cron))
        self.ioloop = ioloop or tornado.ioloop.IOLoop.current()
        # Run now if the task is to be run on startup, and app hasn't started
        if schedule.get('startup') and not self.ioloop._running:
            self.callback = self.ioloop.call_later(0, self.run)
        else:
            self._schedule()

    def run(self):
        'Run task. Then set up next callback.'
        logging.info('Running %s', self.name)
        try:
            self.function(**self.kwargs)
        finally:
            # Do not schedule if self.function has stopped the task
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


def setup(schedule, tasks, ioloop=None):
    'Create tasks running on ioloop for the given schedule, store it in tasks'
    for name, task in tasks.items():
        task.stop()
    tasks.clear()
    for name, sched in schedule.items():
        try:
            tasks[name] = Task(name, sched, ioloop)
        except Exception as e:
            logging.exception(e)
