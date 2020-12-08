from io import StringIO, BytesIO
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
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from . import TestGramex, folder
op = os.path


class TestMLHandler(TestGramex):
    ACC_TOL = 0.95

    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv(op.join(folder, 'iris.csv'), encoding='utf8')
        # cls.df.to_csv(op.join(folder, 'iris.csv'), index=False, encoding='utf8')

    @classmethod
    def tearDownClass(cls):
        model_path = op.join(folder, 'model.pkl')
        if op.exists(model_path):
            os.remove(model_path)

    def test_default(self):
        # Check if model has been trained on iris, and exists at the right path.
        clf = joblib.load(op.join(folder, 'model.pkl'))
        self.assertIsInstance(clf, LogisticRegression)
        score = clf.score(self.df[[c for c in self.df if c != 'species']], self.df['species'])
        self.assertGreaterEqual(score, self.ACC_TOL)

    def test_get_predictions(self):
        resp = self.get(
            '/mlhandler?sepal_length=5.9&sepal_width=3&petal_length=5.1&petal_width=1.8')
        self.assertEqual(resp.json(), ['virginica'])
        req = '/mlhandler?'
        samples = []
        target = []
        for row in self.df.sample(n=5).to_dict(orient='records'):
            samples.extend([(col, value) for col, value in row.items() if col != 'species'])
            target.append(row['species'])
        params = '&'.join([f'{k}={v}' for k, v in samples])
        resp = self.get(req + params)
        self.assertGreaterEqual(accuracy_score(resp.json(), target), 0.8)  # NOQA: E912

    def test_get_score(self):
        req = '/mlhandler?_action=score&'
        samples = []
        for row in self.df.sample(n=5).to_dict(orient='records'):
            samples.extend([(col, value) for col, value in row.items()])
        params = '&'.join([f'{k}={v}' for k, v in samples])
        resp = self.get(req + params)
        self.assertGreaterEqual(resp.json()['score'], 0.8)  # NOQA: E912

    def test_download(self):
        r = self.get('/mlhandler?_download=true')
        buff = BytesIO(r.content)
        buff.seek(0)
        clf = joblib.load(buff)
        self.assertIsInstance(clf, LogisticRegression)

    def test_get_model_params(self):
        params = self.get('/mlhandler?_model=true').json()
        self.assertDictEqual(LogisticRegression().get_params(), params)

    def test_get_bulk_predictions(self):
        df = self.df.drop_duplicates()
        target = df.pop('species')
        resp = self.get('/mlhandler', method='post', data=df.to_json(orient='records'))
        self.assertGreaterEqual(accuracy_score(target, resp.json()), self.ACC_TOL)

    def test_get_bulk_score(self):
        resp = self.get(
            '/mlhandler?_action=score', method='post',
            data=self.df.to_json(orient='records'))
        self.assertGreaterEqual(resp.json()['score'], self.ACC_TOL)

    def test_train(self):
        # backup the original model
        clf = joblib.load(op.join(folder, 'model.pkl'))
        X, y = make_classification()  # NOQA: N806
        xtrain, xtest, ytrain, ytest = train_test_split(X, y, stratify=y, test_size=0.25)
        df = pd.DataFrame(xtrain)
        df['target'] = ytrain
        try:
            resp = self.get('/mlhandler?_action=train&_target_col=target', method='post',
                            data=df.to_json(orient='records'))
            self.assertGreaterEqual(resp.json()['score'], 0.8)  # NOQA: E912
        finally:
            joblib.dump(clf, op.join(folder, 'model.pkl'))

    def test_get_cache(self):
        df = pd.DataFrame.from_records(self.get('/mlhandler?_cache=true').json())
        pd.testing.assert_frame_equal(df, self.df)

    def test_clear_cache(self):
        try:
            r = self.get('/mlhandler?_cache', method='delete')
            self.assertEqual(r.status_code, OK)
            self.assertListEqual(self.get('/mlhandler?_cache').json(), [])
        finally:
            self.get('/mlhandler?_action=append', method='post',
                     data=self.df.to_json(orient='records'))

    def test_append(self):
        try:
            r = self.get('/mlhandler?_action=append', method='post',
                         data=self.df.to_json(orient='records'))
            self.assertEqual(r.status_code, OK)
            df = pd.DataFrame.from_records(self.get('/mlhandler?_cache=true').json())
            self.assertEqual(df.shape[0], 2 * self.df.shape[0])
        finally:
            self.get('/mlhandler?_cache', method='delete')
            self.get('/mlhandler?_action=append', method='post',
                     data=self.df.to_json(orient='records'))

    def test_retrain(self):
        # Make some data
        x, y = make_classification()
        xtrain, xtest, ytrain, ytest = train_test_split(x, y, stratify=y, test_size=0.25)
        df = pd.DataFrame(xtrain)
        df['target'] = ytrain
        test_df = pd.DataFrame(xtest)
        test_df['target'] = ytest
        try:
            # clear the cache
            self.get('/mlhandler?_cache', method='delete')
            self.assertListEqual(self.get('/mlhandler?_cache=true').json(), [])
            # append new data, don't train
            self.get('/mlhandler?_action=append', method='post', data=df.to_json(orient='records'))
            # now, retrain
            self.get('/mlhandler?_action=retrain&_target_col=target', method='post')
            # Check score against test dataset
            resp = self.get(
                '/mlhandler?_action=score', method='post',
                data=test_df.to_json(orient='records'))
            self.assertGreaterEqual(resp.json()['score'], 0.66)  # NOQA: E912
        finally:
            # revert to the original cache
            self.get('/mlhandler?_cache', method='delete')
            self.get('/mlhandler?_action=append', method='post',
                     data=self.df.to_json(orient='records'))

    def test_change_model(self):
        # back up the original model
        clf = joblib.load(op.join(folder, 'model.pkl'))
        try:
            # put a new model
            r = self.get(
                '/mlhandler?_model&class=DecisionTreeClassifier&criterion=entropy&splitter=random',
                method='put')
            self.assertEqual(r.status_code, OK)
            self.assertEqual(r.json()['criterion'], 'entropy')
            self.assertEqual(r.json()['splitter'], 'random')
            model = joblib.load(op.join(folder, 'model.pkl'))
            self.assertIsInstance(model, DecisionTreeClassifier)
            self.assertEqual(model.criterion, 'entropy')
            self.assertEqual(model.splitter, 'random')
            # Train the model on the cache
            self.get('/mlhandler?_action=retrain&_target_col=species', method='post')
            resp = self.get(
                '/mlhandler?_action=score', method='post')
            self.assertGreaterEqual(resp.json()['score'], 0.8)  # NOQA: E912
        finally:
            # restore the backup
            joblib.dump(clf, op.join(folder, 'model.pkl'))

    def test_delete(self):
        clf = joblib.load(op.join(folder, 'model.pkl'))
        try:
            r = self.get('/mlhandler?_model', method='delete')
            self.assertEqual(r.status_code, OK)
            self.assertFalse(op.exists(op.join(folder, 'model.pkl')))
        finally:
            joblib.dump(clf, op.join(folder, 'model.pkl'))


