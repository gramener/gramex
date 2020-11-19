from io import StringIO
import os

from gramex.http import OK
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB

from . import TestGramex, folder
op = os.path


class TestMLHandler(TestGramex):
    ACC_TOL = 0.95

    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv(op.join(folder, '..', 'testlib', 'iris.csv'), encoding='utf8')
        cls.model_path = op.join(folder, 'iris.pkl')

    @classmethod
    def tearDownClass(cls):
        if op.exists(cls.model_path):
            os.remove(cls.model_path)

    def tearDown(self):
        self.get('/mlhandler?_cache=true', method='delete')

    def test_train(self):
        resp = self.get(
            '/mlhandler?_retrain=1&target_col=species', method='post',
            data=self.df.to_json(orient='records'))
        self.assertGreaterEqual(resp.json()['score'], self.ACC_TOL)

    def test_post_file(self):
        buff = StringIO()
        self.df.to_csv(buff, index=False, encoding='utf8')
        buff.seek(0)
        resp = self.get('/mlhandler?_retrain=1&target_col=species', method='post',
                        files={'file': ('iris.csv', buff.read())})
        self.assertGreaterEqual(resp.json()['score'], self.ACC_TOL)

    def test_single_predict(self):
        resp = self.get(
            '/mlhandler?sepal_length=5.9&sepal_width=3&petal_length=5.1&petal_width=1.8')
        self.assertEqual(resp.json()[0], 'virginica')

    def test_bulk_predict(self):
        self.test_train()
        df = self.df[[c for c in self.df if c != 'species']]
        resp = self.get('/mlhandler', method='post', data=df.to_json(orient='records'))
        self.assertGreaterEqual(accuracy_score(self.df['species'], resp.json()), self.ACC_TOL)

    def test_get_model_params(self):
        resp = self.get('/mlhandler?_model')
        ideal_params = LogisticRegression().get_params()
        actual_params = resp.json()['params']
        self.assertEqual(ideal_params, actual_params)

    def test_make_model(self):
        resp = self.get('/mlhandler?class=GaussianNB', method='put')
        self.assertEqual(resp.status_code, OK)
        model = joblib.load(self.model_path)
        self.assertTrue(isinstance(model, GaussianNB))

    def test_modify_params(self):
        self.test_train()
        resp = self.get('/mlhandler?class=LogisticRegression&class_weight=balanced&C=100.0',
                        method='put')
        self.assertEqual(resp.status_code, OK)
        ideal_params = LogisticRegression(C=100.0, class_weight='balanced').get_params()
        self.assertEqual(resp.json()['params'], ideal_params)

    def test_modify_retrain(self):
        resp = self.get(
            '/mlhandler?class=DecisionTreeClassifier&_retrain=1&max_depth=10&target_col=species',
            method='put', data=self.df.to_json(orient='records'))
        self.assertEqual(resp.json(), {'score': 1.0})

    def test_delete(self):
        resp = self.get('/mlhandler', method='delete')
        self.assertEqual(resp.status_code, OK)
        self.assertFalse(op.exists(self.model_path))
