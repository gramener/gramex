from io import BytesIO, StringIO
import os
from unittest import skipUnless

import joblib
import gramex
from gramex.http import OK, NOT_FOUND
import numpy as np
import pandas as pd
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.tree import DecisionTreeClassifier

from . import TestGramex, folder, tempfiles
try:
    from statsmodels.datasets.interest_inflation import load as infl_load
    STATSMODELS_INSTALLED = True
except ImportError:
    STATSMODELS_INSTALLED = False


op = os.path


@skipUnless(STATSMODELS_INSTALLED, "Please install statsmodels to run these tests.")
class TestStatsmodels(TestGramex):

    @classmethod
    def setUpClass(cls):
        cls.root = op.join(gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler')
        paths = [op.join(cls.root, f) for f in [
            'mlhandler-sarimax/config.json',
            'mlhandler-sarimax/data.h5',
            'mlhandler-sarimax/mlhandler-sarimax.pkl',
        ]]
        for p in paths:
            tempfiles[p] = p

    def test_sarimax(self):
        resp = self.get('/sarimax')
        self.assertEqual(resp.status_code, NOT_FOUND)

        # Create the model
        data = infl_load().data
        index = pd.to_datetime(
            data[['year', 'quarter']].apply(lambda x: '%dQ%d' % (x.year, x.quarter), axis=1)
        )
        data.drop(['year', 'quarter'], axis=1, inplace=True)
        data['index'] = index
        params = {
            'index_col': 'index',
            'target_col': 'R'
        }
        resp = self.get('/sarimax', data=params, method='put')
        self.assertEqual(resp.status_code, OK)

        # Train the model
        resp = self.get('/sarimax?_action=append', method='post',
                        data=data.to_json(orient='records'),
                        headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, OK)
        resp = self.get('/sarimax?_action=train', method='post')
        self.assertLessEqual(resp.json()['score'], 0.01)

        # Get predictions
        resp = self.get('/sarimax', method='post',
                        data=data[['index', 'Dp']].to_json(orient='records'),
                        headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, OK)
        self.assertLessEqual(mean_absolute_error(np.array(resp.json()), data['R']), 0.01)


class TestSklearn(TestGramex):
    ACC_TOL = 0.95

    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv(op.join(folder, '..', 'testlib', 'iris.csv'), encoding='utf8')
        cls.root = op.join(gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler')
        cls.model_path = op.join(cls.root, 'mlhandler-config', 'mlhandler-config.pkl')
        paths = [op.join(cls.root, f) for f in [
            'mlhandler-nopath/config.json',
            'mlhandler-nopath/data.h5',
            'mlhandler-blank/config.json',
            'mlhandler-blank/data.h5',
            'mlhandler-blank/mlhandler-blank.pkl',
            'mlhandler-config/config.json',
            'mlhandler-config/data.h5',
            'mlhandler-incr/config.json',
            'mlhandler-incr/data.h5',
            'mlhandler-incr/mlhandler-incr.pkl',
            'mlhandler-xform/config.json',
            'mlhandler-xform/data.h5',
            'mlhandler-xform/mlhandler-xform.pkl',
            'mlhandler-nopath/mlhandler-nopath.pkl',
            'mlhandler-badcol/config.json',
            'mlhandler-badcol/data.h5',
            'mlhandler-badcol/mlhandler-badcol.pkl',
            'mlhandler-decompositions/config.json',
            'mlhandler-decompositions/data.h5',
            'mlhandler-decompositions/mlhandler-decompositions.pkl',
            'mlhandler-pipeline/config.json',
            'mlhandler-pipeline/data.h5',
            'mlhandler-pipeline/mlhandler-pipeline.pkl'
        ]]
        paths += [op.join(folder, 'model.pkl')]
        for p in paths:
            tempfiles[p] = p
        circles = op.join(folder, 'circles.csv')
        tempfiles[circles] = circles

    def test_append(self):
        try:
            r = self.get('/mlhandler?_action=append', method='post',
                         data=self.df.to_json(orient='records'),
                         headers={'Content-Type': 'application/json'})
            self.assertEqual(r.status_code, OK)
            df = pd.DataFrame.from_records(self.get('/mlhandler?_cache').json())
            self.assertEqual(df.shape[0], 2 * self.df.shape[0])
        finally:
            self.get('/mlhandler?delete=cache', method='delete')
            self.get('/mlhandler?_action=append', method='post',
                     data=self.df.to_json(orient='records'),
                     headers={'Content-Type': 'application/json'})

    def test_append_train(self):
        df_train = self.df[self.df['species'] != 'virginica']
        df_append = self.df[self.df['species'] == 'virginica']

        resp = self.get('/mlincr?class=LogisticRegression&target_col=species', method='put')
        self.assertEqual(resp.status_code, OK)

        resp = self.get(
            '/mlincr?_action=append', method='post',
            data=df_train.to_json(orient='records'),
            headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, OK)
        resp = self.get('/mlincr?_action=train', method='post')
        self.assertEqual(resp.status_code, OK)

        resp = self.get(
            '/mlincr?_action=score', method='post',
            data=self.df.to_json(orient='records'),
            headers={'Content-Type': 'application/json'})
        org_score = resp.json()['score']

        resp = self.get(
            '/mlincr?_action=append', method='post',
            data=df_append.to_json(orient='records'),
            headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, OK)
        resp = self.get('/mlincr?_action=train', method='post')
        self.assertEqual(resp.status_code, OK)
        resp = self.get(
            '/mlincr?_action=score', method='post',
            data=self.df.to_json(orient='records'),
            headers={'Content-Type': 'application/json'})
        new_score = resp.json()['score']
        # Score should improve by at least 30%
        self.assertGreaterEqual(new_score - org_score, 0.29)  # NOQA: E912

    def test_blank_slate(self):
        # Assert that a model doesn't have to exist
        model_path = op.join(self.root, 'mlhandler-blank', 'mlhandler-blank.pkl')
        self.assertFalse(op.exists(model_path))
        r = self.get('/mlblank?sepal_length=5.9&sepal_width=3&petal_length=5.1&petal_width=1.8')
        self.assertEqual(r.status_code, NOT_FOUND)
        # Post options in any order, randomly
        r = self.get('/mlblank?target_col=species', method='put')
        self.assertEqual(r.status_code, OK)
        r = self.get('/mlblank?exclude=petal_width', method='put')
        self.assertEqual(r.status_code, OK)
        r = self.get('/mlblank?nums=sepal_length&nums=sepal_width&nums=petal_length',
                     method='put')
        self.assertEqual(r.status_code, OK)

        r = self.get('/mlblank?class=LogisticRegression', method='put')
        self.assertEqual(r.status_code, OK)

        # check the training opts
        params = self.get('/mlblank?_params').json()
        self.assertDictEqual(
            params['opts'],
            {
                'target_col': 'species',
                'exclude': ['petal_width'],
                'nums': ['sepal_length', 'sepal_width', 'petal_length'],
                'include': [],
                'pipeline': True,
                'drop_duplicates': True,
                'dropna': True,
                'cats': [],
                'index_col': None
            }
        )
        self.assertDictEqual(
            params['params'],
            {
                'class': 'LogisticRegression',
                'params': {}
            }
        )

    def test_change_model(self):
        # back up the original model
        clf = joblib.load(self.model_path)
        try:
            # put a new model
            r = self.get(
                '/mlhandler?class=DecisionTreeClassifier&criterion=entropy&splitter=random',
                method='put')
            self.assertEqual(r.status_code, OK)
            r = self.get('/mlhandler?_params')
            self.assertDictEqual(r.json()['params'], {
                'class': 'DecisionTreeClassifier',
                'params': {
                    'criterion': 'entropy',
                    'splitter': 'random'
                }
            })
            # Train the model on the cache
            self.get('/mlhandler?_action=retrain&target_col=species', method='post')
            model = joblib.load(self.model_path)
            self.assertIsInstance(model, DecisionTreeClassifier)
            self.assertEqual(model.criterion, 'entropy')
            self.assertEqual(model.splitter, 'random')
            resp = self.get(
                '/mlhandler?_action=score', method='post')
            self.assertGreaterEqual(resp.json()['score'], 0.8)  # NOQA: E912
        finally:
            # restore the backup
            joblib.dump(clf, self.model_path)

    def test_clear_cache(self):
        try:
            r = self.get('/mlhandler?delete=cache', method='delete')
            self.assertEqual(r.status_code, OK)
            self.assertListEqual(self.get('/mlhandler?_cache').json(), [])
        finally:
            self.get('/mlhandler?_action=append', method='post',
                     data=self.df.to_json(orient='records'),
                     headers={'Content-Type': 'application/json'})

    def test_default(self):
        # Check if model has been trained on iris, and exists at the right path.
        clf = joblib.load(self.model_path)
        self.assertIsInstance(clf, LogisticRegression)
        score = clf.score(self.df[[c for c in self.df if c != 'species']], self.df['species'])
        self.assertGreaterEqual(score, self.ACC_TOL)

    def test_delete(self):
        clf = joblib.load(self.model_path)
        try:
            r = self.get('/mlhandler?delete=model', method='delete')
            self.assertEqual(r.status_code, OK)
            self.assertFalse(op.exists(self.model_path))
            # check if the correct error message is shown
            r = self.get('/mlhandler?_model')
            self.assertEqual(r.status_code, NOT_FOUND)
        finally:
            joblib.dump(clf, self.model_path)

    def test_download(self):
        r = self.get('/mlhandler?_download')
        buff = BytesIO(r.content)
        buff.seek(0)
        clf = joblib.load(buff)
        self.assertIsInstance(clf, LogisticRegression)

    def test_filtercols(self):
        buff = StringIO()
        self.df.to_csv(buff, index=False, encoding='utf8')

        # Train excluding two columns:
        buff.seek(0)
        clf = joblib.load(self.model_path)
        try:
            resp = self.get('/mlhandler?class=LogisticRegression&target_col=species'
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
            pipe = joblib.load(self.model_path)
            self.assertEqual(pipe.coef_.shape, (3, 2))

            # Train including one column:
            buff.seek(0)
            self.get('/mlhandler?include=sepal_width', method='put')
            resp = self.get('/mlhandler?_action=retrain',
                            method='post', files={'file': ('iris.csv', buff.read())})
            self.assertGreaterEqual(resp.json()['score'], 0.5)
            # check coefficients shape
            pipe = joblib.load(self.model_path)
            self.assertEqual(pipe.coef_.shape, (3, 1))
        finally:
            self.get('/mlhandler?delete=opts&_opts=include&_opts=exclude', method='delete')
            joblib.dump(clf, self.model_path)

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
        resp = self.get(
            '/mlhandler?_action=score&_metric=f1_weighted', method='post',
            data=self.df.to_json(orient='records'),
            headers={'Content-Type': 'application/json'})
        self.assertGreaterEqual(resp.json()['score'], self.ACC_TOL)

    def test_get_cache(self):
        df = pd.DataFrame.from_records(self.get('/mlhandler?_cache=true').json())
        pd.testing.assert_frame_equal(df, self.df)

    def test_get_model_params(self):
        params = self.get('/mlhandler?_model').json()
        self.assertDictEqual(LogisticRegression().get_params(), params)

    def test_get_predictions(self, root="mlhandler", target_col='species'):
        resp = self.get(
            f'/{root}?sepal_length=5.9&sepal_width=3&petal_length=5.1&petal_width=1.8')
        self.assertEqual(resp.json(), [
            {'sepal_length': 5.9, 'sepal_width': 3.0,
             'petal_length': 5.1, 'petal_width': 1.8,
             target_col: 'virginica'}
        ])
        resp = self.get(
            f'/{root}?sepal_width=3&petal_length=5.1&sepal_length=5.9&petal_width=1.8')
        self.assertEqual(resp.json(), [
            {'sepal_length': 5.9, 'sepal_width': 3.0,
             'petal_length': 5.1, 'petal_width': 1.8,
             target_col: 'virginica'}
        ])
        req = f'/{root}?'
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

    def test_get_predictions_duplicates(self):
        df = self.df.drop_duplicates()
        df = pd.concat([df, df], axis=0, ignore_index=True)
        target = df.pop('species')
        buff = StringIO()
        df.to_csv(buff, index=False, encoding='utf8')
        buff.seek(0)
        resp = self.get('/mlhandler?_action=predict',
                        method='post', files={'file': ('iris.csv', buff)})
        pred = pd.DataFrame.from_records(resp.json())['species']
        self.assertGreaterEqual(accuracy_score(target, pred), self.ACC_TOL)

    def test_get_predictions_post_json_file(self):
        df = self.df.drop_duplicates()
        target = df.pop('species')
        buff = StringIO()
        df.to_json(buff, orient='records')
        buff.seek(0)
        resp = self.get('/mlhandler?_action=predict',
                        method='post', files={'file': ('iris.json', buff)})
        pred = pd.DataFrame.from_records(resp.json())['species']
        self.assertGreaterEqual(accuracy_score(target, pred), self.ACC_TOL)

    def test_model_default_path(self):
        clf = joblib.load(
            op.join(self.root,
                    'mlhandler-nopath', 'mlhandler-nopath.pkl'))
        self.assertIsInstance(clf, LogisticRegression)
        resp = self.get(
            '/mlnopath?_action=score', method='post',
            headers={'Content-Type': 'application/json'})
        self.assertGreaterEqual(resp.json()['score'], self.ACC_TOL)

    def test_post_after_delete_custom_model(self):
        org_clf = joblib.load(self.model_path)
        try:
            r = self.get('/mlhandler?delete=model', method='delete')
            self.assertEqual(r.status_code, OK)
            self.assertFalse(op.exists(self.model_path))
            # recreate the model
            X, y = make_classification()  # NOQA: N806
            xtrain, xtest, ytrain, ytest = train_test_split(X, y, stratify=y, test_size=0.25)
            df = pd.DataFrame(xtrain)
            df['target'] = ytrain
            r = self.get('/mlhandler?class=GaussianNB', method='put')
            self.assertEqual(r.status_code, OK)
            r = self.get('/mlhandler?_action=train&target_col=target', method='post',
                         data=df.to_json(orient='records'),
                         headers={'Content-Type': 'application/json'})
            self.assertEqual(r.status_code, OK)
            self.assertGreaterEqual(r.json()['score'], 0.8)  # NOQA: E912
            clf = joblib.load(self.model_path)
            self.assertIsInstance(clf, GaussianNB)
        finally:
            joblib.dump(org_clf, self.model_path)

    def test_post_after_delete_default_model(self):
        clf = joblib.load(self.model_path)
        try:
            r = self.get('/mlhandler?delete=model', method='delete')
            self.assertEqual(r.status_code, OK)
            self.assertFalse(op.exists(self.model_path))
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
            joblib.dump(clf, self.model_path)

    def test_retrain(self):
        # Make some data
        x, y = make_classification()
        xtrain, xtest, ytrain, ytest = train_test_split(x, y, stratify=y, test_size=0.25)
        df = pd.DataFrame(xtrain)
        df['target'] = ytrain
        test_df = pd.DataFrame(xtest)
        test_df['target'] = ytest
        clf = joblib.load(self.model_path)
        try:
            # clear the cache
            resp = self.get('/mlhandler?delete=cache', method='delete')
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
            self.get('/mlhandler?delete=cache', method='delete')
            self.get('/mlhandler?_action=append', method='post',
                     data=self.df.to_json(orient='records'),
                     headers={'Content-Type': 'application/json'})
            joblib.dump(clf, self.model_path)

    def test_single_line_train_fetch_model(self):
        resp = self.get('/mlblank?class=DecisionTreeClassifier&target_col=species',
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

        # Assert that the model is a pipeline
        model = joblib.load(op.join(self.root, 'mlhandler-blank', 'mlhandler-blank.pkl'))
        self.assertIsInstance(model, Pipeline)
        self.assertIsInstance(model.named_steps['transform'], ColumnTransformer)
        self.assertIsInstance(
            model.named_steps['DecisionTreeClassifier'], DecisionTreeClassifier
        )

    def test_template(self):
        """Check if viewing the template works fine."""
        r = self.get('/mlhandler')
        self.assertEqual(r.status_code, OK)
        # Try getting predictions
        self.test_get_predictions(target_col='target')
        self.test_get_bulk_predictions('target')

    def test_train(self):
        # backup the original model
        clf = joblib.load(self.model_path)
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
            joblib.dump(clf, self.model_path)
            # TODO: The target_col has to be reset to species for a correct teardown.
            # But any PUT deletes an existing model and causes subsequent tests to fail.
            # Find an atomic way to reset configurations.

    def test_datatransform(self):
        with open(op.join(op.dirname(__file__), 'circles.csv'), 'r', encoding='utf8') as fin:
            resp = self.get('/mltransform?_action=score', method='post',
                            files={'file': ('circles.csv', fin.read())})
        self.assertEqual(resp.json()['score'], 1)

    def test_invalid_category(self):
        self.test_get_predictions('mlhandlerbadcol')

    def test_pca(self):
        xtr, xts = train_test_split(self.df, random_state=12345)
        # Append the training data
        r = self.get('/mldecompose?_action=append', method='post',
                     data=xtr.to_json(orient='records'),
                     headers={'Content-Type': 'application/json'})
        self.assertEqual(r.status_code, OK)
        # Train on it and check attributes
        r = self.get('/mldecompose?_action=train', method='post')
        attributes = r.json()
        sv1, sv2 = attributes['singular_values_']
        self.assertEqual(round(sv1), 20)  # NOQA: E912
        self.assertEqual(round(sv2), 5)
        # Check if test data is transformed
        r = self.get('/mldecompose?_action=predict', method='post',
                     data=xts.to_json(orient='records'),
                     headers={'Content-Type': 'application/json'})
        x_red = np.array(r.json())
        self.assertEqual(x_red.shape, (xts.shape[0], 2))

        # Check that the fitted attributes are available from GET ?_params too
        params = self.get('/mldecompose?_params').json()
        sv1, sv2 = params['attrs']['singular_values_']
        self.assertEqual(round(sv1), 20)  # NOQA: E912
        self.assertEqual(round(sv2), 5)

    def test_pipeline_features(self):
        df = pd.read_csv('actors.csv')  # Send the df as is, no preprocessing
        r = self.get('/mlpipe?_action=score', method='post', data=df.to_json(orient='records'),
                     headers={'Content-Type': 'application/json'})
        self.assertEqual(r.json()['score'], 1)
        # Inspect the model and check that the pipeline rules apply
        buff = BytesIO(self.get('/mlpipe?_download').content)
        buff.seek(0)
        model = joblib.load(buff)
        self.assertEqual(
            [(k[0], k[-1]) for k in model['transform'].transformers_],
            [('ohe', ['category']), ('scaler', ['votes'])]
        )
