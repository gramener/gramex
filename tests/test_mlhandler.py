from io import BytesIO, StringIO
import os

import joblib
import gramex
from gramex.config import variables
from gramex.http import OK, NOT_FOUND
import pandas as pd
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.tree import DecisionTreeClassifier

from . import TestGramex, folder, tempfiles
op = os.path


class TestMLHandler(TestGramex):
    ACC_TOL = 0.95

    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv(op.join(folder, '..', 'testlib', 'iris.csv'), encoding='utf8')
        root = op.join(gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler')
        paths = [op.join(root, f) for f in [
            'mlhandler-nopath/config.json',
            'mlhandler-nopath/data.h5',
            'mlhandler-blank/config.json',
            'mlhandler-blank/data.h5',
            'mlhandler-config/config.json',
            'mlhandler-config/data.h5',
            'mlhandler-incr/config.json',
            'mlhandler-incr/data.h5',
            'mlhandler-blank.pkl',
            'mlhandler-incr.pkl',
            'mlhandler-nopath.pkl',
        ]]
        paths += [op.join(folder, 'model.pkl')]
        for p in paths:
            tempfiles[p] = p

    def test_append(self):
        try:
            r = self.get('/mlhandler?_action=append', method='post',
                         data=self.df.to_json(orient='records'),
                         headers={'Content-Type': 'application/json'})
            self.assertEqual(r.status_code, OK)
            df = pd.DataFrame.from_records(self.get('/mlhandler?_cache=true').json())
            self.assertEqual(df.shape[0], 2 * self.df.shape[0])
        finally:
            self.get('/mlhandler?_cache', method='delete')
            self.get('/mlhandler?_action=append', method='post',
                     data=self.df.to_json(orient='records'),
                     headers={'Content-Type': 'application/json'})

    def test_append_train(self):
        df_train = self.df[self.df['species'] != 'virginica']
        df_append = self.df[self.df['species'] == 'virginica']

        resp = self.get('/mlincr?_model&class=LogisticRegression&target_col=species', method='put')
        self.assertEqual(resp.status_code, OK)

        resp = self.get(
            '/mlincr?_action=append&_action=train', method='post',
            data=df_train.to_json(orient='records'),
            headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, OK)

        resp = self.get(
            '/mlincr?_action=score', method='post',
            data=self.df.to_json(orient='records'),
            headers={'Content-Type': 'application/json'})
        org_score = resp.json()['score']

        resp = self.get(
            '/mlincr?_action=append&_action=train', method='post',
            data=df_append.to_json(orient='records'),
            headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, OK)
        resp = self.get(
            '/mlincr?_action=score', method='post',
            data=self.df.to_json(orient='records'),
            headers={'Content-Type': 'application/json'})
        new_score = resp.json()['score']
        # Score should improve by at least 30%
        self.assertGreaterEqual(new_score - org_score, 0.3)  # NOQA: E912

    def test_blank_slate(self):
        # Assert that a model doesn't have to exist
        model_path = op.join(variables['GRAMEXDATA'], 'apps', 'mlhandler', 'mlhandler-blank.pkl')
        self.assertFalse(op.exists(model_path))
        r = self.get('/mlblank?sepal_length=5.9&sepal_width=3&petal_length=5.1&petal_width=1.8')
        self.assertEqual(r.status_code, NOT_FOUND)
        # Post options in any order, randomly
        r = self.get('/mlblank?_model&target_col=species', method='put')
        self.assertEqual(r.status_code, OK)
        r = self.get('/mlblank?_model&exclude=petal_width', method='put')
        self.assertEqual(r.status_code, OK)
        r = self.get('/mlblank?_model&nums=sepal_length&nums=sepal_width&nums=petal_length',
                     method='put')
        self.assertEqual(r.status_code, OK)

        r = self.get('/mlblank?_model&class=LogisticRegression', method='put')
        self.assertEqual(r.status_code, OK)

        # check the training opts
        self.assertDictEqual(
            self.get('/mlblank?_cache&_opts').json(),
            {
                'target_col': 'species',
                'exclude': ['petal_width'],
                'nums': ['sepal_length', 'sepal_width', 'petal_length']
            }
        )
        self.assertDictEqual(
            self.get('/mlblank?_cache&_params').json(),
            {
                'class': 'LogisticRegression',
                'params': {}
            }
        )

    def test_change_model(self):
        # back up the original model
        clf = joblib.load(op.join(folder, 'model.pkl'))
        try:
            # put a new model
            r = self.get(
                '/mlhandler?_model&class=DecisionTreeClassifier&criterion=entropy&splitter=random',
                method='put')
            self.assertEqual(r.status_code, OK)
            r = self.get('/mlhandler?_cache&_params')
            self.assertDictEqual(r.json(), {
                'class': 'DecisionTreeClassifier',
                'params': {
                    'criterion': 'entropy',
                    'splitter': 'random'
                }
            })
            # Train the model on the cache
            self.get('/mlhandler?_action=retrain&target_col=species', method='post')
            model = joblib.load(op.join(folder, 'model.pkl'))
            self.assertIsInstance(model, Pipeline)
            model = model.named_steps['DecisionTreeClassifier']
            self.assertIsInstance(model, DecisionTreeClassifier)
            self.assertEqual(model.criterion, 'entropy')
            self.assertEqual(model.splitter, 'random')
            resp = self.get(
                '/mlhandler?_action=score', method='post')
            self.assertGreaterEqual(resp.json()['score'], 0.8)  # NOQA: E912
        finally:
            # restore the backup
            joblib.dump(clf, op.join(folder, 'model.pkl'))

    def test_clear_cache(self):
        try:
            r = self.get('/mlhandler?_cache', method='delete')
            self.assertEqual(r.status_code, OK)
            self.assertListEqual(self.get('/mlhandler?_cache').json(), [])
        finally:
            self.get('/mlhandler?_action=append', method='post',
                     data=self.df.to_json(orient='records'),
                     headers={'Content-Type': 'application/json'})

    def test_default(self):
        # Check if model has been trained on iris, and exists at the right path.
        clf = joblib.load(op.join(folder, 'model.pkl'))
        self.assertIsInstance(clf, Pipeline)
        self.assertIsInstance(clf.named_steps['transform'], ColumnTransformer)
        self.assertIsInstance(clf.named_steps['LogisticRegression'], LogisticRegression)
        score = clf.score(self.df[[c for c in self.df if c != 'species']], self.df['species'])
        self.assertGreaterEqual(score, self.ACC_TOL)

    def test_delete(self):
        clf = joblib.load(op.join(folder, 'model.pkl'))
        try:
            r = self.get('/mlhandler?_model', method='delete')
            self.assertEqual(r.status_code, OK)
            self.assertFalse(op.exists(op.join(folder, 'model.pkl')))
            # check if the correct error message is shown
            r = self.get('/mlhandler?_model')
            self.assertEqual(r.status_code, NOT_FOUND)
        finally:
            joblib.dump(clf, op.join(folder, 'model.pkl'))

    def test_download(self):
        r = self.get('/mlhandler?_download')
        buff = BytesIO(r.content)
        buff.seek(0)
        clf = joblib.load(buff)
        self.assertIsInstance(clf, Pipeline)
        self.assertIsInstance(clf.named_steps['transform'], ColumnTransformer)
        self.assertIsInstance(clf.named_steps['LogisticRegression'], LogisticRegression)

    def test_filtercols(self):
        buff = StringIO()
        self.df.to_csv(buff, index=False, encoding='utf8')

        # Train excluding two columns:
        buff.seek(0)
        clf = joblib.load(op.join(folder, 'model.pkl'))
        try:
            resp = self.get('/mlhandler?_model&class=LogisticRegression&target_col=species'
                            '&exclude=sepal_width&exclude=petal_length',
                            method='put')
            resp = self.get('/mlhandler?_action=retrain',
                            files={'file': ('iris.csv', buff.read())},
                            method='post')
            self.assertGreaterEqual(resp.json()['score'], 0.8)  # NOQA: E912

            r = self.get('/mlhandler?_cache').json()
            # Check that the data still has all columns
            self.assertSetEqual(
                set(pd.DataFrame.from_records(r).columns),
                {'sepal_length', 'petal_width', 'petal_length', 'sepal_width', 'species'})
            # But the model has only two
            pipe = joblib.load(op.join(folder, 'model.pkl'))
            self.assertEqual(pipe.named_steps['LogisticRegression'].coef_.shape, (3, 2))

            # Train including one column:
            buff.seek(0)
            self.get('/mlhandler?_model&include=sepal_width', method='put')
            resp = self.get('/mlhandler?_action=retrain',
                            method='post', files={'file': ('iris.csv', buff.read())})
            self.assertGreaterEqual(resp.json()['score'], 0.5)
            # check coefficients shape
            pipe = joblib.load(op.join(folder, 'model.pkl'))
            self.assertEqual(pipe.named_steps['LogisticRegression'].coef_.shape, (3, 1))
        finally:
            self.get('/mlhandler?_model&_opts&include&exclude', method='delete')
            joblib.dump(clf, op.join(folder, 'model.pkl'))

    def test_get_bulk_predictions(self, target_col='species'):
        df = self.df.drop_duplicates()
        target = df.pop('species')
        resp = self.get('/mlhandler', method='post', data=df.to_json(orient='records'),
                        headers={'Content-Type': 'application/json'})
        out = pd.DataFrame.from_records(resp.json())
        self.assertGreaterEqual(accuracy_score(target, out[target_col]), self.ACC_TOL)

    def test_get_bulk_score(self):
        resp = self.get(
            '/mlhandler?_action=score', method='post',
            data=self.df.to_json(orient='records'),
            headers={'Content-Type': 'application/json'})
        self.assertGreaterEqual(resp.json()['score'], self.ACC_TOL)

    def test_get_cache(self):
        df = pd.DataFrame.from_records(self.get('/mlhandler?_cache=true').json())
        pd.testing.assert_frame_equal(df, self.df)

    def test_get_model_params(self):
        params = self.get('/mlhandler?_model').json()
        self.assertDictEqual(LogisticRegression().get_params(), params)

    def test_get_predictions(self, target_col='species'):
        resp = self.get(
            '/mlhandler?sepal_length=5.9&sepal_width=3&petal_length=5.1&petal_width=1.8')
        self.assertEqual(resp.json(), [
            {'sepal_length': 5.9, 'sepal_width': 3.0,
             'petal_length': 5.1, 'petal_width': 1.8,
             target_col: 'virginica'}
        ])
        resp = self.get(
            '/mlhandler?sepal_width=3&petal_length=5.1&sepal_length=5.9&petal_width=1.8')
        req = '/mlhandler?'
        samples = []
        target = []
        for row in self.df.sample(n=5).to_dict(orient='records'):
            samples.extend([(col, value) for col, value in row.items() if col != 'species'])
            target.append(row['species'])
        params = '&'.join([f'{k}={v}' for k, v in samples])
        resp = self.get(req + params)
        self.assertGreaterEqual(
            accuracy_score([c[target_col] for c in resp.json()], target), 0.8)  # NOQA: E912

    def test_get_predictions_post_file(self):
        df = self.df.drop_duplicates()
        target = df.pop('species')
        buff = StringIO()
        df.to_csv(buff, index=False, encoding='utf8')
        buff.seek(0)
        resp = self.get('/mlhandler?_action=predict',
                        method='post', files={'file': ('iris.csv', buff)})
        pred = pd.DataFrame.from_records(resp.json())['species']
        self.assertGreaterEqual(accuracy_score(target, pred), self.ACC_TOL)

    def test_get_score(self):
        req = '/mlhandler?_action=score&'
        samples = []
        for row in self.df.sample(n=5).to_dict(orient='records'):
            samples.extend([(col, value) for col, value in row.items()])
        params = '&'.join([f'{k}={v}' for k, v in samples])
        resp = self.get(req + params)
        self.assertGreaterEqual(resp.json()['score'], 0.6)  # NOQA: E912

    def test_model_default_path(self):
        clf = joblib.load(op.join(
            gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler', 'mlhandler-nopath.pkl'))
        self.assertIsInstance(clf, Pipeline)
        self.assertIsInstance(clf.named_steps['transform'], ColumnTransformer)
        self.assertIsInstance(clf.named_steps['LogisticRegression'], LogisticRegression)
        resp = self.get(
            '/mlnopath?_action=score', method='post',
            headers={'Content-Type': 'application/json'})
        self.assertGreaterEqual(resp.json()['score'], self.ACC_TOL)

    def test_post_after_delete_custom_model(self):
        org_clf = joblib.load(op.join(folder, 'model.pkl'))
        try:
            r = self.get('/mlhandler?_model', method='delete')
            self.assertEqual(r.status_code, OK)
            self.assertFalse(op.exists(op.join(folder, 'model.pkl')))
            # recreate the model
            X, y = make_classification()  # NOQA: N806
            xtrain, xtest, ytrain, ytest = train_test_split(X, y, stratify=y, test_size=0.25)
            df = pd.DataFrame(xtrain)
            df['target'] = ytrain
            r = self.get('/mlhandler?_model&class=GaussianNB', method='put')
            self.assertEqual(r.status_code, OK)
            r = self.get('/mlhandler?_action=train&target_col=target', method='post',
                         data=df.to_json(orient='records'),
                         headers={'Content-Type': 'application/json'})
            self.assertEqual(r.status_code, OK)
            self.assertGreaterEqual(r.json()['score'], 0.8)  # NOQA: E912
            clf = joblib.load(op.join(folder, 'model.pkl'))
            self.assertIsInstance(clf.named_steps['GaussianNB'], GaussianNB)
        finally:
            joblib.dump(org_clf, op.join(folder, 'model.pkl'))

    def test_post_after_delete_default_model(self):
        clf = joblib.load(op.join(folder, 'model.pkl'))
        try:
            r = self.get('/mlhandler?_model', method='delete')
            self.assertEqual(r.status_code, OK)
            self.assertFalse(op.exists(op.join(folder, 'model.pkl')))
            # recreate the model
            X, y = make_classification()  # NOQA: N806
            xtrain, xtest, ytrain, ytest = train_test_split(X, y, stratify=y, test_size=0.25)
            df = pd.DataFrame(xtrain)
            df['target'] = ytrain
            r = self.get('/mlhandler?_action=train&target_col=target', method='post',
                         data=df.to_json(orient='records'),
                         headers={'Content-Type': 'application/json'})
            self.assertEqual(r.status_code, OK)
            self.assertGreaterEqual(r.json()['score'], 0.8)  # NOQA: E912
        finally:
            joblib.dump(clf, op.join(folder, 'model.pkl'))

    def test_retrain(self):
        # Make some data
        x, y = make_classification()
        xtrain, xtest, ytrain, ytest = train_test_split(x, y, stratify=y, test_size=0.25)
        df = pd.DataFrame(xtrain)
        df['target'] = ytrain
        test_df = pd.DataFrame(xtest)
        test_df['target'] = ytest
        clf = joblib.load(op.join(folder, 'model.pkl'))
        try:
            # clear the cache
            resp = self.get('/mlhandler?_cache', method='delete')
            self.assertEqual(resp.status_code, OK)
            resp = self.get('/mlhandler?_cache')
            self.assertListEqual(resp.json(), [])
            # append new data, don't train
            self.get('/mlhandler?_action=append', method='post', data=df.to_json(orient='records'),
                     headers={'Content-Type': 'application/json'})
            # now, retrain
            self.get('/mlhandler?_action=retrain&target_col=target', method='post')
            # Check score against test dataset
            resp = self.get(
                '/mlhandler?_action=score', method='post',
                data=test_df.to_json(orient='records'),
                headers={'Content-Type': 'application/json'})
            self.assertGreaterEqual(resp.json()['score'], 0.6)  # NOQA: E912
        finally:
            # revert to the original cache
            self.get('/mlhandler?_cache', method='delete')
            self.get('/mlhandler?_action=append', method='post',
                     data=self.df.to_json(orient='records'),
                     headers={'Content-Type': 'application/json'})
            joblib.dump(clf, op.join(folder, 'model.pkl'))

    def test_single_line_train_fetch_model(self):
        clf = joblib.load(op.join(folder, 'model.pkl'))
        try:
            resp = self.get('/mlblank?_model&class=DecisionTreeClassifier&target_col=species',
                            method='put')
            self.assertEqual(resp.status_code, OK)
            # train
            line = StringIO()
            self.df.head(1).to_csv(line, index=False, encoding='utf8')
            line.seek(0)
            resp = self.get('/mlblank?_action=train', method='post',
                            files={'file': ('iris.csv', line.read())})
            self.assertEqual(resp.status_code, OK)
            self.assertGreaterEqual(resp.json()['score'], 0.0)

            # get the model
            resp = self.get('/mlblank')
            self.assertEqual(resp.status_code, OK)
        finally:
            joblib.dump(clf, op.join(folder, 'model.pkl'))

    def test_template(self):
        """Check if viewing the template works fine."""
        r = self.get('/mlhandler')
        self.assertEqual(r.status_code, OK)
        # Try getting predictions
        self.test_get_predictions('target')
        self.test_get_bulk_predictions('target')

    def test_train(self):
        # backup the original model
        clf = joblib.load(op.join(folder, 'model.pkl'))
        X, y = make_classification()  # NOQA: N806
        xtrain, xtest, ytrain, ytest = train_test_split(X, y, stratify=y, test_size=0.25)
        df = pd.DataFrame(xtrain)
        df['target'] = ytrain
        try:
            resp = self.get('/mlhandler?_action=train&target_col=target', method='post',
                            data=df.to_json(orient='records'),
                            headers={'Content-Type': 'application/json'})
            self.assertGreaterEqual(resp.json()['score'], 0.8)  # NOQA: E912
        finally:
            joblib.dump(clf, op.join(folder, 'model.pkl'))
            # TODO: The target_col has to be reset to species for a correct teardown.
            # But any PUT deletes an existing model and causes subsequent tests to fail.
            # Find an atomic way to reset configurations.
