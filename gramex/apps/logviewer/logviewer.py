from glob import glob
from gramex import conf
from tornado.gen import coroutine
import pandas as pd
import gramex.data
import gramex.cache

LIMIT = 10000


@coroutine
def get_data(handler):
    log_file = conf.log.handlers.requests.filename
    log_files = glob(log_file + '*')
    columns = conf.log.handlers.requests['keys']
    data = pd.concat([
        gramex.cache.open(file, 'csv', names=columns)
        for file in log_files
    ])
    data = gramex.data.filter(data, args=handler.args)
    # TODO: optimize. What if the logs are huge?
    data = data.sort_values('time', ascending=False).head(LIMIT)
    return gramex.data.download(data, format='csv')
