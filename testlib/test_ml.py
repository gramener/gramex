# coding=utf-8
import os
import json
import unittest
import pandas as pd
from sklearn.svm import SVC
from sklearn.naive_bayes import BernoulliNB
import gramex.ml
import gramex.cache
from nose.tools import eq_, ok_
from pandas.util.testing import assert_frame_equal as afe
from . import folder


class TestClassifier(unittest.TestCase):
    model_path = os.path.join(folder, 'model.pkl')

    def test_01_train(self):
        path = os.path.join(folder, 'iris.csv')
        data = pd.read_csv(path, encoding='utf-8')

        # Model can be trained without specifying a model class, input or output
        model1 = gramex.ml.Classifier()
        model1.train(data)
        ok_(isinstance(model1.model, BernoulliNB))
        eq_(model1.input, data.columns[:4].tolist())
        eq_(model1.output, data.columns[-1])

        # Train accepts explicit model_class, model_kwargs, input and output
        inputs = ['petal_length', 'petal_width', 'sepal_length', 'sepal_width']
        model2 = gramex.ml.Classifier(
            model_class='sklearn.svm.SVC',    # Any sklearn model
            # Optional model parameters
            model_kwargs={'kernel': 'sigmoid'},
            input=inputs,
            output='species')
        model2.train(data)                   # DataFrame with input & output columns
        eq_(model2.input, inputs)
        eq_(model2.output, model1.output)
        ok_(isinstance(model2.model, SVC))
        eq_(model2.model.kernel, 'sigmoid')

        # Test predictions. Note: this is manually crafted. If it fails, change the test case
        result = model1.predict([
            {'sepal_length': 5, 'sepal_width': 3,
                'petal_length': 1.5, 'petal_width': 0},
            {'sepal_length': 5, 'sepal_width': 2,
                'petal_length': 5.0, 'petal_width': 1},
            {'sepal_length': 6, 'sepal_width': 3,
                'petal_length': 4.8, 'petal_width': 2},
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

    # def test_linear_model_with_controlled_data(self):
    #     ...

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.model_path):
            os.remove(cls.model_path)


class TestAutolyse(unittest.TestCase):
    path = os.path.join(folder, 'auto_test.csv')
    df = gramex.cache.open(path, encoding='utf-8')
    opener = lambda h: json.load(h, parse_float=lambda x: round(float(x), 4))  # noqa
    results = gramex.cache.open(os.path.join(folder, 'autolyse.json'),
                                callback=gramex.cache.opener(opener))

    def base(self, groups, numbers, key):
        dff = gramex.ml.groupmeans(self.df, groups, numbers)
        result = {} if dff.empty else json.loads(dff.iloc[0].to_json(double_precision=4))
        self.assertDictEqual(result, self.results[key], f'Failed: {key}')

    def test_groupmeans(self):
        self.base(['Aä'], ['Xfloaté'], 'groupmeans_unicode_col_names')
        self.base(['Régions'], ['`Numbers1'], 'numbers_sparse')
        self.base(['Régions'], ['FloatsWithZero'], 'floats_col_sparse')
        self.base(['Dätes'], ['Numbérs'], 'col_only_dates')
        self.base(['IntCats'], ['`Numbers'], 'only_ints')
        self.base(
            ['GroupWith1Name'],
            ['Xfloaté', 'Yfloaté', 'Zfloaté', 'Numbérs', '`Numbers'],
            'non_normal_dist')


# Map (q, source, target) -> (detected source, translation)
_translate = {
    ('Apple', None, 'nl'): ('en', 'appel'),
    ('Orange', None, 'nl'): ('en', 'Oranje'),
    ('Apple', 'en', 'nl'): ('en', 'appel'),
    ('Orange', 'en', 'nl'): ('en', 'Oranje'),
    ('Apple', 'en', 'de'): ('en', 'Apfel'),
    ('Orange', 'en', 'de'): ('en', 'Orange'),
    ('apfel', '', 'en'): ('de', 'apple'),           # used by tests/test_translater
}
_translate_count = []


def translate_mock(q, source, target, key='...'):
    '''Mock the Google Translate API results'''
    _translate_count.append(1)
    vals = [_translate[item, source, target] for item in q]
    return {
        'source': [v[0] for v in vals],
        'target': [target] * len(q),
        'q': q,
        't': [v[1] for v in vals],
    }


class TestTranslate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = os.path.join(folder, 'translate.xlsx')
        gramex.ml.translate_api['mock'] = translate_mock

    def test_translate(self):
        def check(q, result, **kwargs):
            kwargs['api'] = 'mock'
            actual = gramex.ml.translate(*q, **kwargs)
            expected = pd.DataFrame([
                {'source': item[0], 'target': item[1], 'q': item[2], 't': item[3]}
                for item in result
            ])
            actual.index = expected.index
            afe(actual, expected, check_like=True)

        check(['Apple'], [
            ['en', 'nl', 'Apple', 'appel']
        ], target='nl')
        check(['Apple', 'Orange'], [
            ['en', 'nl', 'Apple', 'appel'],
            ['en', 'nl', 'Orange', 'Oranje']
        ], target='nl')
        check(['Apple', 'Orange'], [
            ['en', 'de', 'Apple', 'Apfel'],
            ['en', 'de', 'Orange', 'Orange']
        ], source='en', target='de')
        check(['Orange', 'Apple'], [
            ['en', 'de', 'Orange', 'Orange'],
            ['en', 'de', 'Apple', 'Apfel'],
        ], source='en', target='de')

        if os.path.exists(self.cache):
            os.remove(self.cache)

        cache = {'url': self.cache}
        count = len(_translate_count)
        check(['Apple'], [['en', 'nl', 'Apple', 'appel']], target='nl', cache=cache)
        eq_(len(_translate_count), count + 1)
        check(['Apple'], [['en', 'nl', 'Apple', 'appel']], target='nl', cache=cache)
        eq_(len(_translate_count), count + 1)
        check(['Apple'], [['en', 'de', 'Apple', 'Apfel']], source='en', target='de', cache=cache)
        eq_(len(_translate_count), count + 2)
        check(['Apple'], [['en', 'de', 'Apple', 'Apfel']], source='en', target='de', cache=cache)
        eq_(len(_translate_count), count + 2)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.cache):
            os.remove(cls.cache)
