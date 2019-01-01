import os
import inspect
import pandas as pd
from tornado.gen import coroutine, Return
from gramex.config import locate, app_log
from sklearn.externals import joblib
from sklearn.preprocessing import StandardScaler

# Expose joblob.load via gramex.ml
load = joblib.load                      # noqa


class Classifier(object):
    '''
        :arg data DataFrame: data to train / re-train the model with
        :arg model_class str: model class to use (default: ``sklearn.naive_bayes.BernoulliNB``)
        :arg model_kwargs dict: kwargs to pass to model class constructor (defaults: ``{}``)
        :arg output str: output column name (default: last column in training data)
        :arg input list: input column names (default: all columns except ``output``)
        :arg labels list: list of possible output values (default: unique ``output`` in training)
    '''

    def __init__(self, **kwargs):
        vars(self).update(kwargs)
        self.model_class = kwargs.get('model_class', 'sklearn.naive_bayes.BernoulliNB')
        self.trained = False  # Boolean Flag

    def __str__(self):
        return repr(vars(self))

    def update_params(self, params):
        model_keys = ('model_class', 'url', 'input', 'output', 'trained', 'query', 'model_kwargs')
        model_params = {k: v[0] if isinstance(v, list) and k != 'input' else v
                        for k, v in params.items() if k in model_keys}
        if model_params:
            self.trained = params.get('trained', False)
        vars(self).update(model_params)

    def train(self, data):
        '''
        :arg data DataFrame: data to train / re-train the model with
        :arg model_class str: model class to use (default: ``sklearn.naive_bayes.BernoulliNB``)
        :arg model_kwargs dict: kwargs to pass to model class constructor (defaults: ``{}``)
        :arg output str: output column name (default: last column in training data)
        :arg input list: input column names (default: all columns except ``output``)
        :arg labels list: list of possible output values (default: unique ``output`` in training)

        Notes:
        - If model has already been trained, extend the model. Else create it
        '''
        self.output = vars(self).get('output', data.columns[-1])
        self.input = vars(self).get('input', list(data.columns[:-1]))
        self.model_kwargs = vars(self).get('model_kwargs', {})
        self.labels = vars(self).get('labels', None)
        # If model_kwargs have changed since we trained last, re-train model.
        if not self.trained and hasattr(self, 'model'):
            vars(self).pop('model')
        if not hasattr(self, 'model'):
            # Split it into input (x) and output (y)
            x, y = data[self.input], data[self.output]
            # Transform the data
            self.scaler = StandardScaler()
            self.scaler.fit(x)
            # Train the classifier. Partially, if possible
            try:
                clf = locate(self.model_class)(**self.model_kwargs)
            except TypeError:
                raise ValueError('{0} is not a correct model class'.format(self.model_class))
            if self.labels and hasattr(clf, 'partial_fit'):
                try:
                    clf.partial_fit(self.scaler.transform(x),
                                    y, classes=self.labels)
                except AttributeError:
                    raise ValueError('{0} does not support partial fit'.format(self.model_class))
            else:
                clf.fit(self.scaler.transform(x), y)
            self.model = clf

        # Extend the model
        else:
            x, y = data[self.input], data[self.output]
            classes = set(self.model.classes_)
            classes |= set(y)
            self.model.partial_fit(self.scaler.transform(x), y)

    def predict(self, data):
        '''
        Return a Series that has the results of the classification of data
        '''
        # Convert list of lists or numpy arrays into DataFrame. Assume columns are as per input
        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data, columns=self.input)
        # Take only trained input columns
        return self.model.predict(self.scaler.transform(data))

    def save(self, path):
        '''
        Serializes the model and associated parameters
        '''
        joblib.dump(self, path, compress=9)


def _conda_r_home():
    '''
    Returns the R home directory for Conda R if it is installed. Else None.

    Typically, people install Conda AND R (in any order), and use the system R
    (rather than the conda R) by placing it before Conda in the PATH.

    But the system R does not work with Conda rpy2. So we check if Conda R
    exists and return its path, so that it can be used as R_HOME.
    '''
    try:
        from conda.base.context import context
    except ImportError:
        app_log.error('Anaconda not installed. Cannot use Anaconda R')
        return None
    r_home = os.path.normpath(os.path.join(context.root_prefix, 'lib', 'R'))
    if os.path.isdir(os.path.join(r_home, 'bin')):
        return r_home
    app_log.error('Anaconda R not installed')
    return None