class _TestMLHandler(TestGramex):
    ACC_TOL = 0.95

    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv(op.join(folder, '..', 'testlib', 'iris.csv'), encoding='utf8')
        cls.df.to_csv(op.join(folder, 'iris.csv'), index=False, encoding='utf8')
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
        self.assertEqual(resp.json(), ['virginica'])

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
        self.assertDictContainsSubset(
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

        # Get the model parameters
        r = self.get('/mlblank?_model')
        self.assertEqual(r.status_code, OK)
        self.assertEqual(r.json()['params']['C'], 100.0)

        # Download the model
        r = self.get('/mlblank?_download')
        self.assertEqual(r.status_code, OK)
        buff = BytesIO(r.content)
        buff.seek(0)
        clf = joblib.load(buff)
        self.assertIsInstance(clf, LogisticRegression)
        self.assertEqual(clf.C, 100.0)

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
        self.assertGreaterEqual(resp.json()['score'], 0.8)  # NOQA: E912

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
        df = pd.DataFrame(X, columns=[f'c{i}' for i in range(X.shape[1])])
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
        self.assertSequenceEqual(x_transformed.shape, (100, X.shape[1] + 3))
        # check if the normalization has occured
        np.testing.assert_allclose(x_transformed[:, -X.shape[1]:].mean(axis=0),
                                   np.zeros((X.shape[1],)), atol=1e-6)
        np.testing.assert_allclose(x_transformed[:, -X.shape[1]:].var(axis=0),
                                   np.ones((X.shape[1],)), atol=1e-6)
