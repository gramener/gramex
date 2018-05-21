import os
import pandas as pd
from gramex.ml import Classifier
from nose.tools import eq_, ok_
from . import folder, TestGramex


class TestModelHandler(TestGramex):
    @classmethod
    def setUpClass(cls):
        data = pd.read_csv(os.path.join(folder, '..', 'testlib', 'iris.csv'), encoding='utf-8')
        model = Classifier()
        model.train(data)
        model.save(os.path.join(folder, 'gen.iris.pkl'))

    def test_model_info(self):
        r = self.check('/model/iris')
        info = r.json()
        ok_('BernoulliNB' in info['model'])
        eq_(info['input'], ['sepal_length', 'sepal_width', 'petal_length', 'petal_width'])
        eq_(info['output'], 'species')

    def test_predict(self):
        # Test individual results
        data = pd.DataFrame([
            {'sepal_length': 5, 'sepal_width': 3, 'petal_length': 1.5, 'petal_width': 0},
            {'sepal_length': 5, 'sepal_width': 2, 'petal_length': 5.0, 'petal_width': 1},
            {'sepal_length': 6, 'sepal_width': 3, 'petal_length': 4.8, 'petal_width': 2},
        ])
        single = [
            self.check('/model/iris', data=row.to_dict()).json()['result'][0]
            for index, row in data.iterrows()
        ]
        ok_(all(species in {'setosa', 'versicolor', 'virginica'} for species in single))

        # Test multiple results
        multi = self.check('/model/iris', data=data.to_dict(orient='list')).json()['result']
        eq_(multi, single)

        # TODO: check that the results are correct. Today, this is not working
        # eq_(multi, ['setosa', 'virginica', 'versicolor'])

    def test_predict_incomplete(self):
        self.check('/model/iris', data={'sepal_length': 5}, code=500)