def r(code=None, path=None, rel=True, conda=True, convert=True,
      repo='https://cran.microsoft.com/', **kwargs):
    '''
    Runs the R script and returns the result.

    :arg str code: R code to execute.
    :arg str path: R script path. Cannot be used if code is specified
    :arg bool rel: True treats path as relative to the caller function's file
    :arg bool conda: True overrides R_HOME to use the Conda R
    :arg bool convert: True converts R objects to Pandas and vice versa
    :arg str repo: CRAN repo URL

    All other keyword arguments as passed as parameters
    '''
    # Use Conda R if possible
    if conda:
        r_home = _conda_r_home()
        if r_home:
            os.environ['R_HOME'] = r_home

    # Import the global R session
    try:
        from rpy2.robjects import r, pandas2ri, globalenv
    except ImportError:
        app_log.error('rpy2 not installed. Run "conda install rpy2"')
        raise
    except RuntimeError:
        app_log.error('Cannot find R. Set R_HOME env variable')
        raise

    # Set a repo so that install.packages() need not ask for one
    r('local({r <- getOption("repos"); r["CRAN"] <- "%s"; options(repos = r)})' % repo)

    # Activate or de-activate automatic conversion
    # https://pandas.pydata.org/pandas-docs/version/0.22.0/r_interface.html
    if convert:
        pandas2ri.activate()
    else:
        pandas2ri.deactivate()

    # Pass all other kwargs as global environment variables
    for key, val in kwargs.items():
        globalenv[key] = val

    if code and path:
        raise RuntimeError('Use r(code=) or r(path=...), not both')
    if path:
        # if rel=True, load path relative to parent directory
        if rel:
            stack = inspect.getouterframes(inspect.currentframe(), 2)
            folder = os.path.dirname(os.path.abspath(stack[1][1]))
            path = os.path.join(folder, path)
        result = r.source(path, chdir=True)
        # source() returns a withVisible: $value and $visible. Use only the first
        result = result[0]
    else:
        result = r(code)

    return result


