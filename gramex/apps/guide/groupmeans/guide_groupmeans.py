import os
import requests
import gramex.ml
import tornado.gen


def autolyse_add(data):
    cols = ['Maths %', 'Reading %', 'Science %', 'Social %']
    data[cols] = data[cols].fillna(data[cols].mean()).round(2)
    data['Total %'] = data[cols].mean(1).round(2)
    return data


def autolyse(data, handler):
    args = handler.argparse(
        groups={'nargs': '*', 'default': []},
        numbers={'nargs': '*', 'default': []},
        cutoff={'type': float, 'default': .01},
        quantile={'type': float, 'default': .95},
        minsize={'type': float, 'default': None},
        weight={'type': float, 'default': None})
    x = gramex.ml.groupmeans(data, args.groups, args.numbers,
                             args.cutoff, args.quantile, args.weight)
    for col in x.select_dtypes(include='object'):
        x[col] = x[col].astype('str')
    return x


@tornado.gen.coroutine
def autolyse_download(handler):
    '''Downloads a file from a url specified in query-parameter'''
    _file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nas.csv')
    if os.path.exists(_file) and os.path.isfile(_file):
        return 'File Exists'
    url = 'https://cloud.gramener.com/f/c43f815486e648f482c7/?dl=1'
    r = requests.get(url, stream=True)
    with open(_file, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    return 'Downloaded'
