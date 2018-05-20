import os
import unittest
import gramex.ml
import pandas as pd
from sklearn.svm import SVC
from sklearn.naive_bayes import BernoulliNB
from gramex.ml import Classifier

from nose.tools import eq_, ok_
from . import folder


class TestClassifier(unittest.TestCase):
    model_path = os.path.join(folder, 'model.pkl')

    def test_01_train(self):
        path = os.path.join(folder, 'iris.csv')
        data = pd.read_csv(path, encoding='utf-8')

        # Model can be trained without specifying a model class, input or output
        model1 = Classifier()
        model1.train(data)
        ok_(isinstance(model1.model, BernoulliNB))
        eq_(model1.input, data.columns[:4].tolist())
        eq_(model1.output, data.columns[-1])

        # Train accepts explicit model_class, model_kwargs, input and output
        model2 = Classifier()
        inputs = ['petal_length', 'petal_width', 'sepal_length', 'sepal_width']
        model2.train(
            data,                                 # DataFrame with input & output columns
            model_class='sklearn.svm.SVC',        # Any sklearn model works
            model_kwargs={'kernel': 'sigmoid'},   # Optional model parameters
            input=inputs,
            output='species'
        )
        eq_(model2.input, inputs)
        eq_(model2.output, model1.output)
        ok_(isinstance(model2.model, SVC))
        eq_(model2.model.kernel, 'sigmoid')

        # Test predictions. Note: this is manually crafted. If it fails, change the test case
        result = model1.predict([
            {'sepal_length': 5, 'sepal_width': 3, 'petal_length': 1.5, 'petal_width': 0},
            {'sepal_length': 5, 'sepal_width': 2, 'petal_length': 5.0, 'petal_width': 1},
            {'sepal_length': 6, 'sepal_width': 3, 'petal_length': 4.8, 'petal_width': 2},
        ])
        eq_(result.tolist(), ['setosa', 'versicolor', 'virginica'])

        # Test saving
        expected = model1.predict(data[model1.input])
        if os.path.exists(self.model_path):
            os.remove(self.model_path)
        model1.save(self.model_path)
        actuals = gramex.ml.load(self.model_path).predict(data[model1.input])
        eq_(actuals.tolist(), expected.tolist())

    def test_02_load(self):
        model = gramex.ml.load(self.model_path)
        result = model.predict([{
            'sepal_length': 5.7,
            'sepal_width': 4.4,
            'petal_length': 1.5,
            'petal_width': 0.4,
        }])
        eq_(result.tolist(), ['setosa'])

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.model_path):
            os.remove(cls.model_path)
