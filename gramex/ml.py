import os
import inspect
import pandas as pd
from gramex.config import locate, app_log
from sklearn.externals import joblib
from sklearn.preprocessing import StandardScaler

# Expose joblob.load via gramex.ml
load = joblib.load                      # noqa


class Classifier(object):
    '''
    TODO
    '''
    def train(self, data, model_class='sklearn.naive_bayes.BernoulliNB', model_kwargs={},
              output=None, input=None, labels=None):
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
        self.output = output if output is not None else data.columns[-1]
        self.input = input
        if self.input is None:
            self.input = list(data.columns)
            self.input.remove(self.output)

        # If model does not exist, create model
        if not hasattr(self, 'model'):
            # Split it into input (x) and output (y)
            x, y = data[self.input], data[self.output]

            # Transform the data
            self.scaler = StandardScaler()
            self.scaler.fit(x)

            # Train the classifier. Partially, if possible
            clf = locate(model_class)(**model_kwargs)
            if labels is not None and hasattr(clf, 'partial_fit'):
                clf.partial_fit(self.scaler.transform(x), y, classes=labels)
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
        data = data[self.input]
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