def groupmeans(data, groups, numbers, cutoff=.01, quantile=.95, minsize=None,
               weight=None):
    '''
    Yields the significant differences in average between every pair of
    groups and numbers.

    Parameters
    ----------
    data : pandas.DataFrame
    groups : non-empty iterable containing category column names in data
    numbers : non-empty iterable containing numeric column names in data
    cutoff : ignore anything with prob > cutoff.
        cutoff=None ignores significance checks, speeding it up a LOT.
    quantile : number that represents target improvement. Defaults to .95.
        The ``diff`` returned is the % impact of everyone moving to the 95th
        percentile
    minsize : each group should contain at least minsize values.
        If minsize=None, automatically set the minimum size to
        1% of the dataset, or 10, whichever is larger.
    '''
    from scipy.stats.mstats import ttest_ind
    if minsize is None:
        minsize = max(len(data.index) // 100, 10)

    if weight is None:
        means = data[numbers].mean()
    else:
        means = weighted_avg(data, numbers, weight)
    results = []
    for group in groups:
        grouped = data.groupby(group, sort=False)
        if weight is None:
            ave = grouped[numbers].mean()
        else:
            ave = grouped.apply(lambda v: weighted_avg(v, numbers, weight))
        ave['#'] = sizes = grouped.size()
        # Each group should contain at least minsize values
        biggies = sizes[sizes >= minsize].index
        # ... and at least 2 groups overall, to compare.
        if len(biggies) < 2:
            continue
        for number in numbers:
            if number == group:
                continue
            sorted_cats = ave[number][biggies].dropna().sort_values()
            if len(sorted_cats) < 2:
                continue
            lo = data[number][grouped.groups[sorted_cats.index[0]]].values
            hi = data[number][grouped.groups[sorted_cats.index[-1]]].values
            _, prob = ttest_ind(
                pd.np.ma.masked_array(lo, pd.np.isnan(lo)),
                pd.np.ma.masked_array(hi, pd.np.isnan(hi))
            )
            if prob > cutoff:
                continue
            results.append({
                'group': group,
                'number': number,
                'prob': prob,
                'gain': sorted_cats.iloc[-1] / means[number] - 1,
                'biggies': ave.loc[biggies][number],
                'means': ave[[number, '#']].sort_values(number),
            })

    results = pd.DataFrame(results)
    if len(results) > 0:
        results = results.set_index(['group', 'number'])
    return results.reset_index()  # Flatten multi-index.


def weighted_avg(data, numeric_cols, weight):
    '''
    Computes weighted average for specificied columns
    '''
    sumprod = data[numeric_cols].multiply(data[weight], axis=0).sum()
    return sumprod / data[weight].sum()


def _google_translate(q, source, target, key):
    import requests
    api = 'https://translation.googleapis.com/language/translate/v2'
    params = {'q': q, 'target': target, 'source': source, 'key': key}
    try:
        r = requests.post(api, data=params)
    except requests.RequestException:
        return app_log.exception('Cannot connect to Google Translate')
    response = r.json()
    if 'error' in response:
        return app_log.error('Google Translate API error: %s', response['error'])
    return {
        'q': q,
        't': [t['translatedText'] for t in response['data']['translations']],
        'source': [source] * len(q),
        'target': [target] * len(q),
    }


translate_api = {
    'google': _google_translate
}


def translate(*q, **kwargs):
    '''
    Translate strings using the Google Translate API. Example::

        translate('Hello', 'World', source='en', target='de', key='...')

    returns a DataFrame::

        source  target  q       t
        en      de      Hello   ...
        en      de      World   ...

    The results can be cached via a ``cache={...}`` that has parameters for
    :py:func:`gramex.data.filter`. Example::

        translate('Hello', key='...', cache={'url': 'translate.xlsx'})

    :arg str q: one or more strings to translate
    :arg str source: 2-letter source language (e.g. en, fr, es, hi, cn, etc). default: en
    :arg str target: 2-letter target language (e.g. en, fr, es, hi, cn, etc). default: hi
    :arg str key: Google Translate API key
    :arg dict cache: kwargs for :py:func:`gramex.data.filter`. Has keys such as
        url (required), table (for databases), sheet_name (for Excel), etc.

    Reference: https://cloud.google.com/translate/docs/apis
    '''
    import gramex.data

    source = kwargs.get('source', 'en')
    target = kwargs.get('target', 'nl')
    key = kwargs.get('key', None)
    cache = kwargs.get('cache', None)
    api = kwargs.get('api', 'google')

    if cache is not None:
        if not isinstance(cache, dict):
            raise ValueError('cache= must be a FormHandler dict config, not %r' % cache)

    # Store data in cache with fixed columns: source, target, q, t
    result = pd.DataFrame(columns=['source', 'target', 'q', 't'])
    if not q:
        return result

    # Fetch from cache, if any
    if cache:
        try:
            result = gramex.data.filter(args={
                'q': q,
                'source': [source] * len(q),
                'target': [target] * len(q),
            }, **cache)
        except Exception:
            app_log.warning('Cannot fetch from translate cache: %r', dict(cache))
        # Remove already cached  results from q
        q = [v for v in q if v not in set(result.get('q', []))]

    if len(q):
        new_data = translate_api[api](q, source, target, key)
        if new_data is not None:
            result = result.append(pd.DataFrame(new_data), sort=False)
            if cache:
                gramex.data.insert(id=['source', 'target', 'q'], args=new_data, **cache)

    return result


@coroutine
def translater(handler, source='en', target='nl', key=None, cache=None, api='google'):
    args = handler.argparse(
        q={'nargs': '*', 'default': []},
        source={'default': source},
        target={'default': target}
    )
    import gramex
    result = yield gramex.service.threadpool.submit(
        translate, *args.q, source=args.source, target=args.target, key=key, cache=cache, api=api)

    # TODO: support gramex.data.download features
    handler.set_header('Content-Type', 'application/json; encoding="UTF-8"')
    raise Return(result.to_json(orient='records'))


# Gramex 1.48 spelt translater as translator. Accept both spellings.
translator = translater
