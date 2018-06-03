import os
import json
import tornado.gen
import gramex
import gramex.ml

folder = os.path.dirname(os.path.abspath(__file__))


def prime(handler):
    args = handler.argparse(n={'type': int, 'default': 100})
    gramex.ml.r(path='sieve.R')
    primes = gramex.ml.r('sieve(n)', n=args.n).tolist()
    return json.dumps(primes)


def plot(handler):
    path = gramex.ml.r(path='plot.R')
    return gramex.cache.open(path[0], 'bin')


@tornado.gen.coroutine
def plot_async(handler):
    path = yield gramex.service.threadpool.submit(
        gramex.ml.r,
        path=os.path.join(folder, 'plot.R'),
    )
    raise tornado.gen.Return(gramex.cache.open(path[0], 'bin'))
