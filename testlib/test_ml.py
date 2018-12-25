# coding=utf-8
import os
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

    def base(self, groups, numbers, check_string):
        eq_(gramex.ml.groupmeans(self.df, groups, numbers).to_json(), check_string)

    def test_groupmeans_unicode_col_names(self):
        '''Unicode column names and categorical column values. '''
        autolysis_string = ''.join([
            '{"group":{"0":"A\\u00e4"},"number":{"0":"Xfloat\\u00e9"},"biggies":{',
            '"0":{"A0":0.5147290217,"A1":0.43041003,"A10":0.4747865202,"A11":0.4814285354,',
            '"A12":0.4106736393,"A13":0.6440158478,"A14":0.4499212197,"A15":0.5564064238,',
            '"A16":0.5736623215,"A17":0.4890015995,"A18":0.6202282336,"A2":0.4501432661,',
            '"A3":0.4593324615,"A4":0.4611977511,"A5":0.4260692432,"A6":0.410675212,',
            '"A7":0.560958454,"A8":0.4463740271,"A9":0.4476561046}},"gain":{"0":0.3144803738},',
            '"means":{"0":{"Xfloat\\u00e9":{"A12":0.4106736393,"A6":0.410675212,',
            '"A5":0.4260692432,',
            '"A1":0.43041003,"A8":0.4463740271,"A9":0.4476561046,"A14":0.4499212197,',
            '"A2":0.4501432661,"A3":0.4593324615,"A4":0.4611977511,"A10":0.4747865202,',
            '"A11":0.4814285354,"A17":0.4890015995,"A0":0.5147290217,"A15":0.5564064238,',
            '"A7":0.560958454,"A16":0.5736623215,"A18":0.6202282336,"A13":0.6440158478},',
            '"#":{"A12":21,"A6":21,"A5":21,"A1":21,"A8":21,"A9":21,"A14":21,"A2":21,',
            '"A3":21,"A4":21,"A10":21,"A11":21,"A17":21,"A0":22,"A15":21,"A7":21,"A16":21,',
            '"A18":21,"A13":21}}},"prob":{"0":0.0046080226}}'
        ])
        self.base([u'Aä'], [u'Xfloaté'], autolysis_string)

    def test_numbers_sparse(self):
        autolysis_string = ''.join([
            '{"group":{"0":"R\\u00e9gions"},"number":{"0":"`Numbers1"},"biggies":{"0":{',
            '"IL":2.0,"NO":2.3333333333,"CE":1.6666666667,"Bretagne":2.5,',
            '"\\u00cele-de-France":2.5833333333,"Aquitaine":2.75,"Picardie":1.75,',
            '"PR":2.3333333333,"Bourgogne":1.5,"HA":3.5,"BR":3.0,"PA":1.1666666667,',
            '"Nord-Pas-de-Calais":3.0,"Pays de la Loire":5.0,',
            '"Provence-Alpes-C\\u00f4te d\'Azur":4.5}},"gain":{"0":0.9157088123},',
            '"means":{"0":{"`Numbers1":{"BO":0.0,"Lorraine":0.0,"PI":0.0,"PO":0.0,',
            '"BA":0.0,"Centre":1.0,"PA":1.1666666667,"CH":1.5,"Bourgogne":1.5,',
            '"CE":1.6666666667,"Picardie":1.75,"IL":2.0,"LO":2.0,"NO":2.3333333333,',
            '"PR":2.3333333333,"AU":2.5,"Poitou-Charentes":2.5,"Bretagne":2.5,',
            '"\\u00cele-de-France":2.5833333333,"Aquitaine":2.75,"Nord-Pas-de-Calais":3.0,',
            '"BR":3.0,"HA":3.5,"AL":4.0,"Provence-Alpes-C\\u00f4te d\'Azur":4.5,',
            '"Pays de la Loire":5.0,"Haute-Normandie":5.0,"Languedoc-Roussillon":6.0,',
            '"MI":6.0,"AQ":6.5,"Alsace":8.0},"#":{"BO":4,"Lorraine":8,"PI":4,"PO":4,"BA":4,',
            '"Centre":8,"PA":24,"CH":8,"Bourgogne":16,"CE":12,"Picardie":16,"IL":36,"LO":4,',
            '"NO":24,"PR":24,"AU":8,"Poitou-Charentes":8,"Bretagne":16,"\\u00cele-de-France":48,',
            '"Aquitaine":16,"Nord-Pas-de-Calais":12,"BR":16,"HA":16,"AL":4,',
            '"Provence-Alpes-C\\u00f4te d\'Azur":16,"Pays de la Loire":12,"Haute-Normandie":8,',
            '"Languedoc-Roussillon":8,"MI":4,"AQ":8,"Alsace":4}}},"prob":{"0":0.0004737537}}'
        ])
        self.base([u'Régions'], [u'`Numbers1'], autolysis_string)

    def test_non_normal_dist(self):
        self.base(['GroupWith1Name'], [u'Xfloaté', u'Yfloaté',
                                       u'Zfloaté', u'Numbérs', u'`Numbers'], '{"index":{}}')

    def test_only_ints(self):
        autolysis_string = ''.join([
            '{"group":{"0":"IntCats"},"number":{"0":"`Numbers"},"biggies":{"0":{"1":5.40625,',
            '"3":5.625,"4":4.4722222222}},"gain":{"0":0.0943579767},"means":{"0":{',
            '"`Numbers":{"4":4.4722222222,"1":5.40625,"3":5.625},"#":{"4":144,"1":128,',
            '"3":128}}},"prob":{"0":0.0002885852}}'
        ])
        self.base(['IntCats'], ['`Numbers'], autolysis_string)

    def test_col_only_dates(self):
        self.base([u'Dätes'], [u'Numbérs'], '{"index":{}}')

    def test_floats_col_sparse(self):
        autolysis_string = ''.join([
            '{"group":{"0":"R\\u00e9gions"},"number":{"0":"FloatsWithZero"},"biggies":{"0":{',
            '"IL":0.012747739,"NO":-0.0352614186,"CE":0.0,"Bretagne":0.0058930111,',
            '"\\u00cele-de-France":0.0109352419,"Aquitaine":0.1169812762,',
            '"Picardie":-0.0470094696,"PR":0.0432100751,"Bourgogne":0.0563597848,',
            '"HA":0.005033869,"BR":0.072658035,"PA":0.0747856489,',
            '"Nord-Pas-de-Calais":0.0547388023,"Pays de la Loire":0.035744271,',
            '"Provence-Alpes-C\\u00f4te d\'Azur":-0.1231877406}},"gain":{"0":10.4323598287},',
            '"means":{"0":{"FloatsWithZero":{"PO":-0.2453796284,"Haute-Normandie":-0.2237780122,',
            '"BA":-0.1698339283,"AU":-0.1614843193,',
            '"Provence-Alpes-C\\u00f4te d\'Azur":-0.1231877406,"Centre":-0.0720992128,',
            '"AQ":-0.0665866815,"Picardie":-0.0470094696,"NO":-0.0352614186,"LO":0.0,',
            '"PI":0.0,"CE":0.0,"AL":0.0,"MI":0.0,"HA":0.005033869,"Bretagne":0.0058930111,',
            '"\\u00cele-de-France":0.0109352419,"IL":0.012747739,"Pays de la Loire":0.035744271,',
            '"CH":0.0377686544,"PR":0.0432100751,"Nord-Pas-de-Calais":0.0547388023,',
            '"Bourgogne":0.0563597848,"Languedoc-Roussillon":0.0726263707,"BR":0.072658035,',
            '"PA":0.0747856489,"Lorraine":0.115573334,"Aquitaine":0.1169812762,',
            '"Poitou-Charentes":0.150149774,"Alsace":0.1766370569,"BO":0.1967609903},',
            '"#":{"PO":4,"Haute-Normandie":8,"BA":4,"AU":8,',
            '"Provence-Alpes-C\\u00f4te d\'Azur":16,"Centre":8,"AQ":8,"Picardie":16,"NO":24,',
            '"LO":4,"PI":4,"CE":12,"AL":4,"MI":4,"HA":16,"Bretagne":16,"\\u00cele-de-France":48,',
            '"IL":36,"Pays de la Loire":12,"CH":8,"PR":24,"Nord-Pas-de-Calais":12,',
            '"Bourgogne":16,"Languedoc-Roussillon":8,"BR":16,"PA":24,"Lorraine":8,',
            '"Aquitaine":16,"Poitou-Charentes":8,"Alsace":4,"BO":4}}},"prob":{"0":0.0000015713}}'
        ])
        self.base([u'Régions'], ['FloatsWithZero'], autolysis_string)


