from io import StringIO
import os
import random

from gramex.config import variables
from gramex.http import OK, NOT_FOUND, INTERNAL_SERVER_ERROR
from gramex.handlers.mlhandler import is_categorical
import joblib
import numpy as np
import pandas as pd
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline

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
        for path in [cls.model_path, op.join(folder, 'blank.pkl')]:
            if op.exists(path):
                os.remove(path)

    def tearDown(self):
        self.get('/mlhandler?_cache=true', method='delete')

    def test_train(self):
        resp = self.get(
            '/mlhandler?_retrain=1&_target_col=species', method='post',
            data=self.df.to_json(orient='records'))
        self.assertGreaterEqual(resp.json()['score'], self.ACC_TOL)
        # Check model metadata
        r = self.get('/mlhandler?_model').json()
        self.assertDictContainsSubset(
            {'input': ['sepal_length', 'sepal_width', 'petal_length', 'petal_width'],
             'target': 'species',
             'train_shape': [136, 4]},
            r)

    def test_post_file(self):
        buff = StringIO()
        self.df.to_csv(buff, index=False, encoding='utf8')
        buff.seek(0)
        resp = self.get('/mlhandler?_retrain=1&_target_col=species', method='post',
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
        df = self.df.drop_duplicates()
        self.assertGreaterEqual(accuracy_score(df['species'], resp.json()), self.ACC_TOL)

    def test_get_model_params(self):
        resp = self.get('/mlhandler?_model')
        ideal_params = LogisticRegression().get_params()
        actual_params = resp.json()
        self.assertEqual(
            {'params': ideal_params, 'model': 'LogisticRegression'},
            actual_params)

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
            '/mlhandler?class=DecisionTreeClassifier&_retrain=1&max_depth=10&_target_col=species',
            method='put', data=self.df.to_json(orient='records'))
        self.assertEqual(resp.json()['score'], 1.0)

    def test_delete(self):
        resp = self.get('/mlhandler', method='delete')
        self.assertEqual(resp.status_code, OK)
        self.assertFalse(op.exists(self.model_path))

    def test_blank_slate(self):
        # Assert that a model doesn't have to exist
        model_path = op.join(folder, 'blank.pkl')
        r = self.get('/mlblank&sepal_length=5.9&sepal_width=3&petal_length=5.1&petal_width=1.8')
        self.assertEqual(r.status_code, NOT_FOUND)
        self.assertFalse(op.exists(model_path))

        # Make the model
        r = self.get(
            '/mlblank?class=LogisticRegression&C=100.0&_retrain=1&_target_col=species',
            method='put', data=self.df.to_json(orient='records'))
        self.assertEqual(r.status_code, OK)
        self.assertGreater(r.json()['score'], self.ACC_TOL)

        # Check the model on disk
        model = joblib.load(model_path)
        self.assertIsInstance(model, LogisticRegression)

    def test_model_path(self):
        r = self.get('/mlnopath?class=LogisticRegression&C=100.0', method='put')
        out = r.json()
        self.assertEqual(out['model'], 'LogisticRegression')
        self.assertEqual(out['params']['C'], 100.0)
        model_path = op.join(variables['GRAMEXDATA'], 'apps', 'mlhandler', 'mlhandler-nopath.pkl')
        self.assertIsInstance(joblib.load(model_path), LogisticRegression)

    def test_filtercols(self):
        buff = StringIO()
        self.df.to_csv(buff, index=False, encoding='utf8')

        # Train excluding two columns:
        buff.seek(0)
        resp = self.get('/mlhandler?_retrain=1&_target_col=species'
                        '&_exclude=sepal_width&_exclude=petal_length',
                        method='post', files={'file': ('iris.csv', buff.read())})
        self.assertGreaterEqual(resp.json()['score'], self.ACC_TOL)

        r = self.get('/mlhandler?_cache').json()['data']
        # Check that the data still has all columns
        self.assertSetEqual(
            set(pd.DataFrame.from_records(r).columns),
            {'sepal_length', 'petal_width', 'petal_length', 'sepal_width', 'species'})
        # But the model has only two
        self.assertEqual(joblib.load(op.join(folder, 'iris.pkl')).coef_.shape, (3, 2))

        # Train including one column:
        buff.seek(0)
        resp = self.get('/mlhandler?_retrain=1&_target_col=species'
                        '&_include=sepal_width',
                        method='post', files={'file': ('iris.csv', buff.read())})
        self.assertGreaterEqual(resp.json()['score'], 0.5)
        # check coefficients shape
        self.assertEqual(joblib.load(op.join(folder, 'iris.pkl')).coef_.shape, (3, 1))

    def test_deduplicate(self):
        buff = StringIO()
        self.df.to_csv(buff, index=False, encoding='utf8')
        buff.seek(0)

        # Train as usual
        resp = self.get('/mlhandler?_retrain=1&_target_col=species',
                        method='post', files={'file': ('iris.csv', buff.read())})
        self.assertEqual(resp.status_code, OK)

        # Check that the model was trained on 136 columns, after dropping duplicates
        r = self.get('/mlhandler?_cache').json()
        self.assertListEqual(r['train_shape'], [self.df.drop_duplicates().shape[0], 4])
        # But the data had 138 rows
        self.assertEqual(len(r['data']), self.df.shape[0])

        # Train without deduplicating
        self.get('/mlhandler?_cache', method='delete')  # Clear the cache
        buff.seek(0)
        resp = self.get('/mlhandler?_retrain=1&_target_col=species&_deduplicate=false',
                        method='post', files={'file': ('iris.csv', buff.read())})
        self.assertEqual(resp.status_code, OK)

        # Check that the model was trained on 138 columns, after dropping duplicates
        r = self.get('/mlhandler?_cache').json()
        self.assertListEqual(r['train_shape'], [self.df.shape[0], 4])
        # And the data had 138 rows
        self.assertEqual(len(r['data']), self.df.shape[0])

    def test_dropna(self):
        # Randomly add nans to ten rows
        na_ix_r = [random.randint(0, self.df.shape[0]) for i in range(10)]
        na_ix_c = [random.randint(0, 4) for i in range(10)]
        df = self.df.copy()
        for row, col in zip(na_ix_r, na_ix_c):
            df.iloc[row, col] = pd.np.nan

        buff = StringIO()
        df.to_csv(buff, index=False, encoding='utf8')
        buff.seek(0)
        # Train as usual
        self.get('/mlhandler?_retrain=1&_target_col=species',
                 method='post', files={'file': ('iris.csv', buff.read())})
        # Check that the data contains 138 rows, but the training happens on 126 rows.
        r = self.get('/mlhandler?_cache').json()
        self.assertListEqual(r['train_shape'], [df.drop_duplicates().dropna().shape[0], 4])
        self.assertEqual(len(r['data']), df.shape[0])

        # Test disabling dropna
        self.get('/mlhandler?_cache', method='delete')  # Clear the cache
        buff.seek(0)
        # Train as usual
        r = self.get('/mlhandler?_retrain=1&_target_col=species&_dropna=false',
                     method='post', files={'file': ('iris.csv', buff.read())})
        self.assertEqual(r.status_code, INTERNAL_SERVER_ERROR)  # Can't train with NaNs
        # Check that the data contains 138 rows, but the training happens on 126 rows.
        r = self.get('/mlhandler?_cache').json()
        self.assertListEqual(r['train_shape'], [df.drop_duplicates().shape[0], 4])
        self.assertEqual(len(r['data']), df.shape[0])

    def test_is_categorical(self):
        self.assertTrue(is_categorical(pd.Series(['a', 'b', 'c'])))
        self.assertFalse(is_categorical(pd.Series([1, 2, 3, 4])))
        self.assertTrue(is_categorical(pd.Series([1, 1, 1, 2])))
        self.assertTrue(is_categorical(pd.Series([1, 1, 2, 2]), 0.5))
        data, _ = make_classification()
        self.assertFalse(
            any([is_categorical(pd.Series(data[:, i])) for i in range(data.shape[1])]))

    def test_pipeline(self):
        X, y = make_classification()  # NOQA: N806
        df = pd.DataFrame(X)
        df['target'] = y
        df['categorical'] = [random.choice('abc') for i in range(X.shape[0])]
        resp = self.get(
            '/mlhandler?_retrain=1&_target_col=target&_pipeline=true', method='post',
            data=df.to_json(orient='records'))
        self.assertEqual(resp.status_code, OK)

        # load the pipeline
        pipe = joblib.load(op.join(folder, 'iris.pkl'))
        self.assertIsInstance(pipe, Pipeline)
        x_transformed = pipe.named_steps['transform'].transform(df)
        # Check that the transformed dataset has the 20 original columns and the
        # three one-hot encoded ones.
        self.assertSequenceEqual(x_transformed.shape, (100, 23))  # NOQA: E912
        # check if the normalization has occured
        np.testing.allclose(x_transformed[:, :20].mean(axis=0), np.zeros((20,)))  # NOQA: E912
        np.testing.allclose(x_transformed[:, :20].var(axis=0), np.ones((20,)))  # NOQA: E912
