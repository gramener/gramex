import pandas as pd
from gramex.config import locate
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
            # Split it into input (X) and output (y)
            X, y = data[self.input], data[self.output]

            # Transform the data
            self.scaler = StandardScaler()
            self.scaler.fit(X)

            # Train the classifier. Partially, if possible
            clf = locate(model_class)(**model_kwargs)
            if labels is not None and hasattr(clf, 'partial_fit'):
                clf.partial_fit(self.scaler.transform(X), y, classes=labels)
            else:
                clf.fit(self.scaler.transform(X), y)
            self.model = clf

        # Extend the model
        else:
            X, y = data[self.input], data[self.output]
            classes = set(self.model.classes_)
            classes |= set(y)
            self.model.partial_fit(self.scaler.transform(X), y)

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