_translate = {
    ('Apple', 'en', 'nl'): 'appel',
    ('Orange', 'en', 'nl'): 'Oranje',
    ('Apple', 'en', 'de'): 'Apfel',
    ('Orange', 'en', 'de'): 'Orange',
}
_translate_count = []


def translate_mock(q, source, target, key='...'):
    '''Mock the Google Translate API results'''
    _translate_count.append(1)
    t = [_translate[item, source, target] for item in q]
    n = len(q)
    return {'q': q, 't': t, 'source': [source] * n, 'target': [target] * n}


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
        ])
        check(['Apple', 'Orange'], [
            ['en', 'nl', 'Apple', 'appel'],
            ['en', 'nl', 'Orange', 'Oranje']
        ])
        check(['Apple', 'Orange'], [
            ['en', 'de', 'Apple', 'Apfel'],
            ['en', 'de', 'Orange', 'Orange']
        ], source='en', target='de')

        if os.path.exists(self.cache):
            os.remove(self.cache)

        cache = {'url': self.cache}
        count = len(_translate_count)
        check(['Apple'], [['en', 'nl', 'Apple', 'appel']], cache=cache)
        eq_(len(_translate_count), count + 1)
        check(['Apple'], [['en', 'nl', 'Apple', 'appel']], cache=cache)
        eq_(len(_translate_count), count + 1)
        check(['Apple'], [['en', 'de', 'Apple', 'Apfel']], target='de', cache=cache)
        eq_(len(_translate_count), count + 2)
        check(['Apple'], [['en', 'de', 'Apple', 'Apfel']], target='de', cache=cache)
        eq_(len(_translate_count), count + 2)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.cache):
            os.remove(cls.cache)
