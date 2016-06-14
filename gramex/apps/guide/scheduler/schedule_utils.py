import logging
import datetime


def log_time():
    now = datetime.datetime.now()
    logging.info('Time is {:%H:%M:%S}'.format(now))
